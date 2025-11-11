from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class DocumentBase(BaseModel):
    title: str | None = None
    file_name: str | None = None
    file_path: str | None = None
    num_pages: int | None = None

    class Config:
        orm_mode = True


class DocumentCreate(DocumentBase):
    collection_id: int


class DocumentRead(DocumentBase):
    id: int
    collection_id: int
    created_at: datetime
