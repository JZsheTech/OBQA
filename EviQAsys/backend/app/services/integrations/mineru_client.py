"""Lightweight wrapper around the MinerU parsing demo service."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from pydantic import BaseModel, Field


class MinerUContentBlock(BaseModel):
    """Represents a single item returned by MinerU's `content_list`."""

    order: int = Field(..., ge=0)
    type: str = Field(..., description="Element type such as text/image/table")
    section_name: Optional[str] = None
    level_nav: Optional[str] = None
    text_content: Optional[str] = None
    text_caption: Optional[str] = None
    image_base64: Optional[str] = None
    bbox: List[float] = Field(
        default_factory=list,
        description="Normalized bounding box [x0, y0, x1, y1]",
    )
    page_no: int = Field(..., ge=1)


class MinerUParseRequest(BaseModel):
    """Payload sent to the MinerU parsing service."""

    file_path: str = Field(..., description="Location of the uploaded PDF")
    file_name: str
    collection_id: Optional[int] = Field(
        default=None, description="Collection used to scope downstream storage."
    )


class MinerUParseResponse(BaseModel):
    """Subset of MinerU response used by downstream stages."""

    doc_uuid: str
    content_list: List[MinerUContentBlock]
    md_text: str


@dataclass
class MinerUClient:
    """Sequential client performing blocking MinerU parse requests."""

    endpoint: str

    def parse_pdf(self, payload: MinerUParseRequest) -> MinerUParseResponse:
        """Call the MinerU demo API and return a structured response.

        The milestone implementation returns deterministic stub data so that
        downstream services can be developed without external dependencies.
        """

        sample_block = MinerUContentBlock(
            order=0,
            type="text",
            section_name="Abstract",
            level_nav="1",
            text_content="This paper introduces the OBQA pipeline.",
            bbox=[0.1, 0.1, 0.9, 0.2],
            page_no=1,
        )
        return MinerUParseResponse(
            doc_uuid="stub-doc-uuid",
            content_list=[sample_block],
            md_text="# Abstract\n\nThis paper introduces the OBQA pipeline.",
        )
