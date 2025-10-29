"""API request and response schemas for milestone 2 interfaces."""

from datetime import datetime
from typing import List, Optional, Sequence

from pydantic import BaseModel, Field, root_validator


class CollectionCreate(BaseModel):
    """Parameters required to create a collection."""

    name: str = Field(..., min_length=1)
    description: Optional[str] = Field(
        default=None, description="Optional description shown in dashboards."
    )


class CollectionUpdate(BaseModel):
    """Modifiable collection properties."""

    name: Optional[str] = Field(default=None, min_length=1)
    description: Optional[str] = None


class CollectionResponse(BaseModel):
    """Collection payload returned by API endpoints."""

    id: int
    name: str
    description: Optional[str]
    created_at: datetime


class CollectionListResponse(BaseModel):
    """Envelope returning multiple collections."""

    items: List[CollectionResponse]


class DocumentUploadRequest(BaseModel):
    """Metadata supplied when uploading a document.

    The actual file transfer will be handled via multipart/form-data in a
    later milestone; this model captures the metadata portion that the
    backend must persist even when uploads are mocked.
    """

    title: str
    file_name: str
    file_path: Optional[str] = Field(
        default=None,
        description="Temporary storage location or remote object key.",
    )
    num_pages: Optional[int] = Field(default=None, ge=1)


class DocumentResponse(BaseModel):
    """Document payload returned to clients."""

    id: int
    collection_id: int
    title: str
    file_name: str
    file_path: Optional[str]
    num_pages: Optional[int]
    created_at: datetime


class DocumentListResponse(BaseModel):
    """Envelope of documents scoped to a collection."""

    items: List[DocumentResponse]


class IndexingRequest(BaseModel):
    """Trigger indexing of a parsed document."""

    force: bool = Field(
        default=False,
        description=(
            "When true the backend should rebuild embeddings and overwrite existing "
            "index records."
        ),
    )


class IndexingResponse(BaseModel):
    """Acknowledges that an indexing job has been accepted."""

    document_id: int
    accepted: bool
    message: str


class ChatCreateRequest(BaseModel):
    """Parameters required to start a chat session."""

    title: Optional[str] = Field(default=None, description="Optional chat title")


class ChatResponse(BaseModel):
    """Chat payload returned to clients."""

    id: int
    collection_id: int
    created_at: datetime
    title: Optional[str]
    max_evidence_no: int


class ChatListResponse(BaseModel):
    """Envelope of chat summaries."""

    items: List[ChatResponse]


class EvidenceAnchor(BaseModel):
    """Reference to an evidence element used in an answer."""

    evidence_no: int = Field(..., ge=1)
    element_id: int
    page_no: int = Field(..., ge=1)
    bbox: Sequence[float] = Field(
        ..., min_length=4, max_length=4, description="Bounding box [x0, y0, x1, y1]."
    )
    section_name: Optional[str] = None
    label: Optional[str] = Field(
        default=None, description="Pre-formatted tag such as [Evidence#1]."
    )

    @root_validator(pre=False)
    def default_label(cls, values: dict) -> dict:
        label = values.get("label")
        evidence_no = values.get("evidence_no")
        if label is None and evidence_no is not None:
            values["label"] = f"[Evidence#{evidence_no}]"
        return values


class AnswerPayload(BaseModel):
    """Answer returned for a chat turn."""

    turn_id: int
    answer_text: str
    evidences: List[EvidenceAnchor]


class TurnSubmitRequest(BaseModel):
    """User request to submit a new question in an existing chat."""

    question: str = Field(..., min_length=1)
    conversation_context: Optional[str] = Field(
        default=None,
        description="Optional UI-provided summary of the conversation so far.",
    )


class TurnResponse(BaseModel):
    """Response returned after submitting a chat turn."""

    chat_id: int
    turn_order: int
    user_question: str
    answer: AnswerPayload


class EvidenceListResponse(BaseModel):
    """Response payload for evidence lookup endpoints."""

    chat_id: int
    turn_id: int
    items: List[EvidenceAnchor]
