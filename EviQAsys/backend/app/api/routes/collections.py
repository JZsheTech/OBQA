from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from ...repositories import CollectionsRepository
from ...schemas import CollectionRead

router = APIRouter(tags=["collections"])


class CollectionsEnvelope(BaseModel):
    code: str = "OK"
    data: list[CollectionRead]

    class Config:
        arbitrary_types_allowed = True


def get_collections_repo() -> CollectionsRepository:
    return CollectionsRepository()


@router.get("/collections", response_model=CollectionsEnvelope)
def list_collections(repo: CollectionsRepository = Depends(get_collections_repo)) -> CollectionsEnvelope:
    collections = repo.list_collections()
    return CollectionsEnvelope(code="OK", data=collections)
