"""ORM model definitions."""

from typing import List, Optional

from sqlalchemy import (
    ForeignKey,
    ForeignKeyConstraint,
    Integer,
    PrimaryKeyConstraint,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.config import settings

from .base import Base, TimestampMixin
from .types import OBVector


class Collection(TimestampMixin, Base):
    __tablename__ = "collections"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)

    documents: Mapped[List["Document"]] = relationship(
        back_populates="collection",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    chats: Mapped[List["Chat"]] = relationship(
        back_populates="collection",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class Document(TimestampMixin, Base):
    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    collection_id: Mapped[int] = mapped_column(
        ForeignKey("collections.id", ondelete="CASCADE"),
        nullable=False,
    )
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    num_pages: Mapped[Optional[int]] = mapped_column(Integer)

    collection: Mapped["Collection"] = relationship(back_populates="documents")
    elements: Mapped[List["Element"]] = relationship(
        back_populates="document",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class Element(TimestampMixin, Base):
    __tablename__ = "elements"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    document_id: Mapped[int] = mapped_column(
        "doc_id",
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
    )
    elem_type: Mapped[str] = mapped_column(String(50), nullable=False)
    section_name: Mapped[Optional[str]] = mapped_column(String(255))
    level_nav: Mapped[Optional[str]] = mapped_column(String(255))
    text_content: Mapped[Optional[str]] = mapped_column(Text)
    text_caption: Mapped[Optional[str]] = mapped_column(Text)
    image_base64: Mapped[Optional[str]] = mapped_column(Text)
    bbox_json: Mapped[Optional[str]] = mapped_column(Text)
    page_no: Mapped[Optional[int]] = mapped_column(Integer)
    vec_embedding: Mapped[Optional[List[float]]] = mapped_column(
        OBVector(settings.vector_dimension)
    )

    document: Mapped["Document"] = relationship(back_populates="elements")
    evidence_links: Mapped[List["Evidence2Element"]] = relationship(
        back_populates="element",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class Chat(TimestampMixin, Base):
    __tablename__ = "chats"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    collection_id: Mapped[int] = mapped_column(
        ForeignKey("collections.id", ondelete="CASCADE"),
        nullable=False,
    )

    collection: Mapped["Collection"] = relationship(back_populates="chats")
    turns: Mapped[List["Turn"]] = relationship(
        back_populates="chat",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    evidence_links: Mapped[List["Evidence2Element"]] = relationship(
        back_populates="chat",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class Turn(TimestampMixin, Base):
    __tablename__ = "turns"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    chat_id: Mapped[int] = mapped_column(
        ForeignKey("chats.id", ondelete="CASCADE"), nullable=False
    )
    user_question: Mapped[str] = mapped_column(Text, nullable=False)
    llm_answer_text: Mapped[Optional[str]] = mapped_column(Text)
    llm_thought_text: Mapped[Optional[str]] = mapped_column(Text)

    chat: Mapped["Chat"] = relationship(back_populates="turns")
    evidence_refs: Mapped[List["Turn2Evidence"]] = relationship(
        back_populates="turn",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class Evidence2Element(Base):
    __tablename__ = "evidence2element"

    chat_id: Mapped[int] = mapped_column(
        ForeignKey("chats.id", ondelete="CASCADE"), nullable=False
    )
    evidence_no: Mapped[int] = mapped_column(Integer, nullable=False)
    element_id: Mapped[int] = mapped_column(
        ForeignKey("elements.id", ondelete="CASCADE"), nullable=False
    )

    __table_args__ = (
        PrimaryKeyConstraint("chat_id", "evidence_no", name="pk_evidence2element"),
    )

    chat: Mapped["Chat"] = relationship(back_populates="evidence_links")
    element: Mapped["Element"] = relationship(back_populates="evidence_links")
    turn_links: Mapped[List["Turn2Evidence"]] = relationship(
        back_populates="evidence_link",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class Turn2Evidence(Base):
    __tablename__ = "turn2evidence"

    turn_id: Mapped[int] = mapped_column(
        ForeignKey("turns.id", ondelete="CASCADE"), nullable=False
    )
    chat_id: Mapped[int] = mapped_column(
        ForeignKey("chats.id", ondelete="CASCADE"), nullable=False
    )
    evidence_no: Mapped[int] = mapped_column(Integer, nullable=False)

    __table_args__ = (
        PrimaryKeyConstraint("turn_id", "evidence_no", name="pk_turn2evidence"),
        ForeignKeyConstraint(
            ["chat_id", "evidence_no"],
            ["evidence2element.chat_id", "evidence2element.evidence_no"],
            ondelete="CASCADE",
            name="fk_turn_to_evidence_link",
        ),
    )

    turn: Mapped["Turn"] = relationship(back_populates="evidence_refs")
    evidence_link: Mapped["Evidence2Element"] = relationship(
        back_populates="turn_links"
    )
