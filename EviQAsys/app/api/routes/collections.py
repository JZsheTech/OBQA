"""Collection endpoints."""

from typing import List

from fastapi import APIRouter, HTTPException, Response, status

from app.api.deps import DBSession
from app import crud
from app.schemas import CollectionCreate, CollectionRead, CollectionUpdate

router = APIRouter(prefix="/collections", tags=["collections"])


@router.get("/", response_model=List[CollectionRead])
def list_collections(
    db: DBSession,
    skip: int = 0,
    limit: int = 100,
) -> List[CollectionRead]:
    return crud.collections.list(db, skip=skip, limit=limit)


@router.post(
    "/", response_model=CollectionRead, status_code=status.HTTP_201_CREATED
)
def create_collection(payload: CollectionCreate, db: DBSession) -> CollectionRead:
    return crud.collections.create(db, obj_in=payload)


@router.get("/{collection_id}", response_model=CollectionRead)
def get_collection(collection_id: int, db: DBSession) -> CollectionRead:
    record = crud.collections.get(db, collection_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Collection not found")
    return record


@router.put("/{collection_id}", response_model=CollectionRead)
def update_collection(
    collection_id: int, payload: CollectionUpdate, db: DBSession
) -> CollectionRead:
    record = crud.collections.get(db, collection_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Collection not found")
    return crud.collections.update(db, db_obj=record, obj_in=payload)


@router.delete("/{collection_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_collection(collection_id: int, db: DBSession) -> Response:
    record = crud.collections.get(db, collection_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Collection not found")
    crud.collections.remove(db, db_obj=record)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
