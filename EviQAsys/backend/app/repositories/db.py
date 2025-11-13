from __future__ import annotations

import logging
import re
from contextlib import contextmanager
from pathlib import Path
from threading import Lock
from typing import Iterator, Sequence

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Connection, Engine, URL
from sqlalchemy.exc import SQLAlchemyError

from ..env_setting import DB_CHARSET, VECTOR_DIM, get_oceanbase_settings

_SCHEMA_FILE = Path(__file__).with_name("sql").joinpath("schema.sql")
_ENGINE: Engine | None = None
_ENGINE_LOCK = Lock()
logger = logging.getLogger(__name__)


def _quote_identifier(identifier: str) -> str:
    if "`" in identifier:
        raise ValueError("Backticks are not allowed in identifiers.")
    return f"`{identifier}`"


def _build_engine() -> Engine:
    settings = get_oceanbase_settings()
    url = URL.create(
        drivername="mysql+pymysql",
        username=settings.user,
        password=settings.password,
        host=settings.host,
        port=settings.port,
        database=None,
        query={"charset": DB_CHARSET},
    )
    return create_engine(
        url,
        future=True,
        pool_pre_ping=True,
        pool_recycle=3600,
        connect_args={"connect_timeout": settings.connect_timeout},
    )


def get_engine() -> Engine:
    global _ENGINE
    if _ENGINE is None:
        with _ENGINE_LOCK:
            if _ENGINE is None:
                _ENGINE = _build_engine()
    return _ENGINE


def _load_schema_statements() -> Sequence[str]:
    if not _SCHEMA_FILE.exists():
        raise FileNotFoundError(f"Schema file not found: {_SCHEMA_FILE}")
    raw_sql = _SCHEMA_FILE.read_text(encoding="utf-8")
    rendered_sql = raw_sql.replace("{{VECTOR_DIM}}", str(VECTOR_DIM))
    statements: list[str] = []
    buffer: list[str] = []
    for line in rendered_sql.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("--"):
            continue
        buffer.append(line)
        if stripped.endswith(";"):
            statement = "\n".join(buffer).rstrip(";\n\t ")
            statements.append(statement)
            buffer = []
    if buffer:
        statements.append("\n".join(buffer).rstrip(";\n\t "))
    return statements


def initialize_database() -> None:
    """Create the target database (if needed) and apply DDL statements."""
    engine = get_engine()
    settings = get_oceanbase_settings()
    statements = _load_schema_statements()
    quoted_db = _quote_identifier(settings.default_database)
    try:
        with engine.begin() as connection:
            connection.execute(
                text(
                    f"CREATE DATABASE IF NOT EXISTS {quoted_db} "
                    f"DEFAULT CHARACTER SET {DB_CHARSET}",
                ),
            )
            connection.execute(text(f"USE {quoted_db}"))
            for statement in statements:
                connection.execute(text(statement))
            _ensure_vector_dimension(connection, settings.default_database)
    except SQLAlchemyError as exc:  # pragma: no cover - startup failure path
        raise RuntimeError("Failed to initialize database schema.") from exc


@contextmanager
def db_connection() -> Iterator[Connection]:
    """Yield a connection that already selected the working database."""
    engine = get_engine()
    settings = get_oceanbase_settings()
    quoted_db = _quote_identifier(settings.default_database)
    with engine.begin() as connection:
        connection.execute(text(f"USE {quoted_db}"))
        yield connection


def _ensure_vector_dimension(connection: Connection, schema_name: str) -> None:
    """Ensure elements.vec_embedding dimension matches VECTOR_DIM."""
    result = connection.execute(
        text(
            "SELECT COLUMN_TYPE FROM information_schema.COLUMNS "
            "WHERE TABLE_SCHEMA = :schema AND TABLE_NAME = 'elements' AND COLUMN_NAME = 'vec_embedding'",
        ),
        {"schema": schema_name},
    ).first()
    if not result:
        return
    column_type = result[0] or ""
    current_dim = _extract_vector_dimension(str(column_type))
    if current_dim is None:
        logger.warning("Unable to detect vec_embedding dimension from COLUMN_TYPE=%s", column_type)
        return
    if current_dim == VECTOR_DIM:
        return
    logger.info(
        "Altering elements.vec_embedding from VECTOR(%s) to VECTOR(%s) to match configuration.",
        current_dim,
        VECTOR_DIM,
    )
    connection.execute(
        text(f"ALTER TABLE elements MODIFY COLUMN vec_embedding VECTOR({VECTOR_DIM}) NULL"),
    )


def _extract_vector_dimension(column_type: str) -> int | None:
    match = re.search(r"vector\((\d+)\)", column_type, flags=re.IGNORECASE)
    if not match:
        return None
    try:
        return int(match.group(1))
    except ValueError:
        return None


__all__ = ["db_connection", "get_engine", "initialize_database"]
