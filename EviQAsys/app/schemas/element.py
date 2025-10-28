"""Element schemas."""

from datetime import datetime
from typing import List, Optional

from pydantic import Field

from .base import ORMModel


class ElementBase(ORMModel):
    document_id: int = Field(..., alias="doc_id")
    elem_type: str = Field(..., max_length=50)
    section_name: Optional[str] = Field(default=None, max_length=255)
    level_nav: Optional[str] = Field(default=None, max_length=255)
    text_content: Optional[str] = None
    text_caption: Optional[str] = None
    image_base64: Optional[str] = None
    bbox_json: Optional[str] = None
    page_no: Optional[int] = Field(default=None, ge=1)
    vec_embedding: Optional[List[float]] = None

    class Config(ORMModel.Config):
        allow_population_by_field_name = True


class ElementCreate(ElementBase):
    pass


class ElementUpdate(ORMModel):
    elem_type: Optional[str] = Field(default=None, max_length=50)
    section_name: Optional[str] = Field(default=None, max_length=255)
    level_nav: Optional[str] = Field(default=None, max_length=255)
    text_content: Optional[str] = None
    text_caption: Optional[str] = None
    image_base64: Optional[str] = None
    bbox_json: Optional[str] = None
    page_no: Optional[int] = Field(default=None, ge=1)
    vec_embedding: Optional[List[float]] = None


class ElementRead(ElementBase):
    id: int
    created_at: datetime
