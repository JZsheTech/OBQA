from __future__ import annotations

from typing import Iterable, Mapping, Callable, ContextManager

from sqlalchemy import text
from sqlalchemy.engine import Connection

from .base import RepositoryResult, dict_to_insert, rows_to_dicts
from .db import db_connection


class Turn2ElementRepository:
    """Bridge table helper between turns and elements (no evidence_no persisted)."""

    table_name = "turn2element"

    def __init__(
        self,
        connection_provider: Callable[[], ContextManager[Connection]] = db_connection,
    ) -> None:
        self._connection_provider = connection_provider

    def bulk_bind(self, records: Iterable[Mapping[str, int]]) -> RepositoryResult:
        """Insert multiple element bindings within a single transaction.

        Each record must include: chat_id, turn_id, turn_order, element_id.
        """
        inserted = 0
        with self._connection_provider() as connection:
            for record in records:
                payload = {
                    "chat_id": record["chat_id"],
                    "turn_id": record["turn_id"],
                    "turn_order": record["turn_order"],
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
                    "SELECT chat_id, turn_id, turn_order, element_id, created_at "
                    "FROM turn2element WHERE turn_id = :turn_id "
                    "ORDER BY turn_order ASC, element_id ASC",
                ),
                {"turn_id": turn_id},
            )
            return rows_to_dicts(result)

    def list_by_chat(self, chat_id: int) -> list[dict[str, object]]:
        with self._connection_provider() as connection:
            result = connection.execute(
                text(
                    "SELECT chat_id, turn_id, turn_order, element_id, created_at "
                    "FROM turn2element WHERE chat_id = :chat_id "
                    "ORDER BY turn_order ASC, created_at ASC",
                ),
                {"chat_id": chat_id},
            )
            return rows_to_dicts(result)

    def delete_by_turn(self, turn_id: int) -> RepositoryResult:
        with self._connection_provider() as connection:
            result = connection.execute(
                text("DELETE FROM turn2element WHERE turn_id = :turn_id"),
                {"turn_id": turn_id},
            )
        return RepositoryResult(rows=None, rowcount=result.rowcount)

