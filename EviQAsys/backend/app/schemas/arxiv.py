from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator


SortBy = Literal["relevance", "submittedDate", "lastUpdatedDate"]
SortOrder = Literal["ascending", "descending"]
DateMode = Literal["submitted", "updated"]


class ArxivPaper(BaseModel):
    arxiv_id: str
    version: str | None = None
    title: str
    summary: str | None = None
    authors: list[str] = Field(default_factory=list)
    primary_category: str | None = None
    categories: list[str] = Field(default_factory=list)
    pdf_url: str | None = None
    abs_url: str | None = None
    doi: str | None = None
    journal_ref: str | None = None
    published: datetime | None = None
    updated: datetime | None = None

    class Config:
        from_attributes = True


class ArxivSearchRequest(BaseModel):
    all_terms: str | None = None
    title: str | None = None
    abstract: str | None = None
    author: str | None = None
    categories: list[str] | None = None
    date_mode: DateMode | None = None
    date_from: date | None = None
    date_to: date | None = None
    sort_by: SortBy = "relevance"
    sort_order: SortOrder = "descending"
    max_results: int = 20
    id_list: list[str] | None = None

    @field_validator("max_results")
    @classmethod
    def clamp_max_results(cls, value: int) -> int:
        if value < 1:
            return 1
        return min(value, 50)


class ArxivSearchResponse(BaseModel):
    items: list[ArxivPaper]


class ArxivFavoriteCreate(BaseModel):
    paper: ArxivPaper
    tags: str | None = None
    note: str | None = None


class ArxivFavoriteUpdate(BaseModel):
    tags: str | None = None
    note: str | None = None


class ArxivFavoriteItem(ArxivPaper):
    id: int
    tags: str | None = None
    note: str | None = None
    document_id: int | None = None
    document_title: str | None = None
    document_collection_id: int | None = None
    created_at: datetime
    updated_at: datetime


class ArxivFavoriteList(BaseModel):
    items: list[ArxivFavoriteItem]
    page: int
    page_size: int
    total: int


class ArxivImportRequest(BaseModel):
    collection_id: int


class ArxivImportResponse(BaseModel):
    favorite_id: int
    document_id: int
    collection_id: int
    file_name: str | None = None
    status: str = "embedding_queued"
