from __future__ import annotations

from pydantic import BaseModel, Field


class TurnCreateRequest(BaseModel):
    question: str = Field(..., min_length=1, description="User question text.")
    top_k: int | None = Field(
        default=None,
        ge=1,
        le=30,
        description="Optional override for retrieval TopK.",
    )
    enable_image_vqa: bool | None = Field(
        default=False,
        description="Enable expensive visual question answering path.",
    )
    enable_memory_summarizer: bool | None = Field(
        default=False,
        description="Enable DSPy MemorySummarizer; default uses raw recent history.",
    )


class EvidenceItem(BaseModel):
    element_id: int
    evidence_no: int | None = None
    document_id: int | None = None
    page_index: int | None = None
    bbox: list[float] | None = None
    elem_type: str
    snippet: str | None = None
    text_content: str | None = None
    title: str | None = None


class TurnResponse(BaseModel):
    turn_id: int
    chat_id: int
    answer_text: str
    evidences: list[EvidenceItem]


class TurnResponseEnvelope(BaseModel):
    code: str = "OK"
    data: TurnResponse


__all__ = ["TurnCreateRequest", "EvidenceItem", "TurnResponse", "TurnResponseEnvelope"]
