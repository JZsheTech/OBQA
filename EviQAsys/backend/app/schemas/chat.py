from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, root_validator, validator


class ChatBase(BaseModel):
    title: str | None = None
    max_turn_order: int = 0
    type: str = "collection"
    document_id: int | None = None

    @validator("type", pre=True, always=True)
    def normalize_type(cls, value: str | None) -> str:
        chat_type = (value or "collection").strip().lower()
        if chat_type not in {"collection", "document"}:
            raise ValueError("type must be 'collection' or 'document'.")
        return chat_type

    class Config:
        orm_mode = True


class ChatCreate(ChatBase):
    collection_id: int | None = None

    @root_validator
    def validate_scope(cls, values: dict[str, object]) -> dict[str, object]:
        chat_type = values.get("type") or "collection"
        collection_id = values.get("collection_id")
        document_id = values.get("document_id")
        if chat_type == "collection":
            if collection_id is None:
                raise ValueError("collection_id is required when type is 'collection'.")
            values["document_id"] = None
        elif chat_type == "document":
            if document_id is None:
                raise ValueError("document_id is required when type is 'document'.")
            values["collection_id"] = None
        return values


class ChatRead(ChatBase):
    id: int
    collection_id: int | None = None
    created_at: datetime
