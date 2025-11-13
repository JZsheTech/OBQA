from __future__ import annotations

from pydantic import BaseModel


class RetrievalCandidate(BaseModel):
    element_id: int
    doc_id: int
    collection_id: int
    page_no: int | None = None
    bbox: list[float] | None = None
    elem_type: str
    score: float
    text_content: str | None = None


class RetrievalEnvelope(BaseModel):
    code: str = "OK"
    data: list[RetrievalCandidate]


__all__ = ["RetrievalCandidate", "RetrievalEnvelope"]
