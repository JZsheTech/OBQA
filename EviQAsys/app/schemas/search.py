"""Search request/response schemas."""

from typing import List, Optional

from pydantic import BaseModel, Field


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1)
    top_k: int = Field(default=5, ge=1, le=50)
    collection_id: Optional[int] = None
    elem_types: Optional[List[str]] = None


class SearchResult(BaseModel):
    element_id: int
    score: float
    elem_type: str
    snippet: Optional[str] = None


class SearchResponse(BaseModel):
    query: str
    top_k: int
    results: List[SearchResult]
