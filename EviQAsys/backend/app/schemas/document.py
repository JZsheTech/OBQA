from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel


class DocumentBase(BaseModel):
    title: str | None = None
    abstract: str | None = None
    file_name: str | None = None
    file_path: str | None = None
    num_pages: int | None = None
    file_size_bytes: int | None = None
    element_count: int | None = None
    md_text: str | None = None
    meta_info: dict[str, Any] | None = None

    class Config:
        orm_mode = True


class DocumentCreate(DocumentBase):
    collection_id: int


class DocumentRead(DocumentBase):
    id: int
    collection_id: int
    created_at: datetime


class DocumentDetail(BaseModel):
    id: int
    collection_id: int
    collection_name: str | None = None
    title: str | None = None
    abstract: str | None = None
    file_name: str | None = None
    file_size_bytes: int | None = None
    num_pages: int | None = None
    element_count: int | None = None
    md_text: str | None = None
    meta_info: dict[str, Any] | None = None
    created_at: datetime
    parse_status: str


class DocumentListItem(BaseModel):
    id: int
    collection_id: int
    title: str | None = None
    abstract: str | None = None
    file_name: str | None = None
    file_size_bytes: int | None = None
    element_count: int | None = None
    num_pages: int | None = None
    created_at: datetime
    parse_status: str


class DocumentUploadResponse(BaseModel):
    doc_id: int
    file_name: str
    file_size_bytes: int
    status: str = "stored"
