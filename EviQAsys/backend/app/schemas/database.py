"""Database record schemas mirroring the global OceanBase schema."""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class Collection(BaseModel):
    """Collection metadata grouped under the global namespace."""

    id: int
    name: str
    description: Optional[str] = None
    created_at: datetime


class Document(BaseModel):
    """Document stored under a collection."""

    id: int
    collection_id: int
    title: str
    file_name: str
    file_path: str
    num_pages: int
    created_at: datetime


class Element(BaseModel):
    """Individual parsed element originating from MinerU output."""

    id: int
    doc_id: int
    order: int = Field(..., ge=0, description="Reading order inside the document")
    elem_type: str
    section_name: Optional[str] = None
    level_nav: Optional[str] = None
    text_content: Optional[str] = None
    text_caption: Optional[str] = None
    image_base64: Optional[str] = None
    bbox_json: List[float]
    page_no: int
    vec_embedding: Optional[List[float]] = None


class Chat(BaseModel):
    """Chat session scoped to a collection."""

    id: int
    collection_id: int
    created_at: datetime
    title: Optional[str] = None
    max_evidence_no: int


class Turn(BaseModel):
    """Single question-answer exchange within a chat."""

    id: int
    chat_id: int
    order: int
    user_question: str
    llm_answer_text: Optional[str] = None
    llm_thought_text: Optional[str] = None
    created_at: datetime
    response_tokens: Optional[int] = None
    used_llm_model: Optional[str] = None


class TurnEvidence(BaseModel):
    """Mapping between turns and supporting document elements."""

    chat_id: int
    turn_id: int
    turn_order: int
    evidence_no: int
    element_id: int
    created_at: datetime
