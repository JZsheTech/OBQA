"""Database schema bootstrap utilities."""

from sqlalchemy import create_engine, text

from app.core.config import settings

from .base import Base
from .session import engine


def ensure_database() -> None:
    """Create the target OceanBase schema if it does not already exist."""
    server_engine = create_engine(settings.sqlalchemy_server_uri, future=True)
    db_name = settings.ob_database
    with server_engine.begin() as conn:
        conn.execute(text(f"CREATE DATABASE IF NOT EXISTS {db_name}"))


def init_database_schema() -> None:
    """Ensure database and tables exist."""
    ensure_database()
    # Import models so they are registered on the Declarative Base metadata.
    from app.db import models  # noqa: F401

    Base.metadata.create_all(bind=engine)
