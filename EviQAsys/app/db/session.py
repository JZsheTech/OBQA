"""SQLAlchemy session and engine helpers."""

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings

engine = create_engine(
    settings.sqlalchemy_database_uri,
    echo=settings.sql_echo,
    future=True,
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(
    bind=engine,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
    class_=Session,
)


def get_db_session() -> Generator[Session, None, None]:
    """FastAPI dependency that yields a scoped session."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
