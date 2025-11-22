from __future__ import annotations

import logging
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from pydantic import BaseModel

from ...env_setting import UploadSettings, get_upload_settings
from ...repositories import ChatsRepository, CollectionsRepository, DocumentsRepository
from ...schemas import ChatRead, DocumentDetail

router = APIRouter(tags=["documents"])
logger = logging.getLogger(__name__)


class DocumentEnvelope(BaseModel):
    code: str = "OK"
    data: DocumentDetail


class ChatsEnvelope(BaseModel):
    code: str = "OK"
    data: list[ChatRead]


def get_documents_repo() -> DocumentsRepository:
    return DocumentsRepository()


def get_collections_repo() -> CollectionsRepository:
    return CollectionsRepository()


def get_chats_repo() -> ChatsRepository:
    return ChatsRepository()


def get_upload_config() -> UploadSettings:
    return get_upload_settings()


@router.get(
    "/documents/{document_id}",
    response_model=DocumentEnvelope,
)
def get_document_detail(
    document_id: int,
    repo: DocumentsRepository = Depends(get_documents_repo),
    collections_repo: CollectionsRepository = Depends(get_collections_repo),
) -> DocumentEnvelope:
    document = repo.get_by_id(document_id)
    if not document:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.")
    collection = collections_repo.get_by_id(document["collection_id"])
    if not collection:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Collection not found.")
    detail = _format_document_detail(document, collection)
    return DocumentEnvelope(code="OK", data=detail)


@router.get(
    "/documents/{document_id}/chats",
    response_model=ChatsEnvelope,
)
def list_document_chats(
    document_id: int,
    repo: ChatsRepository = Depends(get_chats_repo),
    documents_repo: DocumentsRepository = Depends(get_documents_repo),
) -> ChatsEnvelope:
    document = documents_repo.get_by_id(document_id)
    if not document:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.")
    chats = repo.list_by_document(document_id)
    items = [
        ChatRead(
            id=chat["id"],
            collection_id=chat.get("collection_id"),
            document_id=chat.get("document_id"),
            type=chat.get("type") or "document",
            title=chat.get("title") or f"Chat #{chat.get('id')}",
            max_turn_order=int(chat.get("max_turn_order") or 0),
            created_at=chat["created_at"],
        )
        for chat in chats
    ]
    return ChatsEnvelope(code="OK", data=items)


@router.get(
    "/documents/{document_id}/file",
    response_class=FileResponse,
)
def download_document_file(
    document_id: int,
    repo: DocumentsRepository = Depends(get_documents_repo),
    upload_settings: UploadSettings = Depends(get_upload_config),
) -> FileResponse:
    document = repo.get_by_id(document_id)
    if not document:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.")
    file_path = document.get("file_path")
    if not file_path:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document file is missing.")
    resolved_path = Path(file_path).resolve()
    upload_root = Path(upload_settings.root_dir).resolve()
    try:
        resolved_path.relative_to(upload_root)
    except ValueError:
        logger.warning("Blocked file download outside upload dir: %s", resolved_path)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document file is missing.")
    if not resolved_path.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document file is missing.")
    filename = document.get("file_name") or resolved_path.name
    return FileResponse(
        path=resolved_path,
        media_type="application/pdf",
        filename=filename,
    )


def _format_document_detail(
    document: dict[str, object],
    collection: dict[str, object],
) -> DocumentDetail:
    element_count = _safe_int(document.get("element_count"))
    parse_status = "parsed" if (element_count or 0) > 0 else "uploaded"
    meta_info = document.get("meta_info") if isinstance(document.get("meta_info"), dict) else None
    return DocumentDetail(
        id=int(document["id"]),
        collection_id=int(document["collection_id"]),
        collection_name=collection.get("name"),
        title=document.get("title"),
        abstract=document.get("abstract"),
        file_name=document.get("file_name"),
        file_size_bytes=_safe_int(document.get("file_size_bytes")),
        num_pages=document.get("num_pages"),
        element_count=element_count,
        md_text=document.get("md_text"),
        meta_info=meta_info,
        created_at=document["created_at"],
        parse_status=parse_status,
    )


def _safe_int(value: object) -> int | None:
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None


__all__ = ["router"]
