from __future__ import annotations

import logging
from typing import Any

from ...env_setting import ENABLE_PAGE_TEXT_CHUNKS, INGEST_BATCH_SIZE
from ...repositories import (
    ChunksRepository,
    DocumentsRepository,
    ElementsRepository,
    PageTextChunksRepository,
)
from ..embedding import EmbeddingService
from .chunk_builder import ChunkBuilder

logger = logging.getLogger(__name__)


class DocumentIndexer:
    """Build chunks/page-chunks and embed them for documents/collections."""

    def __init__(
        self,
        *,
        elements_repo: ElementsRepository | None = None,
        chunks_repo: ChunksRepository | None = None,
        page_chunks_repo: PageTextChunksRepository | None = None,
        documents_repo: DocumentsRepository | None = None,
        embedding_service: EmbeddingService | None = None,
        chunk_builder: ChunkBuilder | None = None,
        enable_page_chunks: bool | None = None,
        batch_size: int = INGEST_BATCH_SIZE,
    ) -> None:
        self._elements_repo = elements_repo or ElementsRepository()
        self._chunks_repo = chunks_repo or ChunksRepository()
        self._page_chunks_repo = page_chunks_repo or PageTextChunksRepository()
        self._documents_repo = documents_repo or DocumentsRepository()
        self._embedding_service = embedding_service or EmbeddingService()
        self._chunk_builder = chunk_builder or ChunkBuilder()
        self._enable_page_chunks = ENABLE_PAGE_TEXT_CHUNKS if enable_page_chunks is None else bool(enable_page_chunks)
        self._default_batch_size = max(1, batch_size)

    def embed_document(self, *, collection_id: int, doc_id: int, batch_size: int | None = None) -> int:
        """Rebuild chunks (and page chunks) for a document and embed them."""
        document = self._documents_repo.get_by_id(doc_id)
        if not document:
            raise ValueError(f"Document {doc_id} not found.")
        actual_collection_id = int(document["collection_id"])
        if actual_collection_id != collection_id:
            collection_id = actual_collection_id
        chunk_size = max(1, batch_size or self._default_batch_size)
        elements = self._elements_repo.list_by_document(doc_id)
        element_map = {int(row["id"]): row for row in elements if row.get("id") is not None}
        chunk_records = self._chunk_builder.build_chunks(
            doc_id=doc_id,
            collection_id=collection_id,
            elements=elements,
        )
        page_chunk_records: list[dict[str, Any]] = []
        if self._enable_page_chunks:
            page_chunk_records = self._chunk_builder.build_page_chunks(
                doc_id=doc_id,
                collection_id=collection_id,
                elements=elements,
            )

        self._chunks_repo.delete_by_document(doc_id)
        if chunk_records:
            self._chunks_repo.batch_insert(chunk_records, batch_size=chunk_size)
        if self._enable_page_chunks:
            self._page_chunks_repo.delete_by_document(doc_id)
            if page_chunk_records:
                self._page_chunks_repo.batch_insert(page_chunk_records, batch_size=chunk_size)

        embedded_chunks = self._embed_chunks(
            doc_id=doc_id,
            collection_id=collection_id,
            element_map=element_map,
            batch_size=chunk_size,
        )
        embedded_page_chunks = 0
        if self._enable_page_chunks:
            embedded_page_chunks = self._embed_page_chunks(
                doc_id=doc_id,
                collection_id=collection_id,
                batch_size=chunk_size,
            )
        logger.info(
            "Document indexing completed doc_id=%s collection_id=%s chunks=%s page_chunks=%s",
            doc_id,
            collection_id,
            embedded_chunks,
            embedded_page_chunks,
        )
        return embedded_chunks + embedded_page_chunks

    def embed_collection(self, *, collection_id: int, batch_size: int | None = None) -> int:
        """Rebuild and embed chunks for every document in the collection."""
        documents = self._documents_repo.list_by_collection(collection_id)
        total = 0
        for document in documents:
            doc_id = int(document["id"])
            total += self.embed_document(collection_id=collection_id, doc_id=doc_id, batch_size=batch_size)
        return total

    def _embed_chunks(
        self,
        *,
        doc_id: int,
        collection_id: int,
        element_map: dict[int, dict[str, Any]],
        batch_size: int | None,
    ) -> int:
        total = 0
        chunk_size = max(1, batch_size or self._default_batch_size)
        while True:
            pending = self._chunks_repo.list_unembedded(
                collection_id=collection_id,
                doc_id=doc_id,
                limit=chunk_size,
            )
            if not pending:
                break
            embeddings: dict[int, list[float]] = {}
            for row in pending:
                chunk_type = (row.get("chunk_type") or "text").lower()
                elem_ids = row.get("elem_ids") or []
                raw_text = (row.get("chunk_text_main") or "").strip()
                text = raw_text
                image_payload = None
                element: dict[str, Any] | None = None
                if chunk_type in {"image", "table"} and elem_ids:
                    element = element_map.get(int(elem_ids[0]))
                    if element:
                        image_payload = element.get("image_base64")
                    text = self._compose_multimodal_text(
                        chunk_type=chunk_type,
                        chunk_text=raw_text,
                        element=element,
                    )
                try:
                    if chunk_type in {"image", "table"}:
                        if not text and not image_payload:
                            logger.debug("Skip embedding empty multimodal chunk %s", row.get("id"))
                            continue
                        vector = self._embedding_service.embed_text_image(text, image_payload)
                    else:
                        if not text:
                            logger.debug("Skip embedding empty text chunk %s", row.get("id"))
                            continue
                        vector = self._embedding_service.embed_text(text)
                except Exception as exc:  # pragma: no cover - runtime guard
                    logger.warning("Embedding chunk failed id=%s doc_id=%s: %s", row.get("id"), doc_id, exc)
                    continue
                embeddings[int(row["id"])] = vector
            if embeddings:
                self._chunks_repo.update_embeddings(embeddings)
                total += len(embeddings)
                logger.info(
                    "Embedded chunk batch size=%s (doc_id=%s collection_id=%s total=%s)",
                    len(embeddings),
                    doc_id,
                    collection_id,
                    total,
                )
            if len(pending) < chunk_size:
                break
        return total

    def _embed_page_chunks(
        self,
        *,
        doc_id: int,
        collection_id: int,
        batch_size: int | None,
    ) -> int:
        total = 0
        chunk_size = max(1, batch_size or self._default_batch_size)
        while True:
            pending = self._page_chunks_repo.list_unembedded(
                collection_id=collection_id,
                doc_id=doc_id,
                limit=chunk_size,
            )
            if not pending:
                break
            embeddings: dict[int, list[float]] = {}
            for row in pending:
                text = (row.get("chunk_text_main") or "").strip()
                if not text:
                    continue
                try:
                    vector = self._embedding_service.embed_text(text)
                except Exception as exc:  # pragma: no cover - runtime guard
                    logger.warning("Embedding page chunk failed id=%s doc_id=%s: %s", row.get("id"), doc_id, exc)
                    continue
                embeddings[int(row["id"])] = vector
            if embeddings:
                self._page_chunks_repo.update_embeddings(embeddings)
                total += len(embeddings)
                logger.info(
                    "Embedded page chunk batch size=%s (doc_id=%s collection_id=%s total=%s)",
                    len(embeddings),
                    doc_id,
                    collection_id,
                    total,
                )
            if len(pending) < chunk_size:
                break
        return total

    @staticmethod
    def _compose_multimodal_text(
        *,
        chunk_type: str,
        chunk_text: str,
        element: dict[str, Any] | None,
    ) -> str:
        parts: list[str] = []
        seen: set[str] = set()

        def _add(value: Any) -> None:
            text = (value or "").strip()
            if not text:
                return
            if text in seen:
                return
            seen.add(text)
            parts.append(text)

        _add(chunk_text)
        if element:
            lowered = (chunk_type or "").lower()
            if lowered == "image":
                _add(element.get("text_caption"))
                _add(element.get("raw_text_content"))
                _add(element.get("text_content"))
            elif lowered == "table":
                _add(element.get("text_content"))
                _add(element.get("raw_text_content"))
                _add(element.get("text_caption"))
            else:
                _add(element.get("raw_text_content"))
        return " ".join(parts).strip()


__all__ = ["DocumentIndexer"]
