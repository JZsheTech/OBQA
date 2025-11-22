from __future__ import annotations

import logging

from ...repositories import ElementsRepository
from ..embedding import EmbeddingService

logger = logging.getLogger(__name__)


class DocumentIndexer:
    """Embed elements for documents/collections and write vectors to the database."""

    def __init__(
        self,
        *,
        elements_repo: ElementsRepository | None = None,
        embedding_service: EmbeddingService | None = None,
        batch_size: int = 32,
    ) -> None:
        self._elements_repo = elements_repo or ElementsRepository()
        self._embedding_service = embedding_service or EmbeddingService()
        self._default_batch_size = max(1, batch_size)

    def embed_document(self, *, collection_id: int, doc_id: int, batch_size: int | None = None) -> int:
        """Embed all pending elements for a specific document."""
        return self._embed_unembedded(collection_id=collection_id, doc_id=doc_id, batch_size=batch_size)

    def embed_collection(self, *, collection_id: int, batch_size: int | None = None) -> int:
        """Embed all pending elements for an entire collection."""
        return self._embed_unembedded(collection_id=collection_id, doc_id=None, batch_size=batch_size)

    def _embed_unembedded(
        self,
        *,
        collection_id: int,
        doc_id: int | None,
        batch_size: int | None,
    ) -> int:
        total = 0
        chunk_size = max(1, batch_size or self._default_batch_size)
        while True:
            pending = self._elements_repo.list_unembedded(
                collection_id=collection_id,
                doc_id=doc_id,
                limit=chunk_size,
            )
            if not pending:
                break
            embeddings = self._embedding_service.batch_embed_elements(pending)
            self._elements_repo.update_embeddings(embeddings)
            total += len(pending)
            logger.info(
                "Embedded batch size=%s (doc_id=%s, collection_id=%s, total=%s)",
                len(pending),
                doc_id,
                collection_id,
                total,
            )
        if total == 0:
            logger.info(
                "No unembedded elements found (doc_id=%s, collection_id=%s)",
                doc_id,
                collection_id,
            )
        return total


__all__ = ["DocumentIndexer"]
