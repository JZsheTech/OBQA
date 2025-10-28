"""Element endpoints."""

from typing import List, Optional

from fastapi import APIRouter, HTTPException, Response, status
from sqlalchemy import select

from app.api.deps import DBSession
from app import crud
from app.db import models
from app.schemas import ElementCreate, ElementRead, ElementUpdate

router = APIRouter(prefix="/elements", tags=["elements"])


@router.get("/", response_model=List[ElementRead])
def list_elements(
    db: DBSession,
    skip: int = 0,
    limit: int = 100,
    document_id: Optional[int] = None,
    elem_type: Optional[str] = None,
) -> List[ElementRead]:
    stmt = select(models.Element).offset(skip).limit(limit)
    if document_id is not None:
        stmt = stmt.where(models.Element.document_id == document_id)
    if elem_type is not None:
        stmt = stmt.where(models.Element.elem_type == elem_type)
    return list(db.execute(stmt).scalars().all())


@router.post("/", response_model=ElementRead, status_code=status.HTTP_201_CREATED)
def create_element(payload: ElementCreate, db: DBSession) -> ElementRead:
    if crud.documents.get(db, payload.document_id) is None:
        raise HTTPException(status_code=404, detail="Document not found")
    return crud.elements.create(db, obj_in=payload)


@router.get("/{element_id}", response_model=ElementRead)
def get_element(element_id: int, db: DBSession) -> ElementRead:
    record = crud.elements.get(db, element_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Element not found")
    return record


@router.put("/{element_id}", response_model=ElementRead)
def update_element(
    element_id: int, payload: ElementUpdate, db: DBSession
) -> ElementRead:
    record = crud.elements.get(db, element_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Element not found")
    return crud.elements.update(db, db_obj=record, obj_in=payload)


@router.delete("/{element_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_element(element_id: int, db: DBSession) -> Response:
    record = crud.elements.get(db, element_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Element not found")
    crud.elements.remove(db, db_obj=record)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
