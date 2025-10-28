"""Document schemas."""

from datetime import datetime
from typing import Optional

from pydantic import Field

from .base import ORMModel


class DocumentBase(ORMModel):
    collection_id: int
    file_name: str = Field(..., max_length=255)
    file_path: str = Field(..., max_length=1024)
    num_pages: Optional[int] = Field(default=None, ge=0)


class DocumentCreate(DocumentBase):
    pass


class DocumentUpdate(ORMModel):
    file_name: Optional[str] = Field(default=None, max_length=255)
    file_path: Optional[str] = Field(default=None, max_length=1024)
    num_pages: Optional[int] = Field(default=None, ge=0)


class DocumentRead(DocumentBase):
    id: int
    created_at: datetime
