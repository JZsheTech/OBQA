from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from .. import schemas
from ..database import get_db
from ..repositories import (
    delete_saved,
    get_saved_with_paper,
    list_saved,
    save_paper,
    saved_to_schema,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/papers", tags=["papers"])


@router.post("/save", response_model=schemas.SavedPaper, status_code=status.HTTP_201_CREATED)
def save_paper_endpoint(
    payload: schemas.SavePaperRequest,
    db: Session = Depends(get_db),
):
    saved = save_paper(db, payload.paper, payload.tags, payload.note)
    db.commit()
    db.refresh(saved)
    logger.info("paper saved", extra={"arxiv_id": payload.paper.arxiv_id})
    return saved_to_schema(saved)


@router.get("/saved", response_model=schemas.SavedListResponse)
def list_saved_endpoint(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=50),
    keyword: Optional[str] = None,
    author: Optional[str] = None,
    category: Optional[str] = None,
    tag: Optional[str] = None,
    sort_by: str = Query("created_at", pattern="^(created_at|published|updated)$"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$"),
    db: Session = Depends(get_db),
):
    items, total = list_saved(
        db=db,
        page=page,
        page_size=page_size,
        keyword=keyword,
        author=author,
        category=category,
        tag=tag,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    return schemas.SavedListResponse(
        items=[saved_to_schema(i) for i in items],
        page=page,
        page_size=page_size,
        total=total,
    )


@router.get("/{saved_id}", response_model=schemas.SavedPaper)
def get_saved_endpoint(saved_id: int, db: Session = Depends(get_db)):
    saved = get_saved_with_paper(db, saved_id)
    if not saved:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Saved paper not found")
    return saved_to_schema(saved)


@router.patch("/{saved_id}", response_model=schemas.SavedPaper)
def update_saved_endpoint(
    saved_id: int,
    payload: schemas.UpdateSavedRequest,
    db: Session = Depends(get_db),
):
    saved = get_saved_with_paper(db, saved_id)
    if not saved:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Saved paper not found")

    if payload.tags is not None:
        saved.tags = payload.tags
    if payload.note is not None:
        saved.note = payload.note

    db.commit()
    db.refresh(saved)
    return saved_to_schema(saved)


@router.delete("/{saved_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_saved_endpoint(saved_id: int, db: Session = Depends(get_db)):
    saved = get_saved_with_paper(db, saved_id)
    if not saved:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Saved paper not found")

    delete_saved(db, saved)
    db.commit()
    return None

