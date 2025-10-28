"""Chat schemas."""

from datetime import datetime

from .base import ORMModel


class ChatBase(ORMModel):
    collection_id: int


class ChatCreate(ChatBase):
    pass


class ChatUpdate(ORMModel):
    collection_id: int


class ChatRead(ChatBase):
    id: int
    created_at: datetime
