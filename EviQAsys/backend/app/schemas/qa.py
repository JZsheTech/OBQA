from __future__ import annotations

from datetime import datetime

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
    answer_with_evidence: str | None = None


class TurnResponseEnvelope(BaseModel):
    code: str = "OK"
    data: TurnResponse


class TurnWithEvidence(BaseModel):
    id: int
    chat_id: int
    order: int
    user_question: str | None = None
    answer_text: str | None = None
    answer_with_evidence: str | None = None
    created_at: datetime
    evidences: list[EvidenceItem]


class ChatDetail(BaseModel):
    id: int
    collection_id: int | None = None
    document_id: int | None = None
    type: str
    title: str | None = None
    max_turn_order: int = 0
    created_at: datetime
    turns: list[TurnWithEvidence]
    evidence_no_mapping: dict[int, int]


class ChatDetailEnvelope(BaseModel):
    code: str = "OK"
    data: ChatDetail


class TurnEvidencesResponse(BaseModel):
    chat_id: int
    turn_id: int
    evidence_no_mapping: dict[int, int]
    evidences: list[EvidenceItem]


class TurnEvidencesEnvelope(BaseModel):
    code: str = "OK"
    data: TurnEvidencesResponse


__all__ = [
    "TurnCreateRequest",
    "EvidenceItem",
    "TurnResponse",
    "TurnResponseEnvelope",
    "TurnWithEvidence",
    "ChatDetail",
    "ChatDetailEnvelope",
    "TurnEvidencesResponse",
    "TurnEvidencesEnvelope",
]
