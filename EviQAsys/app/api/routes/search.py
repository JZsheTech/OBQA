"""Search endpoints (placeholder for Stage 2 vector search)."""

from fastapi import APIRouter

from app.schemas import SearchRequest, SearchResponse

router = APIRouter(prefix="/search", tags=["search"])


@router.post("/elements", response_model=SearchResponse)
def search_elements(payload: SearchRequest) -> SearchResponse:
    # Stage 0 placeholder: respond with empty results while plumbing is prepared.
    return SearchResponse(query=payload.query, top_k=payload.top_k, results=[])
