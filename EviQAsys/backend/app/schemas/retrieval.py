from __future__ import annotations

from pydantic import BaseModel


class ChunkRetrievalCandidate(BaseModel):
    chunk_id: int
    doc_id: int
    collection_id: int
    order: int | None = None
    level_nav: str | None = None
    chunk_type: str
    page_start: int | None = None
    page_end: int | None = None
    elem_ids: list[int]
    score: float
    chunk_text_main: str | None = None


class RetrievalEnvelope(BaseModel):
    code: str = "OK"
    data: list[ChunkRetrievalCandidate]


__all__ = ["ChunkRetrievalCandidate", "RetrievalEnvelope"]
