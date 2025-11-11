from __future__ import annotations

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


__all__ = ["db_connection", "get_engine", "initialize_database"]
