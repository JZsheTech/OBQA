from __future__ import annotations

import logging
from typing import Literal

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from pydantic import BaseModel

from ...repositories import ArxivFavoritesRepository
from ...schemas import (
    ArxivFavoriteCreate,
    ArxivFavoriteItem,
    ArxivFavoriteList,
    ArxivFavoriteUpdate,
    ArxivImportRequest,
    ArxivImportResponse,
    ArxivPaper,
    ArxivSearchRequest,
    ArxivSearchResponse,
)
from ...services.index import DocumentIndexer
from ...services.ingestion import DuplicateDocumentError
from ...services.integrations import ArxivImportService, ArxivSearchParams, search_arxiv

router = APIRouter(tags=["arxiv"])
logger = logging.getLogger(__name__)


class SearchEnvelope(BaseModel):
    code: str = "OK"
    data: ArxivSearchResponse


class FavoriteEnvelope(BaseModel):
    code: str = "OK"
    data: ArxivFavoriteItem


class FavoriteListEnvelope(BaseModel):
    code: str = "OK"
    data: ArxivFavoriteList


class ImportEnvelope(BaseModel):
    code: str = "OK"
    data: ArxivImportResponse


def get_favorites_repo() -> ArxivFavoritesRepository:
    return ArxivFavoritesRepository()


def get_import_service() -> ArxivImportService:
    return ArxivImportService()


def get_document_indexer() -> DocumentIndexer:
    return DocumentIndexer()


@router.post("/arxiv/search", response_model=SearchEnvelope)
def arxiv_search(payload: ArxivSearchRequest) -> SearchEnvelope:
    params = ArxivSearchParams(
        all_terms=payload.all_terms,
        title=payload.title,
        abstract=payload.abstract,
        author=payload.author,
        categories=payload.categories or [],
        date_mode=payload.date_mode,
        date_from=payload.date_from,
        date_to=payload.date_to,
        sort_by=payload.sort_by,
        sort_order=payload.sort_order,
        max_results=payload.max_results,
        id_list=payload.id_list or [],
    )
    try:
        results = search_arxiv(params)
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc
    papers = [ArxivPaper(**item) for item in results]
    return SearchEnvelope(code="OK", data=ArxivSearchResponse(items=papers))


@router.post(
    "/arxiv/favorites",
    response_model=FavoriteEnvelope,
    status_code=status.HTTP_201_CREATED,
)
def save_favorite(
    payload: ArxivFavoriteCreate,
    repo: ArxivFavoritesRepository = Depends(get_favorites_repo),
) -> FavoriteEnvelope:
    paper = payload.paper
    favorite = repo.upsert_favorite(
        arxiv_id=paper.arxiv_id,
        version=paper.version,
        title=paper.title,
        summary=paper.summary,
        authors=paper.authors,
        primary_category=paper.primary_category,
        categories=paper.categories,
        pdf_url=paper.pdf_url,
        abs_url=paper.abs_url,
        doi=paper.doi,
        journal_ref=paper.journal_ref,
        tags=payload.tags,
        note=payload.note,
        published=paper.published,
        updated=paper.updated,
    )
    return FavoriteEnvelope(code="OK", data=ArxivFavoriteItem(**favorite))


@router.get("/arxiv/favorites", response_model=FavoriteListEnvelope)
def list_favorites(
    repo: ArxivFavoritesRepository = Depends(get_favorites_repo),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    keyword: str | None = Query(default=None, description="Keyword search for title/summary"),
    author: str | None = Query(default=None, description="Filter by author substring"),
    category: str | None = Query(default=None, description="Filter by category substring"),
    tag: str | None = Query(default=None, description="Filter by tags substring"),
    sort_by: Literal["created_at", "published", "updated"] = Query(default="created_at"),
    sort_order: Literal["asc", "desc"] = Query(default="desc"),
) -> FavoriteListEnvelope:
    items, total = repo.list_favorites(
        page=page,
        page_size=page_size,
        keyword=keyword,
        author=author,
        category=category,
        tag=tag,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    payload = ArxivFavoriteList(
        items=[ArxivFavoriteItem(**item) for item in items],
        page=page,
        page_size=page_size,
        total=total,
    )
    return FavoriteListEnvelope(code="OK", data=payload)


@router.get("/arxiv/favorites/{favorite_id}", response_model=FavoriteEnvelope)
def get_favorite(
    favorite_id: int,
    repo: ArxivFavoritesRepository = Depends(get_favorites_repo),
) -> FavoriteEnvelope:
    favorite = repo.get_by_id(favorite_id)
    if not favorite:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Favorite not found.")
    return FavoriteEnvelope(code="OK", data=ArxivFavoriteItem(**favorite))


@router.patch("/arxiv/favorites/{favorite_id}", response_model=FavoriteEnvelope)
def update_favorite(
    favorite_id: int,
    payload: ArxivFavoriteUpdate,
    repo: ArxivFavoritesRepository = Depends(get_favorites_repo),
) -> FavoriteEnvelope:
    existing = repo.get_by_id(favorite_id)
    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Favorite not found.")
    if payload.tags is None and payload.note is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one of tags or note must be provided.",
        )
    repo.update_favorite(favorite_id, tags=payload.tags, note=payload.note)
    refreshed = repo.get_by_id(favorite_id)
    return FavoriteEnvelope(code="OK", data=ArxivFavoriteItem(**(refreshed or existing)))


@router.delete("/arxiv/favorites/{favorite_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_favorite(
    favorite_id: int,
    repo: ArxivFavoritesRepository = Depends(get_favorites_repo),
) -> None:
    existing = repo.get_by_id(favorite_id)
    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Favorite not found.")
    repo.delete_favorite(favorite_id)


@router.post(
    "/arxiv/favorites/{favorite_id}/import",
    response_model=ImportEnvelope,
    status_code=status.HTTP_201_CREATED,
)
def import_favorite(
    favorite_id: int,
    payload: ArxivImportRequest,
    background_tasks: BackgroundTasks,
    service: ArxivImportService = Depends(get_import_service),
    indexer: DocumentIndexer = Depends(get_document_indexer),
) -> ImportEnvelope:
    try:
        document = service.import_to_collection(
            favorite_id=favorite_id,
            collection_id=payload.collection_id,
        )
    except DuplicateDocumentError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    except ValueError as exc:
        detail = str(exc)
        status_code = (
            status.HTTP_409_CONFLICT
            if "already imported" in detail.lower()
            else status.HTTP_400_BAD_REQUEST
        )
        raise HTTPException(status_code=status_code, detail=detail) from exc
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc

    _enqueue_embedding_task(
        background_tasks,
        indexer,
        collection_id=document["collection_id"],
        doc_id=document["id"],
    )
    response = ArxivImportResponse(
        favorite_id=favorite_id,
        document_id=document["id"],
        collection_id=document["collection_id"],
        file_name=document.get("file_name"),
        status="embedding_queued",
    )
    return ImportEnvelope(code="OK", data=response)


def _enqueue_embedding_task(
    background_tasks: BackgroundTasks,
    indexer: DocumentIndexer,
    *,
    collection_id: int,
    doc_id: int,
) -> None:
    def _run() -> None:
        try:
            embedded = indexer.embed_document(collection_id=collection_id, doc_id=doc_id)
            logger.info(
                "Background embedding complete doc_id=%s collection_id=%s count=%s",
                doc_id,
                collection_id,
                embedded,
            )
        except Exception:
            logger.exception("Background embedding failed for doc_id=%s collection_id=%s", doc_id, collection_id)

    background_tasks.add_task(_run)


__all__ = ["router"]
