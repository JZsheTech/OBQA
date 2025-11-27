from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    Column,
    String,
    Text,
    BigInteger,
    DateTime,
    ForeignKey,
    UniqueConstraint,
    Index,
)
from sqlalchemy.orm import relationship

from .database import Base


class Paper(Base):
    __tablename__ = "papers"
    __table_args__ = (
        UniqueConstraint("arxiv_id", name="uq_papers_arxiv_id"),
        Index("idx_papers_arxiv_id", "arxiv_id"),
        Index("idx_papers_primary_category", "primary_category"),
    )

    id = Column(BigInteger, primary_key=True, index=True)
    arxiv_id = Column(String(32), nullable=False)
    version = Column(String(16), nullable=True)
    title = Column(Text, nullable=False)
    summary = Column(Text, nullable=True)
    authors = Column(Text, nullable=True)  # JSON array string
    primary_category = Column(String(64), nullable=True)
    categories = Column(Text, nullable=True)  # JSON array string
    published = Column(DateTime, nullable=True)
    updated = Column(DateTime, nullable=True)
    pdf_url = Column(String(512), nullable=True)
    abs_url = Column(String(512), nullable=True)
    doi = Column(String(128), nullable=True)
    journal_ref = Column(String(512), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    saved_records = relationship("SavedPaper", back_populates="paper", cascade="all, delete-orphan")


class SavedPaper(Base):
    __tablename__ = "saved_papers"
    __table_args__ = (
        Index("idx_saved_papers_created_at", "created_at"),
    )

    id = Column(BigInteger, primary_key=True, index=True)
    paper_id = Column(BigInteger, ForeignKey("papers.id", ondelete="CASCADE"), nullable=False)
    tags = Column(String(512), nullable=True)
    note = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    paper = relationship("Paper", back_populates="saved_records")
