"""Declarative base definition."""

from datetime import datetime

from sqlalchemy import DateTime, func
from sqlalchemy.orm import DeclarativeBase, Mapped, declared_attr, mapped_column


class Base(DeclarativeBase):
    """Base class with automatic table naming."""

    @declared_attr.directive
    def __tablename__(cls) -> str:  # type: ignore[misc]
        return cls.__name__.lower()


class TimestampMixin:
    """Mixin adding created_at timestamp."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
