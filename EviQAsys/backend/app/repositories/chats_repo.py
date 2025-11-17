from __future__ import annotations

from typing import Any, Callable, ContextManager

from sqlalchemy import text
from sqlalchemy.engine import Connection

from .base import RepositoryResult, dict_to_insert, dict_to_update, row_to_dict, rows_to_dicts
from .db import db_connection


class ChatsRepository:
    """SQL helpers for chat metadata."""

    table_name = "chats"

    def __init__(
        self,
        connection_provider: Callable[[], ContextManager[Connection]] = db_connection,
    ) -> None:
        self._connection_provider = connection_provider

    def create_chat(
        self,
        *,
        collection_id: int,
        title: str | None = None,
        max_turn_order: int = 0,
    ) -> dict[str, Any]:
        payload = {
            "collection_id": collection_id,
            "title": title,
            "max_turn_order": max_turn_order,
        }
        sql, params = dict_to_insert(self.table_name, payload)
        with self._connection_provider() as connection:
            result = connection.execute(text(sql), params)
            chat_id = result.lastrowid
            fetched = connection.execute(
                text("SELECT * FROM chats WHERE id = :id"),
                {"id": chat_id},
            )
            row = row_to_dict(fetched)
        return row or {}

    def get_by_id(self, chat_id: int) -> dict[str, Any] | None:
        with self._connection_provider() as connection:
            result = connection.execute(
                text("SELECT * FROM chats WHERE id = :id"),
                {"id": chat_id},
            )
            return row_to_dict(result)

    def list_by_collection(self, collection_id: int) -> list[dict[str, Any]]:
        with self._connection_provider() as connection:
            result = connection.execute(
                text(
                    "SELECT * FROM chats WHERE collection_id = :collection_id "
                    "ORDER BY created_at DESC, id DESC",
                ),
                {"collection_id": collection_id},
            )
            return rows_to_dicts(result)

    def update_chat(self, chat_id: int, **fields: Any) -> RepositoryResult:
        allowed = {"title", "max_turn_order"}
        payload = {key: value for key, value in fields.items() if key in allowed}
        if not payload:
            return RepositoryResult(rows=[], rowcount=0)
        sql, params = dict_to_update(self.table_name, payload, "id = :target_id")
        params["target_id"] = chat_id
        with self._connection_provider() as connection:
            result = connection.execute(text(sql), params)
        return RepositoryResult(rows=None, rowcount=result.rowcount)

    def delete_chat(self, chat_id: int) -> RepositoryResult:
        with self._connection_provider() as connection:
            result = connection.execute(
                text("DELETE FROM chats WHERE id = :id"),
                {"id": chat_id},
            )
        return RepositoryResult(rows=None, rowcount=result.rowcount)
