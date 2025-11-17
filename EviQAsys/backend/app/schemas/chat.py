from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class ChatBase(BaseModel):
    title: str | None = None
    max_turn_order: int = 0

    class Config:
        orm_mode = True


class ChatCreate(ChatBase):
    collection_id: int


class ChatRead(ChatBase):
    id: int
    collection_id: int
    created_at: datetime
