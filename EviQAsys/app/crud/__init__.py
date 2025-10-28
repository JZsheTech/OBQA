"""CRUD repositories."""

from app.db import models
from app.schemas import (
    ChatCreate,
    ChatUpdate,
    CollectionCreate,
    CollectionUpdate,
    DocumentCreate,
    DocumentUpdate,
    ElementCreate,
    ElementUpdate,
    TurnCreate,
    TurnUpdate,
)

from .base import CRUDBase
from .evidence import (
    create_evidence_link,
    create_turn_evidence_link,
    list_evidence_links,
)

collections = CRUDBase[models.Collection, CollectionCreate, CollectionUpdate](
    models.Collection
)
documents = CRUDBase[models.Document, DocumentCreate, DocumentUpdate](models.Document)
elements = CRUDBase[models.Element, ElementCreate, ElementUpdate](models.Element)
chats = CRUDBase[models.Chat, ChatCreate, ChatUpdate](models.Chat)
turns = CRUDBase[models.Turn, TurnCreate, TurnUpdate](models.Turn)

__all__ = [
    "collections",
    "documents",
    "elements",
    "chats",
    "turns",
    "create_evidence_link",
    "create_turn_evidence_link",
    "list_evidence_links",
]
