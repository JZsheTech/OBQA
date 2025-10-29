"""Document upload and indexing routes."""

from datetime import datetime
from typing import List

from fastapi import APIRouter, HTTPException, Path

from ...schemas import (
    DocumentListResponse,
    DocumentResponse,
    DocumentUploadRequest,
    IndexingRequest,
    IndexingResponse,
)

router = APIRouter(prefix="/collections/{collection_id}/documents", tags=["documents"])


def _example_document(collection_id: int, document_id: int) -> DocumentResponse:
    return DocumentResponse(
        id=document_id,
        collection_id=collection_id,
        title="Example Paper",
        file_name="example.pdf",
        file_path="/tmp/example.pdf",
        num_pages=12,
        created_at=datetime(2024, 1, 2, 0, 0, 0),
    )


@router.get("/", response_model=DocumentListResponse)
async def list_documents(collection_id: int = Path(..., ge=1)) -> DocumentListResponse:
    """List documents inside a collection."""

    items: List[DocumentResponse] = [_example_document(collection_id, 10)]
    return DocumentListResponse(items=items)


@router.post("/", response_model=DocumentResponse, status_code=201)
async def upload_document(
    payload: DocumentUploadRequest, collection_id: int = Path(..., ge=1)
) -> DocumentResponse:
    """Accept document metadata while uploads are stubbed."""

    return DocumentResponse(
        id=11,
        collection_id=collection_id,
        title=payload.title,
        file_name=payload.file_name,
        file_path=payload.file_path,
        num_pages=payload.num_pages,
        created_at=datetime.utcnow(),
    )


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    collection_id: int = Path(..., ge=1), document_id: int = Path(..., ge=1)
) -> DocumentResponse:
    """Return metadata for a single document."""

    if document_id != 10:
        raise HTTPException(status_code=404, detail="Document not found")
    return _example_document(collection_id, document_id)


@router.post(
    "/{document_id}/index",
    response_model=IndexingResponse,
    tags=["indexing"],
)
async def trigger_indexing(
    payload: IndexingRequest,
    collection_id: int = Path(..., ge=1),
    document_id: int = Path(..., ge=1),
) -> IndexingResponse:
    """Trigger an indexing job for a parsed document."""

    if document_id != 10:
        raise HTTPException(status_code=404, detail="Document not found")

    message = "Re-index scheduled" if payload.force else "Index scheduled"
    return IndexingResponse(document_id=document_id, accepted=True, message=message)
