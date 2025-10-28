"""Document endpoints."""

from typing import List, Optional

from fastapi import APIRouter, HTTPException, Response, status
from sqlalchemy import select

from app.api.deps import DBSession
from app import crud
from app.db import models
from app.schemas import DocumentCreate, DocumentRead, DocumentUpdate

router = APIRouter(prefix="/documents", tags=["documents"])


@router.get("/", response_model=List[DocumentRead])
def list_documents(
    db: DBSession,
    skip: int = 0,
    limit: int = 100,
    collection_id: Optional[int] = None,
) -> List[DocumentRead]:
    if collection_id is None:
        return crud.documents.list(db, skip=skip, limit=limit)

    stmt = (
        select(models.Document)
        .where(models.Document.collection_id == collection_id)
        .offset(skip)
        .limit(limit)
    )
    return list(db.execute(stmt).scalars().all())


@router.post("/", response_model=DocumentRead, status_code=status.HTTP_201_CREATED)
def create_document(payload: DocumentCreate, db: DBSession) -> DocumentRead:
    if crud.collections.get(db, payload.collection_id) is None:
        raise HTTPException(status_code=404, detail="Collection not found")
    return crud.documents.create(db, obj_in=payload)


@router.get("/{document_id}", response_model=DocumentRead)
def get_document(document_id: int, db: DBSession) -> DocumentRead:
    record = crud.documents.get(db, document_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Document not found")
    return record


@router.put("/{document_id}", response_model=DocumentRead)
def update_document(
    document_id: int, payload: DocumentUpdate, db: DBSession
) -> DocumentRead:
    record = crud.documents.get(db, document_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Document not found")
    return crud.documents.update(db, db_obj=record, obj_in=payload)


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(document_id: int, db: DBSession) -> Response:
    record = crud.documents.get(db, document_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Document not found")
    crud.documents.remove(db, db_obj=record)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
