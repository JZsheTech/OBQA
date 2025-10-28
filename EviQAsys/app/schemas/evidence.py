"""Evidence link schemas."""

from .base import ORMModel


class EvidenceLinkBase(ORMModel):
    chat_id: int
    evidence_no: int
    element_id: int


class EvidenceLinkCreate(EvidenceLinkBase):
    pass


class EvidenceLinkRead(EvidenceLinkBase):
    pass


class TurnEvidenceBase(ORMModel):
    turn_id: int
    chat_id: int
    evidence_no: int


class TurnEvidenceCreate(TurnEvidenceBase):
    pass


class TurnEvidenceRead(TurnEvidenceBase):
    pass
