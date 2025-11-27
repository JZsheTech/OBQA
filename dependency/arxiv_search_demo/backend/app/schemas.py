from __future__ import annotations

from datetime import datetime, date
from typing import List, Optional, Literal

from pydantic import BaseModel, Field, field_validator


SortBy = Literal["relevance", "submittedDate", "lastUpdatedDate"]
SortOrder = Literal["ascending", "descending"]
DateMode = Literal["submitted", "updated"]


class ArxivPaper(BaseModel):
    arxiv_id: str
    version: Optional[str] = None
    title: str
    summary: Optional[str] = None
    authors: List[str] = Field(default_factory=list)
    primary_category: Optional[str] = None
    categories: List[str] = Field(default_factory=list)
    published: Optional[datetime] = None
    updated: Optional[datetime] = None
    pdf_url: Optional[str] = None
    abs_url: Optional[str] = None
    doi: Optional[str] = None
    journal_ref: Optional[str] = None

    class Config:
        from_attributes = True


class SearchRequest(BaseModel):
    all_terms: Optional[str] = None
    title: Optional[str] = None
    abstract: Optional[str] = None
    author: Optional[str] = None
    categories: Optional[List[str]] = None
    date_mode: Optional[DateMode] = None
    date_from: Optional[date] = None
    date_to: Optional[date] = None
    sort_by: SortBy = "relevance"
    sort_order: SortOrder = "descending"
    max_results: int = 20
    id_list: Optional[List[str]] = None

    @field_validator("max_results")
    @classmethod
    def cap_max_results(cls, v: int) -> int:
        if v < 1:
            return 1
        return min(v, 50)


class SearchResponse(BaseModel):
    items: List[ArxivPaper]


class SavePaperRequest(BaseModel):
    paper: ArxivPaper
    tags: Optional[str] = None
    note: Optional[str] = None


class SavedPaper(BaseModel):
    id: int
    paper_id: int
    tags: Optional[str] = None
    note: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    paper: ArxivPaper

    class Config:
        from_attributes = True


class SavedListResponse(BaseModel):
    items: List[SavedPaper]
    page: int
    page_size: int
    total: int


class UpdateSavedRequest(BaseModel):
    tags: Optional[str] = None
    note: Optional[str] = None

