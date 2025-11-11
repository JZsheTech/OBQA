from __future__ import annotations

from typing import Iterable, Mapping, Callable, ContextManager

from sqlalchemy import text
from sqlalchemy.engine import Connection

from .base import RepositoryResult, dict_to_insert, rows_to_dicts
from .db import db_connection


class Turn2EvidenceRepository:
    """Bridge table helper between turns and evidence elements."""

    table_name = "turn2evidence"

    def __init__(
        self,
        connection_provider: Callable[[], ContextManager[Connection]] = db_connection,
    ) -> None:
        self._connection_provider = connection_provider

    def bulk_bind(
        self,
        records: Iterable[Mapping[str, int]],
    ) -> RepositoryResult:
        """Insert multiple evidence bindings within a single transaction."""
        inserted = 0
        with self._connection_provider() as connection:
            for record in records:
                payload = {
                    "chat_id": record["chat_id"],
                    "turn_id": record["turn_id"],
                    "turn_order": record["turn_order"],
                    "evidence_no": record["evidence_no"],
                    "element_id": record["element_id"],
                }
                sql, params = dict_to_insert(self.table_name, payload)
                connection.execute(text(sql), params)
                inserted += 1
        return RepositoryResult(rows=None, rowcount=inserted)

    def list_by_turn(self, turn_id: int) -> list[dict[str, object]]:
        with self._connection_provider() as connection:
            result = connection.execute(
                text(
                    "SELECT chat_id, turn_id, turn_order, evidence_no, element_id, created_at "
                    "FROM turn2evidence WHERE turn_id = :turn_id "
                    "ORDER BY evidence_no ASC",
                ),
                {"turn_id": turn_id},
            )
            return rows_to_dicts(result)

    def delete_by_turn(self, turn_id: int) -> RepositoryResult:
        with self._connection_provider() as connection:
            result = connection.execute(
                text("DELETE FROM turn2evidence WHERE turn_id = :turn_id"),
                {"turn_id": turn_id},
            )
        return RepositoryResult(rows=None, rowcount=result.rowcount)
