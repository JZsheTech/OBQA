from __future__ import annotations

import logging
from typing import Iterable, Sequence, TypedDict

from ...repositories import ElementsRepository
from ..embedding import EmbeddingService

logger = logging.getLogger(__name__)


class RetrievalResult(TypedDict, total=False):
    element_id: int
    doc_id: int
    collection_id: int
    page_no: int | None
    bbox: list[float] | None
    elem_type: str
    score: float
    text_content: str | None


class Retriever:
    """Coordinates embedding + repository searches for QA flows."""

    def __init__(
        self,
        *,
        embedding_service: EmbeddingService | None = None,
        elements_repo: ElementsRepository | None = None,
        max_candidates: int = 2000,
    ) -> None:
        self._embedding_service = embedding_service or EmbeddingService()
        self._elements_repo = elements_repo or ElementsRepository()
        self._max_candidates = max(100, max_candidates)

    def embed_query(self, query_text: str) -> list[float]:
        return self._embedding_service.embed_text(query_text)

    def retrieve_topk(
        self,
        *,
        collection_id: int,
        query_text: str,
        top_k: int = 5,
        doc_id: int | None = None,
        elem_types: Iterable[str] | None = None,
        search_mode: str = "vector",
        query_vector: Sequence[float] | None = None,
    ) -> list[RetrievalResult]:
        search_mode = (search_mode or "vector").lower()
        normalized_types = self._normalize_types(elem_types)
        if search_mode == "vector":
            vector = list(query_vector) if query_vector is not None else self.embed_query(query_text)
            rows = self._elements_repo.topk_by_collection(
                collection_id=collection_id,
                query_vec=vector,
                k=top_k,
                doc_id=doc_id,
                elem_types=normalized_types,
                max_candidates=self._max_candidates,
            )
        elif search_mode == "fulltext":
            rows = self._elements_repo.search_fulltext(
                collection_id=collection_id,
                query=query_text,
                k=top_k,
                doc_id=doc_id,
                elem_types=normalized_types,
                max_candidates=min(self._max_candidates, 1000),
            )
        else:
            raise ValueError(f"Unsupported search_mode: {search_mode}")
        logger.debug("Retriever returning %s candidates (mode=%s)", len(rows), search_mode)
        return [self._format_result(row) for row in rows]

    @staticmethod
    def _normalize_types(elem_types: Iterable[str] | None) -> set[str] | None:
        if not elem_types:
            return None
        normalized = {entry.strip().lower() for entry in elem_types if entry and entry.strip()}
        return normalized or None

    @staticmethod
    def _format_result(row: dict[str, object]) -> RetrievalResult:
        bbox = row.get("bbox")
        if bbox is not None and not isinstance(bbox, list):
            bbox = None
        return RetrievalResult(
            element_id=int(row["element_id"]),
            doc_id=int(row["doc_id"]),
            collection_id=int(row["collection_id"]),
            page_no=row.get("page_no"),
            bbox=bbox,
            elem_type=str(row.get("elem_type") or ""),
            score=float(row.get("score") or 0.0),
            text_content=row.get("text_content"),
        )


__all__ = ["Retriever", "RetrievalResult"]
