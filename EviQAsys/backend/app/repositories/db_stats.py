from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Sequence

from sqlalchemy import text
from sqlalchemy.engine import Connection

from .db import db_connection
from .maintenance import DEFAULT_PURGE_ORDER

logger = logging.getLogger(__name__)
handler = logging.StreamHandler()
formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
handler.setFormatter(formatter)

logger.addHandler(handler)
logger.setLevel(logging.INFO)


@dataclass(slots=True)
class TableStats:
    table: str
    row_count: int
    max_id: int | None
    oldest_created_at: datetime | None
    newest_created_at: datetime | None


def _list_all_tables(connection: Connection) -> list[str]:
    rows = connection.execute(
        text(
            """
            SELECT TABLE_NAME
            FROM information_schema.TABLES
            WHERE TABLE_SCHEMA = DATABASE()
            ORDER BY TABLE_NAME
            """
        ),
    )
    return [row[0] for row in rows]


def _resolve_target_tables(connection: Connection, tables: Sequence[str] | None) -> list[str]:
    if tables:
        return list(tables)
    default_order = list(DEFAULT_PURGE_ORDER)
    existing_tables = _list_all_tables(connection)
    merged = default_order + [name for name in existing_tables if name not in default_order]
    # Remove duplicates while preserving order.
    deduped: list[str] = []
    seen: set[str] = set()
    for table in merged:
        if table not in seen:
            deduped.append(table)
            seen.add(table)
    return deduped


def _fetch_column_names(connection: Connection, table: str) -> set[str]:
    rows = connection.execute(
        text(
            """
            SELECT COLUMN_NAME
            FROM information_schema.COLUMNS
            WHERE TABLE_SCHEMA = DATABASE()
              AND TABLE_NAME = :table_name
            """
        ),
        {"table_name": table},
    )
    return {row[0] for row in rows}


def _collect_table_stats(connection: Connection, table: str) -> TableStats:
    column_names = _fetch_column_names(connection, table)
    has_id = "id" in column_names
    has_created_at = "created_at" in column_names
    select_parts = ["COUNT(*) AS row_count"]
    select_parts.append("MAX(id) AS max_id" if has_id else "NULL AS max_id")
    if has_created_at:
        select_parts.extend(
            [
                "MIN(created_at) AS oldest_created_at",
                "MAX(created_at) AS newest_created_at",
            ]
        )
    else:
        select_parts.extend(
            ["NULL AS oldest_created_at", "NULL AS newest_created_at"],
        )
    row = connection.execute(
        text(f"SELECT {', '.join(select_parts)} FROM `{table}`"),
    ).mappings().one()
    row_count = int(row["row_count"] or 0)
    max_id_value = row["max_id"]
    max_id = int(max_id_value) if max_id_value is not None else None
    return TableStats(
        table=table,
        row_count=row_count,
        max_id=max_id,
        oldest_created_at=row["oldest_created_at"],
        newest_created_at=row["newest_created_at"],
    )


def collect_table_stats(tables: Sequence[str] | None = None) -> list[TableStats]:
    with db_connection() as connection:
        target_tables = _resolve_target_tables(connection, tables)
        return [_collect_table_stats(connection, table) for table in target_tables]


def print_table_stats(tables: Sequence[str] | None = None) -> None:
    stats = collect_table_stats(tables)
    header = f"{'table':20} {'rows':>8} {'max_id':>12} {'oldest_created_at':20} {'newest_created_at':20}"
    logger.info(header)
    for stat in stats:
        logger.info(
            "%-20s %8d %12s %20s %20s",
            stat.table,
            stat.row_count,
            stat.max_id if stat.max_id is not None else "-",
            stat.oldest_created_at.isoformat(sep=" ", timespec="seconds")
            if stat.oldest_created_at
            else "-",
            stat.newest_created_at.isoformat(sep=" ", timespec="seconds")
            if stat.newest_created_at
            else "-",
        )


__all__ = ["TableStats", "collect_table_stats", "print_table_stats"]
