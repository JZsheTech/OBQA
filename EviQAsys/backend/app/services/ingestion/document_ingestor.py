from __future__ import annotations

import hashlib
import logging
import re
import secrets
from contextlib import nullcontext
from dataclasses import dataclass
from pathlib import Path
from typing import Any, BinaryIO

from fastapi import UploadFile

from ...env_setting import INGEST_BATCH_SIZE, UploadSettings, get_upload_settings
from ...repositories import CollectionsRepository, DocumentsRepository, ElementsRepository, db_connection
from ..integrations.mineru_adapter import MinerUAdapter
from ..parser import normalize_element, preprocess_headers
from ..parser.unifier import ROOT_LEVEL_NAV

logger = logging.getLogger(__name__)

INLINE_ABSTRACT_PREFIX = re.compile(
    "^\\s*abstract\\b[\\s:\\uFF1A\\-\\u2013\\u2014\\u2015\\.]+(.+)$",
    re.IGNORECASE | re.DOTALL,
)
ALLOWED_MINERU_TYPES = {"text", "image", "table", "equation"}


@dataclass(slots=True)
class StoredUpload:
    path: Path
    original_name: str
    file_size_bytes: int
    file_sha256: str


class DuplicateDocumentError(Exception):
    """Raised when a document with the same name and file hash already exists."""


