from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, field_validator, model_validator


class ChatBase(BaseModel):
    title: str | None = None
    max_turn_order: int = 0
    type: str = "collection"
    document_id: int | None = None

    @field_validator("type", mode="before")
    def normalize_type(cls, value: str | None) -> str:
        chat_type = (value or "collection").strip().lower()
        if chat_type not in {"collection", "document"}:
            raise ValueError("type must be 'collection' or 'document'.")
        return chat_type

    model_config = ConfigDict(from_attributes=True)


class ChatCreate(ChatBase):
    collection_id: int | None = None

    @model_validator(mode="after")
    def validate_scope(cls, model: "ChatCreate") -> "ChatCreate":
        chat_type = model.type or "collection"
        if chat_type == "collection":
            if model.collection_id is None:
                raise ValueError("collection_id is required when type is 'collection'.")
            model.document_id = None
        elif chat_type == "document":
            if model.document_id is None:
                raise ValueError("document_id is required when type is 'document'.")
            model.collection_id = None
        return model


class ChatRead(ChatBase):
    id: int
    collection_id: int | None = None
    created_at: datetime
