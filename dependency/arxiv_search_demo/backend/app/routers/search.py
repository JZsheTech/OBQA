from __future__ import annotations

import logging
from fastapi import APIRouter, HTTPException

from .. import schemas
from ..utils.arxiv_client import ArxivSearchParams, search_arxiv

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/arxiv", tags=["arxiv"])


@router.post("/search", response_model=schemas.SearchResponse)
def arxiv_search(payload: schemas.SearchRequest):
    params = ArxivSearchParams(
        all_terms=payload.all_terms,
        title=payload.title,
        abstract=payload.abstract,
        author=payload.author,
        categories=payload.categories or None,
        date_mode=payload.date_mode,
        date_from=payload.date_from,
        date_to=payload.date_to,
        sort_by=payload.sort_by,
        sort_order=payload.sort_order,
        max_results=payload.max_results,
        id_list=payload.id_list or None,
    )

    try:
        results = search_arxiv(params)
        logger.info("arxiv search success", extra={"params": payload.model_dump()})
    except Exception as exc:  # noqa: BLE001
        logger.exception("arxiv search failed")
        raise HTTPException(status_code=502, detail="arXiv search failed") from exc

    return {"items": results}
