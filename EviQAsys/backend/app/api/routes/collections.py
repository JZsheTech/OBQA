from __future__ import annotations

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from pydantic import BaseModel

from ...repositories import CollectionsRepository, DocumentsRepository
from ...schemas import CollectionRead, DocumentListItem, DocumentUploadResponse
from ...services.ingestion import DocumentIngestor, DuplicateDocumentError

router = APIRouter(tags=["collections"])


class CollectionsEnvelope(BaseModel):
    code: str = "OK"
    data: list[CollectionRead]

    class Config:
        arbitrary_types_allowed = True


class DocumentsEnvelope(BaseModel):
    code: str = "OK"
    data: list[DocumentListItem]


class DocumentUploadEnvelope(BaseModel):
    code: str = "OK"
    data: DocumentUploadResponse


def get_collections_repo() -> CollectionsRepository:
    return CollectionsRepository()


def get_documents_repo() -> DocumentsRepository:
    return DocumentsRepository()


def get_document_ingestor() -> DocumentIngestor:
    return DocumentIngestor()


@router.get("/collections", response_model=CollectionsEnvelope)
def list_collections(repo: CollectionsRepository = Depends(get_collections_repo)) -> CollectionsEnvelope:
    collections = repo.list_collections()
    return CollectionsEnvelope(code="OK", data=collections)


@router.get(
    "/collections/{collection_id}/documents",
    response_model=DocumentsEnvelope,
)
def list_collection_documents(
    collection_id: int,
    repo: DocumentsRepository = Depends(get_documents_repo),
    collections_repo: CollectionsRepository = Depends(get_collections_repo),
) -> DocumentsEnvelope:
    collection = collections_repo.get_by_id(collection_id)
    if not collection:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Collection not found.")
    documents = repo.list_by_collection(collection_id)
    items = [
        DocumentListItem(
            id=doc["id"],
            collection_id=doc["collection_id"],
            file_name=doc.get("file_name"),
            file_size_bytes=doc.get("file_size_bytes"),
            element_count=doc.get("element_count"),
            created_at=doc["created_at"],
            parse_status="parsed" if (doc.get("element_count") or 0) > 0 else "uploaded",
        )
        for doc in documents
    ]
    return DocumentsEnvelope(code="OK", data=items)


@router.post(
    "/collections/{collection_id}/documents",
    response_model=DocumentUploadEnvelope,
    status_code=status.HTTP_201_CREATED,
)
def upload_document(
    collection_id: int,
    file: UploadFile = File(...),
    ingestor: DocumentIngestor = Depends(get_document_ingestor),
) -> DocumentUploadEnvelope:
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF uploads are supported.",
        )
    try:
        document = ingestor.ingest_upload(collection_id, file)
    except DuplicateDocumentError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    response = DocumentUploadResponse(
        doc_id=document["id"],
        file_name=document.get("file_name") or file.filename,
        file_size_bytes=int(document.get("file_size_bytes") or 0),
        status="stored",
    )
    return DocumentUploadEnvelope(code="OK", data=response)
