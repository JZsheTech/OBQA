"""Chat endpoints."""

from typing import List, Optional

from fastapi import APIRouter, HTTPException, Response, status
from sqlalchemy import select

from app.api.deps import DBSession
from app import crud
from app.db import models
from app.schemas import (
    ChatCreate,
    ChatRead,
    ChatUpdate,
    EvidenceLinkCreate,
    EvidenceLinkRead,
)

router = APIRouter(prefix="/chats", tags=["chats"])


@router.get("/", response_model=List[ChatRead])
def list_chats(
    db: DBSession,
    skip: int = 0,
    limit: int = 100,
    collection_id: Optional[int] = None,
) -> List[ChatRead]:
    stmt = select(models.Chat).offset(skip).limit(limit)
    if collection_id is not None:
        stmt = stmt.where(models.Chat.collection_id == collection_id)
    return list(db.execute(stmt).scalars().all())


@router.post("/", response_model=ChatRead, status_code=status.HTTP_201_CREATED)
def create_chat(payload: ChatCreate, db: DBSession) -> ChatRead:
    if crud.collections.get(db, payload.collection_id) is None:
        raise HTTPException(status_code=404, detail="Collection not found")
    return crud.chats.create(db, obj_in=payload)


@router.get("/{chat_id}", response_model=ChatRead)
def get_chat(chat_id: int, db: DBSession) -> ChatRead:
    record = crud.chats.get(db, chat_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Chat not found")
    return record


@router.put("/{chat_id}", response_model=ChatRead)
def update_chat(chat_id: int, payload: ChatUpdate, db: DBSession) -> ChatRead:
    record = crud.chats.get(db, chat_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Chat not found")
    return crud.chats.update(db, db_obj=record, obj_in=payload)


@router.delete("/{chat_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_chat(chat_id: int, db: DBSession) -> Response:
    record = crud.chats.get(db, chat_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Chat not found")
    crud.chats.remove(db, db_obj=record)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{chat_id}/evidence-links", response_model=List[EvidenceLinkRead])
def get_chat_evidence_links(chat_id: int, db: DBSession) -> List[EvidenceLinkRead]:
    if crud.chats.get(db, chat_id) is None:
        raise HTTPException(status_code=404, detail="Chat not found")
    return crud.list_evidence_links(db, chat_id)


@router.post(
    "/{chat_id}/evidence-links",
    response_model=EvidenceLinkRead,
    status_code=status.HTTP_201_CREATED,
)
def create_chat_evidence_link(
    chat_id: int, payload: EvidenceLinkCreate, db: DBSession
) -> EvidenceLinkRead:
    if payload.chat_id != chat_id:
        raise HTTPException(
            status_code=400,
            detail="chat_id mismatch between path and payload",
        )
    try:
        return crud.create_evidence_link(db, payload)
    except ValueError as exc:
        message = str(exc)
        if "not found" in message.lower():
            raise HTTPException(status_code=404, detail=message) from exc
        raise HTTPException(status_code=400, detail=message) from exc
