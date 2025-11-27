from __future__ import annotations

import json
from typing import List, Optional, Tuple

from sqlalchemy import or_, desc, asc
from sqlalchemy.orm import Session

from . import schemas
from .models import Paper, SavedPaper


def _dumps_list(data: Optional[List[str]]) -> str:
    return json.dumps(data or [], ensure_ascii=False)


def _loads_list(data: Optional[str]) -> List[str]:
    if not data:
        return []
    try:
        return json.loads(data)
    except json.JSONDecodeError:
        return []


def paper_to_schema(paper: Paper) -> schemas.ArxivPaper:
    return schemas.ArxivPaper(
        arxiv_id=paper.arxiv_id,
        version=paper.version,
        title=paper.title,
        summary=paper.summary,
        authors=_loads_list(paper.authors),
        primary_category=paper.primary_category,
        categories=_loads_list(paper.categories),
        published=paper.published,
        updated=paper.updated,
        pdf_url=paper.pdf_url,
        abs_url=paper.abs_url,
        doi=paper.doi,
        journal_ref=paper.journal_ref,
    )


def saved_to_schema(saved: SavedPaper) -> schemas.SavedPaper:
    return schemas.SavedPaper(
        id=saved.id,
        paper_id=saved.paper_id,
        tags=saved.tags,
        note=saved.note,
        created_at=saved.created_at,
        updated_at=saved.updated_at,
        paper=paper_to_schema(saved.paper),
    )


def upsert_paper(db: Session, payload: schemas.ArxivPaper) -> Paper:
    paper = db.query(Paper).filter(Paper.arxiv_id == payload.arxiv_id).first()
    if not paper:
        paper = Paper(arxiv_id=payload.arxiv_id)
        db.add(paper)

    paper.version = payload.version
    paper.title = payload.title
    paper.summary = payload.summary
    paper.authors = _dumps_list(payload.authors)
    paper.primary_category = payload.primary_category
    paper.categories = _dumps_list(payload.categories)
    paper.published = payload.published
    paper.updated = payload.updated
    paper.pdf_url = payload.pdf_url
    paper.abs_url = payload.abs_url
    paper.doi = payload.doi
    paper.journal_ref = payload.journal_ref

    return paper


def save_paper(
    db: Session,
    payload: schemas.ArxivPaper,
    tags: Optional[str],
    note: Optional[str],
) -> SavedPaper:
    paper = upsert_paper(db, payload)
    db.flush()  # ensure paper.id is available

    saved = db.query(SavedPaper).filter(SavedPaper.paper_id == paper.id).first()
    if not saved:
        saved = SavedPaper(paper_id=paper.id)
        db.add(saved)

    if tags is not None:
        saved.tags = tags
    if note is not None:
        saved.note = note

    db.flush()
    return saved


def get_saved_with_paper(db: Session, saved_id: int) -> Optional[SavedPaper]:
    return (
        db.query(SavedPaper)
        .join(Paper)
        .filter(SavedPaper.id == saved_id)
        .first()
    )


def list_saved(
    db: Session,
    page: int,
    page_size: int,
    keyword: Optional[str] = None,
    author: Optional[str] = None,
    category: Optional[str] = None,
    tag: Optional[str] = None,
    sort_by: str = "created_at",
    sort_order: str = "desc",
) -> Tuple[List[SavedPaper], int]:
    query = db.query(SavedPaper).join(Paper)

    if keyword:
        pattern = f"%{keyword}%"
        query = query.filter(
            or_(
                Paper.title.ilike(pattern),
                Paper.summary.ilike(pattern),
            )
        )

    if author:
        pattern = f"%{author}%"
        query = query.filter(Paper.authors.ilike(pattern))

    if category:
        pattern = f"%{category}%"
        query = query.filter(Paper.categories.ilike(pattern))

    if tag:
        pattern = f"%{tag}%"
        query = query.filter(SavedPaper.tags.ilike(pattern))

    if sort_by == "published":
        sort_field = Paper.published
    elif sort_by == "updated":
        sort_field = Paper.updated
    else:
        sort_field = SavedPaper.created_at

    sort_fn = desc if sort_order == "desc" else asc
    query = query.order_by(sort_fn(sort_field))

    total = query.count()
    offset = (page - 1) * page_size
    items = query.offset(offset).limit(page_size).all()
    return items, total


def delete_saved(db: Session, saved: SavedPaper) -> None:
    db.delete(saved)
    db.flush()

