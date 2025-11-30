from __future__ import annotations

import logging
from typing import Any, Iterable, Sequence, TypedDict

from ...env_setting import ENABLE_PAGE_CHUNK_RETRIEVAL, RETRIEVAL_TOPK_CHUNK, RETRIEVAL_TOPK_PAGE
from ...repositories import ChunksRepository, ElementsRepository, PageTextChunksRepository
from ..embedding import EmbeddingService

logger = logging.getLogger(__name__)


class ChunkRetrievalResult(TypedDict, total=False):
    chunk_id: int
    doc_id: int
    collection_id: int
    order: int | None
    level_nav: str | None
    chunk_type: str
    chunk_text_main: str | None
    elem_ids: list[int]
    page_start: int | None
    page_end: int | None
    score: float


class Retriever:
    """Coordinates embedding + repository searches for QA flows."""

    def __init__(
        self,
        *,
        embedding_service: EmbeddingService | None = None,
        chunks_repo: ChunksRepository | None = None,
        page_chunks_repo: PageTextChunksRepository | None = None,
        elements_repo: ElementsRepository | None = None,
        max_candidates: int = 2000,
        chunk_top_k: int = RETRIEVAL_TOPK_CHUNK,
        page_top_k: int = RETRIEVAL_TOPK_PAGE,
        enable_page_filter: bool = ENABLE_PAGE_CHUNK_RETRIEVAL,
    ) -> None:
        self._embedding_service = embedding_service or EmbeddingService()
        self._chunks_repo = chunks_repo or ChunksRepository()
        self._page_chunks_repo = page_chunks_repo or PageTextChunksRepository()
        self._elements_repo = elements_repo or ElementsRepository()
        self._max_candidates = max(100, max_candidates)
        self._chunk_top_k = max(1, chunk_top_k)
        self._page_top_k = max(1, page_top_k)
        self._enable_page_filter = enable_page_filter

    def embed_query(self, query_text: str) -> list[float]:
        return self._embedding_service.embed_text(query_text)

    def retrieve_topk(
        self,
        *,
        collection_id: int,
        query_text: str,
        top_k: int | None = None,
        doc_id: int | None = None,
        chunk_types: Iterable[str] | None = None,
        search_mode: str = "hybrid",
        query_vector: Sequence[float] | None = None,
        enable_page_filter: bool | None = None,
        page_top_k: int | None = None,
    ) -> list[ChunkRetrievalResult]:
        search_mode = (search_mode or "hybrid").lower()
        normalized_types = self._normalize_types(chunk_types)
        chunk_top_k = max(1, top_k or self._chunk_top_k)
        use_page_filter = self._enable_page_filter if enable_page_filter is None else bool(enable_page_filter)
        page_top_limit = max(1, page_top_k or self._page_top_k)
        query = (query_text or "").strip()
        if not query:
            raise ValueError("query_text must be provided for retrieval.")
        vector = None
        if search_mode in {"vector", "hybrid"} or use_page_filter:
            vector = list(query_vector) if query_vector is not None else self.embed_query(query)

        page_filters: list[tuple[int, int]] = []
        if use_page_filter and vector is not None:
            page_candidates = self._page_chunks_repo.topk_by_collection(
                collection_id=collection_id,
                doc_id=doc_id,
                query_vec=vector,
                k=page_top_limit,
                max_candidates=self._max_candidates,
            )
            page_filters = [
                (int(row["doc_id"]), int(row["page_no"]))
                for row in page_candidates
                if row.get("page_no") is not None
            ]
            logger.debug(
                "Page-level filters applied: %s",
                page_filters,
            )

        if search_mode == "vector":
            if vector is None:
                vector = self.embed_query(query)
            rows = self._chunks_repo.topk_by_collection(
                collection_id=collection_id,
                query_vec=vector,
                k=chunk_top_k,
                doc_id=doc_id,
                chunk_types=normalized_types,
                page_filters=page_filters,
                max_candidates=self._max_candidates,
            )
        elif search_mode == "hybrid":
            if vector is None:
                vector = self.embed_query(query)
            rows = self._chunks_repo.search_hybrid(
                collection_id=collection_id,
                query=query,
                query_vec=vector,
                k=chunk_top_k,
                doc_id=doc_id,
                chunk_types=normalized_types,
                page_filters=page_filters,
                max_candidates=self._max_candidates,
            )
        elif search_mode == "fulltext":
            rows = self._chunks_repo.search_fulltext(
                collection_id=collection_id,
                query=query,
                k=chunk_top_k,
                doc_id=doc_id,
                chunk_types=normalized_types,
                page_filters=page_filters,
                max_candidates=min(self._max_candidates, 1000),
            )
        else:
            raise ValueError(f"Unsupported search_mode: {search_mode}")
        logger.debug("Retriever returning %s chunk candidates (mode=%s)", len(rows), search_mode)
        return [self._format_chunk_result(row) for row in rows]

    def expand_chunks_to_elements(self, chunk_results: Sequence[ChunkRetrievalResult]) -> list[dict[str, Any]]:
        """Load element payloads for the given chunk retrieval results."""
        element_ids: list[int] = []
        for result in chunk_results:
            for elem_id in result.get("elem_ids") or []:
                if elem_id not in element_ids:
                    element_ids.append(int(elem_id))
        if not element_ids:
            return []
        elements = self._elements_repo.list_by_ids(element_ids)
        element_map: dict[int, dict[str, Any]] = {}
        for row in elements:
            element_map[int(row["id"])] = row
        expanded: list[dict[str, Any]] = []
        for result in chunk_results:
            chunk_id = int(result["chunk_id"])
            chunk_type = (result.get("chunk_type") or "").lower()
            chunk_score = float(result.get("score") or 0.0)
            for elem_id in result.get("elem_ids") or []:
                element = element_map.get(int(elem_id))
                if not element:
                    continue
                expanded.append(
                    {
                        "chunk_id": chunk_id,
                        "chunk_type": chunk_type,
                        "chunk_score": chunk_score,
                        "element_id": int(elem_id),
                        "doc_id": element.get("doc_id"),
                        "collection_id": result.get("collection_id"),
                        "page_no": element.get("page_no"),
                        "bbox": element.get("bbox"),
                        "elem_type": element.get("elem_type"),
                        "raw_text_content": element.get("raw_text_content"),
                        "text_caption": element.get("text_caption"),
                        "image_base64": element.get("image_base64"),
                        "level_nav": element.get("level_nav"),
                    },
                )
        return expanded

    @staticmethod
    def _normalize_types(chunk_types: Iterable[str] | None) -> set[str] | None:
        if not chunk_types:
            return None
        normalized = {entry.strip().lower() for entry in chunk_types if entry and entry.strip()}
        return normalized or None

    @staticmethod
    def _format_chunk_result(row: dict[str, object]) -> ChunkRetrievalResult:
        elem_ids = row.get("elem_ids") or []
        if not isinstance(elem_ids, list):
            elem_ids = []
        return ChunkRetrievalResult(
            chunk_id=int(row["chunk_id"]),
            doc_id=int(row["doc_id"]),
            collection_id=int(row["collection_id"]),
            order=row.get("order"),
            level_nav=row.get("level_nav"),
            chunk_type=str(row.get("chunk_type") or ""),
            chunk_text_main=row.get("chunk_text_main"),
            elem_ids=[int(elem_id) for elem_id in elem_ids if elem_id is not None],
            page_start=row.get("page_start"),
            page_end=row.get("page_end"),
            score=float(row.get("score") or 0.0),
        )


__all__ = ["Retriever", "ChunkRetrievalResult"]