class DocumentIngestor:
    """Co-ordinates PDF ingestion via MinerU into documents/elements tables."""

    def __init__(
        self,
        *,
        upload_settings: UploadSettings | None = None,
        documents_repo: DocumentsRepository | None = None,
        elements_repo: ElementsRepository | None = None,
        collections_repo: CollectionsRepository | None = None,
        mineru_adapter: MinerUAdapter | None = None,
        batch_size: int = INGEST_BATCH_SIZE
    ) -> None:
        self._upload_settings = upload_settings or get_upload_settings()
        self._documents_repo = documents_repo or DocumentsRepository()
        self._elements_repo = elements_repo or ElementsRepository()
        self._collections_repo = collections_repo or CollectionsRepository()
        self._mineru_adapter = mineru_adapter or MinerUAdapter()
        self._batch_size = max(1, batch_size)

        self._upload_root = Path(self._upload_settings.root_dir)
        self._upload_root.mkdir(parents=True, exist_ok=True)

    def ingest_upload(self, collection_id: int, upload: UploadFile) -> dict[str, Any]:
        if not upload.filename:
            raise ValueError("Uploaded file must include original filename.")
        self._ensure_collection_exists(collection_id)
        upload.file.seek(0)
        stored = self._persist_stream(collection_id, upload.file, upload.filename)
        try:
            return self._ingest_stored_file(collection_id, stored, arxiv_favorite_id=None)
        except Exception:
            # Clean up persisted artifact on failure.
            try:
                stored.path.unlink(missing_ok=True)
            except OSError:
                logger.warning("Failed to delete temporary upload %s", stored.path)
            raise
        finally:
            upload.file.seek(0)

    def ingest_path(
        self,
        collection_id: int,
        file_path: str | Path,
        *,
        arxiv_favorite_id: int | None = None,
    ) -> dict[str, Any]:
        """Helper for manual scripts that already have a PDF on disk."""
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"PDF not found: {path}")
        self._ensure_collection_exists(collection_id)
        with path.open("rb") as stream:
            stored = self._persist_stream(collection_id, stream, path.name)
        return self._ingest_stored_file(collection_id, stored, arxiv_favorite_id=arxiv_favorite_id)

    def _ensure_collection_exists(self, collection_id: int) -> None:
        collection = self._collections_repo.get_by_id(collection_id)
        if not collection:
            raise ValueError(f"Collection {collection_id} does not exist.")

    def _persist_stream(self, collection_id: int, stream: BinaryIO, original_name: str) -> StoredUpload:
        sanitized_name = Path(original_name).name or f"collection-{collection_id}.pdf"
        target_dir = self._upload_root.joinpath(str(collection_id))
        target_dir.mkdir(parents=True, exist_ok=True)
        unique_name = f"{secrets.token_hex(4)}_{sanitized_name}"
        target_path = target_dir.joinpath(unique_name)
        max_bytes = self._upload_settings.max_upload_mb * 1024 * 1024
        hasher = hashlib.sha256()
        total = 0
        chunk_size = 1024 * 1024
        try:
            with target_path.open("wb") as destination:
                stream.seek(0)
                while True:
                    chunk = stream.read(chunk_size)
                    if not chunk:
                        break
                    total += len(chunk)
                    if total > max_bytes:
                        raise ValueError("Uploaded file exceeds MAX_UPLOAD_MB limit.")
                    destination.write(chunk)
                    hasher.update(chunk)
        except Exception:
            target_path.unlink(missing_ok=True)
            raise
        file_hash = hasher.hexdigest()
        return StoredUpload(
            path=target_path,
            original_name=sanitized_name,
            file_size_bytes=total,
            file_sha256=file_hash,
        )

    def _ingest_stored_file(
        self,
        collection_id: int,
        stored: StoredUpload,
        *,
        arxiv_favorite_id: int | None,
    ) -> dict[str, Any]:
        duplicate = self._documents_repo.find_duplicate(
            collection_id=collection_id,
            file_name=stored.original_name,
            file_sha256=stored.file_sha256,
        )
        if duplicate:
            stored.path.unlink(missing_ok=True)
            raise DuplicateDocumentError(
                f"Document already exists for collection={collection_id} and file={stored.original_name}",
            )
        document = self._documents_repo.create_document(
            collection_id=collection_id,
            title=Path(stored.original_name).stem,
            file_name=stored.original_name,
            file_path=str(stored.path),
            file_sha256=stored.file_sha256,
            file_size_bytes=stored.file_size_bytes,
            arxiv_favorite_id=arxiv_favorite_id,
        )
        try:
            parse_result = self._mineru_adapter.parse(stored.path, file_name=stored.original_name)
            content_list = self._filter_noise_entries(parse_result.content_list)
            processed_items = preprocess_headers(content_list)
            document_title = self._determine_document_title(
                default_title=document.get("title"),
                processed_items=processed_items,
            )
            if document_title != document.get("title"):
                self._documents_repo.update_document(document["id"], title=document_title)
            document["title"] = document_title
            normalized = [
                normalize_element(item, images=parse_result.images) for item in processed_items
            ]
            for idx, row in enumerate(normalized):
                row["doc_id"] = document["id"]
                row["order"] = idx
            abstract_text = self._extract_abstract_text(normalized)
            self._inject_contextual_text_content(normalized)
            element_count = len(normalized)
            num_pages = self._calculate_num_pages(normalized)
            self._write_elements_and_finalize(
                normalized,
                md_text=parse_result.md_text,
                abstract=abstract_text,
                meta_info=None,
                num_pages=num_pages,
                element_count=element_count,
                document_id=document["id"],
            )
            document["md_text"] = parse_result.md_text
            document["num_pages"] = num_pages
            document["element_count"] = element_count
            document["abstract"] = abstract_text
            document["meta_info"] = None
            return document
        except Exception:
            logger.exception("Failed to ingest document %s", document.get("id"))
            self._documents_repo.delete_document(document["id"])
            raise

    def _filter_noise_entries(self, content_list: Any) -> list[dict[str, Any]]:
        """Drop MinerU items that contain only '#' or unsupported types."""
        cleaned: list[dict[str, Any]] = []
        skipped_hash = 0
        skipped_type = 0
        for entry in list(content_list or []):
            if not isinstance(entry, dict):
                continue
            elem_type = (entry.get("type") or "").lower()
            if elem_type not in ALLOWED_MINERU_TYPES:
                skipped_type += 1
                continue
            if self._is_hash_placeholder(entry.get("text")):
                skipped_hash += 1
                continue
            cleaned.append(entry)
        if skipped_type:
            logger.info("Filtered %d MinerU items with unsupported type.", skipped_type)
        if skipped_hash:
            logger.info("Filtered %d MinerU items consisting of hash-only text.", skipped_hash)
        return cleaned

    def _calculate_num_pages(self, elements: list[dict[str, Any]]) -> int | None:
        pages = [row.get("page_no") for row in elements if row.get("page_no") is not None]
        if not pages:
            return None
        return max(int(page) for page in pages)

    def _write_elements_and_finalize(
        self,
        elements: list[dict[str, Any]],
        *,
        md_text: str | None,
        abstract: str | None,
        meta_info: dict[str, Any] | None,
        num_pages: int | None,
        element_count: int,
        document_id: int,
    ) -> None:
        if not elements:
            raise ValueError("MinerU returned empty content_list.")
        with db_connection() as connection:
            conn_ctx = lambda: nullcontext(connection)
            elements_repo = ElementsRepository(connection_provider=conn_ctx)
            documents_repo = DocumentsRepository(connection_provider=conn_ctx)
            elements_repo.batch_insert(elements, batch_size=self._batch_size)
            documents_repo.update_document(
                document_id,
                md_text=md_text,
                num_pages=num_pages,
                element_count=element_count,
                abstract=abstract,
                meta_info=meta_info,
            )

    def _determine_document_title(
        self,
        *,
        default_title: str | None,
        processed_items: list[dict[str, Any]],
    ) -> str:
        fallback = self._clean_metadata_text(default_title) or "untitled"
        merged = self._merge_header_title_fragments(processed_items)
        if merged:
            return merged
        for item in processed_items:
            if item.get("elem_type") != "header":
                continue
            header_name = self._clean_metadata_text(item.get("header_name"))
            if header_name and header_name.lower() != "root":
                return header_name
        return fallback

    def _merge_header_title_fragments(self, items: list[dict[str, Any]]) -> str | None:
        """Join contiguous header lines on the first page to recover split titles."""
        first_header_idx = None
        for idx, item in enumerate(items):
            if item.get("elem_type") != "header":
                continue
            header_name = self._clean_metadata_text(item.get("header_name"))
            if header_name and header_name.lower() != "root":
                first_header_idx = idx
                break
        if first_header_idx is None:
            return None
        base = items[first_header_idx]
        base_level = base.get("header_level")
        base_page = self._resolve_page_index(base)
        fragments = [self._clean_metadata_text(base.get("header_name"))]
        prev_bbox = base.get("bbox") or base.get("bbox_json")
        for candidate in items[first_header_idx + 1 :]:
            if candidate.get("elem_type") != "header":
                break
            if base_level is not None and candidate.get("header_level") != base_level:
                break
            if self._resolve_page_index(candidate) != base_page:
                break
            candidate_text = self._clean_metadata_text(candidate.get("header_name"))
            if not candidate_text or candidate_text.lower() == "root":
                break
            if self._is_section_break_header(candidate_text):
                break
            curr_bbox = candidate.get("bbox") or candidate.get("bbox_json")
            if not self._within_title_gap(prev_bbox, curr_bbox):
                break
            fragments.append(candidate_text)
            prev_bbox = curr_bbox or prev_bbox
        merged = self._clean_metadata_text(" ".join(fragment for fragment in fragments if fragment))
        return merged or None

    @staticmethod
    def _resolve_page_index(item: dict[str, Any]) -> int | None:
        for key in ("page_idx", "page_no"):
            value = item.get(key)
            if value is None:
                continue
            try:
                page = int(value)
            except (TypeError, ValueError):
                continue
            if key == "page_no" and page > 0:
                return page - 1
            return page
        return None

    @staticmethod
    def _within_title_gap(prev_bbox: Any, curr_bbox: Any, *, max_gap: float = 80.0) -> bool:
        if not prev_bbox or not curr_bbox:
            return True
        try:
            prev_bottom = float(prev_bbox[3])
            curr_top = float(curr_bbox[1])
        except (TypeError, ValueError, IndexError):
            return True
        return (curr_top - prev_bottom) <= max_gap

    @staticmethod
    def _is_section_break_header(text: str) -> bool:
        lowered = text.lower()
        stop_tokens = ("abstract", "introduction", "table of contents", "contents", "keywords")
        return any(token in lowered for token in stop_tokens)

    def _inject_contextual_text_content(self, elements: list[dict[str, Any]]) -> None:
        if not elements:
            return
        for row in elements:
            nav_key = self._clean_metadata_text(row.get("level_nav")) or ROOT_LEVEL_NAV
            row["level_nav"] = nav_key
            row["raw_text_content"] = self._clean_body_text(row.get("raw_text_content"))
            row["text_content"] = row["raw_text_content"]

    @staticmethod
    def _clean_metadata_text(value: Any) -> str:
        if value is None:
            return ""
        return " ".join(str(value).split())

    @staticmethod
    def _clean_body_text(value: Any) -> str:
        if value is None:
            return ""
        return str(value).strip()

    @staticmethod
    def _is_hash_placeholder(text: Any) -> bool:
        if text is None:
            return False
        text_str = str(text)
        if not text_str:
            return False
        if "#" not in text_str:
            return False
        return text_str.replace("#", "").strip() == ""

    def _extract_abstract_text(self, elements: list[dict[str, Any]]) -> str | None:
        if not elements:
            return None
        header_abstract = self._extract_header_abstract(elements)
        if header_abstract:
            return header_abstract
        return self._extract_inline_abstract(elements)

    def _extract_header_abstract(self, elements: list[dict[str, Any]]) -> str | None:
        for idx, row in enumerate(elements):
            if row.get("elem_type") != "header":
                continue
            header_name = self._clean_metadata_text(row.get("header_name"))
            if header_name.lower() != "abstract":
                continue
            for candidate in elements[idx + 1 :]:
                if candidate.get("elem_type") == "header":
                    break
                abstract_text = self._clean_body_text(
                    candidate.get("raw_text_content") or candidate.get("text_content"),
                )
                if abstract_text:
                    return abstract_text
            return None
        return None

    def _extract_inline_abstract(self, elements: list[dict[str, Any]]) -> str | None:
        for row in elements:
            if row.get("elem_type") != "text":
                continue
            page_idx = self._resolve_page_index(row)
            if page_idx is not None and page_idx > 1:
                # Abstracts appear at the very start; ignore later pages to avoid false positives.
                continue
            text_value = self._clean_body_text(
                row.get("raw_text_content") or row.get("text_content"),
            )
            if not text_value:
                continue
            abstract_text = self._parse_inline_abstract(text_value)
            if abstract_text:
                return abstract_text
        return None

    def _parse_inline_abstract(self, text_value: str) -> str | None:
        match = INLINE_ABSTRACT_PREFIX.match(text_value)
        if not match:
            return None
        abstract_body = match.group(1).strip()
        if not abstract_body:
            return None
        return abstract_body or None


__all__ = ["DocumentIngestor", "DuplicateDocumentError"]
