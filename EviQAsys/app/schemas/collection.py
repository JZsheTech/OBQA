"""Collection schemas."""

from datetime import datetime
from typing import Optional

from pydantic import Field

from .base import ORMModel


class CollectionBase(ORMModel):
    name: str = Field(..., max_length=255)


class CollectionCreate(CollectionBase):
    pass


class CollectionUpdate(ORMModel):
    name: Optional[str] = Field(default=None, max_length=255)


class CollectionRead(CollectionBase):
    id: int
    created_at: datetime
