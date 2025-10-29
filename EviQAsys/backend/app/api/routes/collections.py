"""Collection CRUD routes exposing contract-first responses."""

from datetime import datetime
from typing import List

from fastapi import APIRouter, HTTPException, Path

from ...schemas import (
    CollectionCreate,
    CollectionListResponse,
    CollectionResponse,
    CollectionUpdate,
)

router = APIRouter(prefix="/collections", tags=["collections"])


def _example_collection(collection_id: int) -> CollectionResponse:
    """Return a deterministic example collection payload."""

    return CollectionResponse(
        id=collection_id,
        name="Sample Collection",
        description="Stub collection used during interface validation.",
        created_at=datetime(2024, 1, 1, 0, 0, 0),
    )


@router.get("/", response_model=CollectionListResponse)
async def list_collections() -> CollectionListResponse:
    """List collections currently available.

    During Milestone 2 the route returns deterministic stub data so the
    frontend can be implemented against a stable contract.
    """

    items: List[CollectionResponse] = [_example_collection(1)]
    return CollectionListResponse(items=items)


@router.post("/", response_model=CollectionResponse, status_code=201)
async def create_collection(payload: CollectionCreate) -> CollectionResponse:
    """Create a new collection entry.

    The response echoes the payload with a mocked identifier so that client
    logic can be exercised prior to full persistence wiring.
    """

    return CollectionResponse(
        id=2,
        name=payload.name,
        description=payload.description,
        created_at=datetime.utcnow(),
    )


@router.get("/{collection_id}", response_model=CollectionResponse)
async def get_collection(collection_id: int = Path(..., ge=1)) -> CollectionResponse:
    """Retrieve a single collection by identifier."""

    if collection_id != 1:
        raise HTTPException(status_code=404, detail="Collection not found")
    return _example_collection(collection_id)


@router.put("/{collection_id}", response_model=CollectionResponse)
async def update_collection(
    payload: CollectionUpdate, collection_id: int = Path(..., ge=1)
) -> CollectionResponse:
    """Update a collection's mutable fields."""

    if collection_id != 1:
        raise HTTPException(status_code=404, detail="Collection not found")

    example = _example_collection(collection_id)
    return CollectionResponse(
        id=example.id,
        name=payload.name or example.name,
        description=payload.description or example.description,
        created_at=example.created_at,
    )


@router.delete("/{collection_id}", status_code=204)
async def delete_collection(collection_id: int = Path(..., ge=1)) -> None:
    """Delete a collection (stubbed)."""

    if collection_id != 1:
        raise HTTPException(status_code=404, detail="Collection not found")

    return None
