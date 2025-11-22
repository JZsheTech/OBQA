from __future__ import annotations

from typing import Any, Literal

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from pydantic import BaseModel

from ...repositories import ChatsRepository, CollectionsRepository, DocumentsRepository
from ...schemas import ChatRead, CollectionCreate, CollectionRead, DocumentListItem, DocumentUploadResponse
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


class CollectionEnvelope(BaseModel):
    code: str = "OK"
    data: CollectionRead


class DocumentUploadEnvelope(BaseModel):
    code: str = "OK"
    data: DocumentUploadResponse


class ChatsEnvelope(BaseModel):
    code: str = "OK"
    data: list[ChatRead]


def get_collections_repo() -> CollectionsRepository:
    return CollectionsRepository()


def get_documents_repo() -> DocumentsRepository:
    return DocumentsRepository()


def get_chats_repo() -> ChatsRepository:
    return ChatsRepository()


def get_document_ingestor() -> DocumentIngestor:
    return DocumentIngestor()


@router.get("/collections", response_model=CollectionsEnvelope)
def list_collections(
    repo: CollectionsRepository = Depends(get_collections_repo),
    search_field: Literal["name", "description"] | None = Query(
        default=None, description="Search field to filter collections.",
    ),
    keyword: str | None = Query(default=None, description="Keyword for fuzzy search."),
) -> CollectionsEnvelope:
    keyword_value = (keyword or "").strip()
    try:
        if keyword_value:
            field = search_field or "name"
            collections = repo.search_collections(field=field, keyword=keyword_value)
        elif search_field:
            collections = repo.list_collections()
        else:
            collections = repo.list_collections()
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    return CollectionsEnvelope(code="OK", data=collections)


@router.post("/collections", response_model=CollectionEnvelope, status_code=status.HTTP_201_CREATED)
def create_collection(
    payload: CollectionCreate,
    repo: CollectionsRepository = Depends(get_collections_repo),
) -> CollectionEnvelope:
    name = (payload.name or "").strip()
    if not name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Collection name is required.",
        )
    description = (payload.description or "").strip() or None
    collection = repo.create_collection(name=name, description=description)
    if not collection:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create collection.",
        )
    return CollectionEnvelope(code="OK", data=CollectionRead(**collection))


@router.get(
    "/collections/{collection_id}",
    response_model=CollectionEnvelope,
)
def get_collection_detail(
    collection_id: int,
    repo: CollectionsRepository = Depends(get_collections_repo),
) -> CollectionEnvelope:
    collection = repo.get_by_id(collection_id)
    if not collection:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Collection not found.")
    return CollectionEnvelope(code="OK", data=CollectionRead(**collection))


@router.get(
    "/collections/{collection_id}/documents",
    response_model=DocumentsEnvelope,
)
def list_collection_documents(
    collection_id: int,
    repo: DocumentsRepository = Depends(get_documents_repo),
    collections_repo: CollectionsRepository = Depends(get_collections_repo),
    search_field: Literal["title", "abstract", "md_text"] | None = Query(
        default=None,
        description="Search field to filter documents (title, abstract, md_text).",
    ),
    keyword: str | None = Query(
        default=None,
        description="Keyword for fuzzy search within documents of a collection.",
    ),
) -> DocumentsEnvelope:
    collection = collections_repo.get_by_id(collection_id)
    if not collection:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Collection not found.")
    keyword_value = (keyword or "").strip()
    try:
        if keyword_value:
            field = search_field or "title"
            documents = repo.search_in_collection(
                collection_id=collection_id,
                field=field,
                keyword=keyword_value,
            )
        else:
            documents = repo.list_by_collection(collection_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    items = [_to_document_list_item(doc) for doc in documents]
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


@router.get(
    "/collections/{collection_id}/chats",
    response_model=ChatsEnvelope,
)
def list_collection_chats(
    collection_id: int,
    repo: ChatsRepository = Depends(get_chats_repo),
    collections_repo: CollectionsRepository = Depends(get_collections_repo),
) -> ChatsEnvelope:
    collection = collections_repo.get_by_id(collection_id)
    if not collection:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Collection not found.")
    chats = repo.list_by_collection(collection_id)
    items = [
        ChatRead(
            id=chat["id"],
            collection_id=chat.get("collection_id"),
            document_id=chat.get("document_id"),
            type=chat.get("type") or "collection",
            title=chat.get("title") or f"Chat #{chat.get('id')}",
            max_turn_order=int(chat.get("max_turn_order") or 0),
            created_at=chat["created_at"],
        )
        for chat in chats
    ]
    return ChatsEnvelope(code="OK", data=items)


def _to_document_list_item(doc: dict[str, Any]) -> DocumentListItem:
    element_count = doc.get("element_count")
    parse_status = "parsed" if (element_count or 0) > 0 else "uploaded"
    return DocumentListItem(
        id=doc["id"],
        collection_id=doc["collection_id"],
        title=doc.get("title"),
        abstract=doc.get("abstract"),
        file_name=doc.get("file_name"),
        file_size_bytes=_safe_int(doc.get("file_size_bytes")),
        element_count=element_count,
        num_pages=doc.get("num_pages"),
        created_at=doc["created_at"],
        parse_status=parse_status,
    )


def _safe_int(value: Any) -> int | None:
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None
