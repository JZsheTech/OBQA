from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class TurnCreateRequest(BaseModel):
    question: str = Field(..., min_length=1, description="User question text.")
    use_image: bool | None = Field(default=None, description="Enable image retrieval + multimodal answer.")
    text_retrieve_topk: int | None = Field(default=None, ge=1, le=20, description="Text chunk retrieval TopK.")
    image_retrieve_topk: int | None = Field(default=None, ge=1, le=20, description="Image chunk retrieval TopK.")
    text_memory_topk: int | None = Field(default=None, ge=1, le=20, description="Memory text elements TopK.")
    image_memory_topk: int | None = Field(default=None, ge=1, le=20, description="Memory image elements TopK.")
    use_page_in_text_retrieve: bool | None = Field(default=None, description="Enable page-level filter for text retrieval.")
    page_retrieve_topk: int | None = Field(default=None, ge=1, le=20, description="Page-level TopK when filter is enabled.")
    text_search_mode: Literal["vector", "fulltext", "hybrid"] | None = Field(
        default=None,
        description="Search backend selection for text retrieval (vector/fulltext/hybrid).",
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
    evidence_map: dict[str, int] | None = None
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


class QAConfigDefaults(BaseModel):
    use_image: bool
    text_retrieve_topk: int
    image_retrieve_topk: int
    text_memory_topk: int
    image_memory_topk: int
    use_page_in_text_retrieve: bool
    page_retrieve_topk: int
    text_search_mode: Literal["vector", "fulltext", "hybrid"]


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
    qa_config_defaults: QAConfigDefaults | None = None


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
    "QAConfigDefaults",
]
