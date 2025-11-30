from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status

from ...env_setting import ENABLE_PAGE_CHUNK_RETRIEVAL, RETRIEVAL_TOPK_CHUNK, RETRIEVAL_TOPK_PAGE
from ...schemas import RetrievalEnvelope
from ...services.embedding import EmbeddingService
from ...services.retrieval import Retriever

router = APIRouter(tags=["retrieval"])


def get_retriever() -> Retriever:
    # Share EmbeddingService so repeated requests reuse HTTP session.
    service = EmbeddingService()
    return Retriever(embedding_service=service)


@router.get("/retrieval/test", response_model=RetrievalEnvelope)
def test_retrieval(
    *,
    collection_id: int = Query(..., ge=1, description="Target collection id."),
    query: str = Query(..., min_length=1, description="Query text used for embedding or keyword search."),
    top_k: int = Query(RETRIEVAL_TOPK_CHUNK, ge=1, le=50, description="Maximum number of chunk candidates to return."),
    doc_id: int | None = Query(None, ge=1, description="Optional document filter inside the collection."),
    chunk_types: str | None = Query(
        None,
        description="Comma separated chunk types (text,image,table).",
    ),
    search_mode: str = Query(
        "hybrid",
        description="Search mode: hybrid (default), vector, or fulltext.",
    ),
    enable_page_filter: bool = Query(
        ENABLE_PAGE_CHUNK_RETRIEVAL,
        description="Enable page-level filtering before chunk search.",
    ),
    page_top_k: int = Query(
        RETRIEVAL_TOPK_PAGE,
        ge=1,
        le=50,
        description="Page-level topK used when page filter is enabled.",
    ),
    retriever: Retriever = Depends(get_retriever),
) -> RetrievalEnvelope:
    chunk_type_list = _parse_chunk_types(chunk_types)
    try:
        results = retriever.retrieve_topk(
            collection_id=collection_id,
            query_text=query,
            top_k=top_k,
            doc_id=doc_id,
            chunk_types=chunk_type_list,
            search_mode=search_mode,
            enable_page_filter=enable_page_filter,
            page_top_k=page_top_k,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    return RetrievalEnvelope(code="OK", data=results)


def _parse_chunk_types(raw: str | None) -> list[str] | None:
    if raw is None:
        return None
    values = [entry.strip() for entry in raw.split(",") if entry.strip()]
    return values or None


__all__ = ["router"]
