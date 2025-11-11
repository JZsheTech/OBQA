from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class CollectionBase(BaseModel):
    name: str
    description: str | None = None

    class Config:
        orm_mode = True


class CollectionCreate(CollectionBase):
    """Payload used when creating a new collection."""


class CollectionRead(CollectionBase):
    id: int
    created_at: datetime
