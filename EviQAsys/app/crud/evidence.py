"""Domain-specific CRUD helpers for evidence link tables."""

from typing import List

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import models
from app.schemas import EvidenceLinkCreate, TurnEvidenceCreate


def create_evidence_link(
    db: Session, payload: EvidenceLinkCreate
) -> models.Evidence2Element:
    """Insert a chat-level evidence link, enforcing existence checks."""
    if db.get(models.Chat, payload.chat_id) is None:
        raise ValueError(f"Chat {payload.chat_id} not found")
    if db.get(models.Element, payload.element_id) is None:
        raise ValueError(f"Element {payload.element_id} not found")

    pk = (payload.chat_id, payload.evidence_no)
    if db.get(models.Evidence2Element, pk) is not None:
        raise ValueError(
            f"Evidence #{payload.evidence_no} already exists for chat {payload.chat_id}"
        )

    record = models.Evidence2Element(
        chat_id=payload.chat_id,
        evidence_no=payload.evidence_no,
        element_id=payload.element_id,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def list_evidence_links(db: Session, chat_id: int) -> List[models.Evidence2Element]:
    """List evidence links for a chat."""
    stmt = select(models.Evidence2Element).where(models.Evidence2Element.chat_id == chat_id)
    return list(db.execute(stmt).scalars().all())


def create_turn_evidence_link(
    db: Session, payload: TurnEvidenceCreate
) -> models.Turn2Evidence:
    """Tie a turn to an evidence entry."""
    if db.get(models.Turn, payload.turn_id) is None:
        raise ValueError(f"Turn {payload.turn_id} not found")

    pk = (payload.turn_id, payload.evidence_no)
    if db.get(models.Turn2Evidence, pk) is not None:
        raise ValueError(
            f"Evidence #{payload.evidence_no} already linked to turn {payload.turn_id}"
        )

    # Ensure referenced evidence link exists
    if db.get(models.Evidence2Element, (payload.chat_id, payload.evidence_no)) is None:
        raise ValueError(
            f"Evidence #{payload.evidence_no} not found for chat {payload.chat_id}"
        )

    record = models.Turn2Evidence(
        turn_id=payload.turn_id,
        chat_id=payload.chat_id,
        evidence_no=payload.evidence_no,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record
