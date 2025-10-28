"""Turn endpoints."""

from typing import List, Optional

from fastapi import APIRouter, HTTPException, Response, status
from sqlalchemy import select

from app.api.deps import DBSession
from app import crud
from app.db import models
from app.schemas import (
    TurnCreate,
    TurnRead,
    TurnUpdate,
    TurnEvidenceCreate,
    TurnEvidenceRead,
)

router = APIRouter(prefix="/turns", tags=["turns"])


@router.get("/", response_model=List[TurnRead])
def list_turns(
    db: DBSession,
    skip: int = 0,
    limit: int = 100,
    chat_id: Optional[int] = None,
) -> List[TurnRead]:
    stmt = select(models.Turn).offset(skip).limit(limit)
    if chat_id is not None:
        stmt = stmt.where(models.Turn.chat_id == chat_id)
    return list(db.execute(stmt).scalars().all())


@router.post("/", response_model=TurnRead, status_code=status.HTTP_201_CREATED)
def create_turn(payload: TurnCreate, db: DBSession) -> TurnRead:
    if crud.chats.get(db, payload.chat_id) is None:
        raise HTTPException(status_code=404, detail="Chat not found")
    return crud.turns.create(db, obj_in=payload)


@router.get("/{turn_id}", response_model=TurnRead)
def get_turn(turn_id: int, db: DBSession) -> TurnRead:
    record = crud.turns.get(db, turn_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Turn not found")
    return record


@router.put("/{turn_id}", response_model=TurnRead)
def update_turn(turn_id: int, payload: TurnUpdate, db: DBSession) -> TurnRead:
    record = crud.turns.get(db, turn_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Turn not found")
    return crud.turns.update(db, db_obj=record, obj_in=payload)


@router.delete("/{turn_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_turn(turn_id: int, db: DBSession) -> Response:
    record = crud.turns.get(db, turn_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Turn not found")
    crud.turns.remove(db, db_obj=record)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{turn_id}/evidence-links", response_model=List[TurnEvidenceRead])
def list_turn_evidences(turn_id: int, db: DBSession) -> List[TurnEvidenceRead]:
    if crud.turns.get(db, turn_id) is None:
        raise HTTPException(status_code=404, detail="Turn not found")
    stmt = select(models.Turn2Evidence).where(models.Turn2Evidence.turn_id == turn_id)
    return list(db.execute(stmt).scalars().all())


@router.post(
    "/{turn_id}/evidence-links",
    response_model=TurnEvidenceRead,
    status_code=status.HTTP_201_CREATED,
)
def create_turn_evidence(
    turn_id: int, payload: TurnEvidenceCreate, db: DBSession
) -> TurnEvidenceRead:
    if payload.turn_id != turn_id:
        raise HTTPException(
            status_code=400,
            detail="turn_id mismatch between path and payload",
        )
    try:
        return crud.create_turn_evidence_link(db, payload)
    except ValueError as exc:
        message = str(exc)
        if "not found" in message.lower():
            raise HTTPException(status_code=404, detail=message) from exc
        raise HTTPException(status_code=400, detail=message) from exc
