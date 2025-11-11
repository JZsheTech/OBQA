from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Iterable

from sqlalchemy.engine import Result

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class RepositoryResult:
    """Standard wrapper for repository calls."""

    rows: list[dict[str, Any]] | None = None
    rowcount: int | None = None

    def first(self) -> dict[str, Any] | None:
        return self.rows[0] if self.rows else None


def dict_to_insert(table: str, payload: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    columns = ", ".join(f"`{column}`" for column in payload.keys())
    placeholders = ", ".join(f":{column}" for column in payload.keys())
    sql = f"INSERT INTO {table} ({columns}) VALUES ({placeholders})"
    return sql, payload


def dict_to_update(
    table: str,
    payload: dict[str, Any],
    where_clause: str,
) -> tuple[str, dict[str, Any]]:
    assignments = ", ".join(f"`{column}` = :{column}" for column in payload.keys())
    sql = f"UPDATE {table} SET {assignments} WHERE {where_clause}"
    return sql, payload


def rows_to_dicts(result: Result) -> list[dict[str, Any]]:
    return [dict(row._mapping) for row in result]


def row_to_dict(result: Result) -> dict[str, Any] | None:
    row = result.first()
    return dict(row._mapping) if row else None


def log_db_error(message: str, *, exc: Exception | None = None) -> None:
    if exc:
        logger.exception(message, exc_info=exc)
    else:
        logger.error(message)
