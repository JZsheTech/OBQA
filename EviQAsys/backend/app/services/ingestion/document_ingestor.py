from __future__ import annotations

import hashlib
import logging
import secrets
from contextlib import nullcontext
from dataclasses import dataclass
from pathlib import Path
from typing import Any, BinaryIO

from fastapi import UploadFile

from ...env_setting import ELEMENT_CONTEXT_OVERLAP, INGEST_BATCH_SIZE, UploadSettings, get_upload_settings
from ...repositories import CollectionsRepository, DocumentsRepository, ElementsRepository, db_connection
from ..integrations import MinerUAdapter
from ..parser import normalize_element, preprocess_headers, tfidf_summary
from ..parser.unifier import ROOT_LEVEL_NAV

logger = logging.getLogger(__name__)


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
        batch_size: int = INGEST_BATCH_SIZE,
        element_context_overlap: int | None = None,
    ) -> None:
        self._upload_settings = upload_settings or get_upload_settings()
        self._documents_repo = documents_repo or DocumentsRepository()
        self._elements_repo = elements_repo or ElementsRepository()
        self._collections_repo = collections_repo or CollectionsRepository()
        self._mineru_adapter = mineru_adapter or MinerUAdapter()
        self._batch_size = max(1, batch_size)
        overlap = element_context_overlap if element_context_overlap is not None else ELEMENT_CONTEXT_OVERLAP
        self._context_overlap = max(0, overlap)
        self._upload_root = Path(self._upload_settings.root_dir)
        self._upload_root.mkdir(parents=True, exist_ok=True)

    def ingest_upload(self, collection_id: int, upload: UploadFile) -> dict[str, Any]:
        if not upload.filename:
            raise ValueError("Uploaded file must include original filename.")
        self._ensure_collection_exists(collection_id)
        upload.file.seek(0)
        stored = self._persist_stream(collection_id, upload.file, upload.filename)
        try:
            return self._ingest_stored_file(collection_id, stored)
        except Exception:
            # Clean up persisted artifact on failure.
            try:
                stored.path.unlink(missing_ok=True)
            except OSError:
                logger.warning("Failed to delete temporary upload %s", stored.path)
            raise
        finally:
            upload.file.seek(0)

    def ingest_path(self, collection_id: int, file_path: str | Path) -> dict[str, Any]:
        """Helper for manual scripts that already have a PDF on disk."""
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"PDF not found: {path}")
        self._ensure_collection_exists(collection_id)
        with path.open("rb") as stream:
            stored = self._persist_stream(collection_id, stream, path.name)
        return self._ingest_stored_file(collection_id, stored)

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

    def _ingest_stored_file(self, collection_id: int, stored: StoredUpload) -> dict[str, Any]:
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
            self._attach_header_summaries(processed_items)
            normalized = [
                normalize_element(item, images=parse_result.images) for item in processed_items
            ]
            for idx, row in enumerate(normalized):
                row["doc_id"] = document["id"]
                row["order"] = idx
            abstract_text = self._extract_abstract_text(normalized)
            self._inject_contextual_text_content(
                normalized,
                document_title=document_title,
            )
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

    def _attach_header_summaries(self, items: list[dict[str, Any]]) -> None:
        for item in items:
            if item.get("elem_type") != "header":
                continue
            start = item.get("order_start")
            end = item.get("order_end")
            section_text = self._collect_section_text(items, start, end)
            item["section_summary"] = tfidf_summary(section_text)

    def _collect_section_text(self, items: list[dict[str, Any]], start: Any, end: Any) -> str:
        chunks: list[str] = []
        for element in items:
            order = element.get("order")
            if order is None:
                continue
            if start is not None and order < start:
                continue
            if end is not None and order > end:
                continue
            if order == start and element.get("elem_type") == "header":
                continue
            elem_type = element.get("elem_type")
            if elem_type == "text":
                chunks.append(element.get("text") or "")
            elif elem_type == "table":
                captions = element.get("table_caption") or []
                if isinstance(captions, list):
                    chunks.append(" ".join(captions))
                elif isinstance(captions, str):
                    chunks.append(captions)
                if element.get("table_body"):
                    chunks.append(element["table_body"])
            elif elem_type == "equation":
                chunks.append(element.get("text") or "")
            elif elem_type == "image":
                captions = element.get("image_caption") or []
                if isinstance(captions, list):
                    chunks.append(" ".join(captions))
                elif isinstance(captions, str):
                    chunks.append(captions)
        return "\n".join(part for part in chunks if part)

    def _filter_noise_entries(self, content_list: Any) -> list[dict[str, Any]]:
        """Drop MinerU items that contain only '#' and whitespace."""
        cleaned: list[dict[str, Any]] = []
        skipped = 0
        for entry in list(content_list or []):
            if not isinstance(entry, dict):
                cleaned.append(entry)
                continue
            if self._is_hash_placeholder(entry.get("text")):
                skipped += 1
                continue
            cleaned.append(entry)
        if skipped:
            logger.info("Filtered %d MinerU items consisting of hash-only text.", skipped)
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
        for item in processed_items:
            if item.get("elem_type") != "header":
                continue
            header_name = self._clean_metadata_text(item.get("header_name"))
            if header_name and header_name.lower() != "root":
                return header_name
        return fallback

    def _inject_contextual_text_content(
        self,
        elements: list[dict[str, Any]],
        *,
        document_title: str,
    ) -> None:
        if not elements:
            return
        nav_to_indexes: dict[str, list[int]] = {}
        for idx, row in enumerate(elements):
            nav_key = self._clean_metadata_text(row.get("level_nav")) or ROOT_LEVEL_NAV
            row["level_nav"] = nav_key
            row["raw_text_content"] = self._clean_body_text(row.get("raw_text_content"))
            nav_to_indexes.setdefault(nav_key, []).append(idx)
        index_positions: dict[int, int] = {}
        for indexes in nav_to_indexes.values():
            for position, index in enumerate(indexes):
                index_positions[index] = position
        overlap = max(0, self._context_overlap)
        prefix_title = self._clean_metadata_text(document_title) or "untitled"
        for idx, row in enumerate(elements):
            nav_key = row["level_nav"]
            siblings = nav_to_indexes.get(nav_key, [])
            position = index_positions.get(idx, 0)
            elem_type = row.get("elem_type")
            use_overlap = overlap and elem_type not in {"image", "table"}
            if use_overlap:
                prev_slice = siblings[max(0, position - overlap) : position]
                next_slice = siblings[position + 1 : position + 1 + overlap]
            else:
                prev_slice = []
                next_slice = []
            prev_texts = [
                elements[ref]["raw_text_content"]
                for ref in prev_slice
                if elements[ref]["raw_text_content"]
            ]
            next_texts = [
                elements[ref]["raw_text_content"]
                for ref in next_slice
                if elements[ref]["raw_text_content"]
            ]
            current_text = self._resolve_current_text(row)
            prefix = self._format_text_prefix(
                document_title=prefix_title,
                page_no=row.get("page_no"),
                level_nav=nav_key,
            )
            body = self._compose_context_body(
                curr=current_text,
                prev_entries=prev_texts,
                next_entries=next_texts,
            )
            row["text_content"] = f"{prefix} {body}".strip()

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

    def _format_text_prefix(
        self,
        *,
        document_title: str,
        page_no: int | None,
        level_nav: str | None,
    ) -> str:
        nav_label = self._clean_metadata_text(level_nav) or ROOT_LEVEL_NAV
        page_label = str(page_no) if page_no is not None else "unknown"
        title_label = document_title or "untitled"
        return f"[doc={title_label}] [page_no={page_label}] [nav={nav_label}]"

    @staticmethod
    def _compose_context_body(
        *,
        curr: str,
        prev_entries: list[str],
        next_entries: list[str],
    ) -> str:
        blocks: list[str] = []
        if prev_entries:
            blocks.append("[PREV_CTX]")
            blocks.append("\n\n".join(prev_entries))
        blocks.append("[CURR]")
        if curr:
            blocks.append(curr)
        if next_entries:
            blocks.append("[NEXT_CTX]")
            blocks.append("\n\n".join(next_entries))
        return "\n".join(block for block in blocks if block).strip()

    def _resolve_current_text(self, row: dict[str, Any]) -> str:
        if row.get("elem_type") == "header":
            summary = self._clean_body_text(row.get("section_summary"))
            if summary:
                return summary
        return row["raw_text_content"]

    def _extract_abstract_text(self, elements: list[dict[str, Any]]) -> str | None:
        if not elements:
            return None
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


__all__ = ["DocumentIngestor", "DuplicateDocumentError"]
