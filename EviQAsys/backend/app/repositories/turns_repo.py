from __future__ import annotations

from typing import Any, Callable, ContextManager

from sqlalchemy import text
from sqlalchemy.engine import Connection

from .base import RepositoryResult, dict_to_insert, dict_to_update, row_to_dict, rows_to_dicts
from .db import db_connection


class TurnsRepository:
    """SQL helpers for the turns table."""

    table_name = "turns"

    def __init__(
        self,
        connection_provider: Callable[[], ContextManager[Connection]] = db_connection,
    ) -> None:
        self._connection_provider = connection_provider

    def create_turn(
        self,
        *,
        chat_id: int,
        order: int,
        user_question: str,
        llm_answer_text: str | None = None,
        llm_thought_text: str | None = None,
        response_tokens: int | None = None,
        used_llm_model: str | None = None,
    ) -> dict[str, Any]:
        payload = {
            "chat_id": chat_id,
            "order": order,
            "user_question": user_question,
            "llm_answer_text": llm_answer_text,
            "llm_thought_text": llm_thought_text,
            "response_tokens": response_tokens,
            "used_llm_model": used_llm_model,
        }
        sql, params = dict_to_insert(self.table_name, payload)
        with self._connection_provider() as connection:
            result = connection.execute(text(sql), params)
            turn_id = result.lastrowid
            fetched = connection.execute(
                text("SELECT * FROM turns WHERE id = :id"),
                {"id": turn_id},
            )
            row = row_to_dict(fetched)
        return row or {}

    def get_by_id(self, turn_id: int) -> dict[str, Any] | None:
        with self._connection_provider() as connection:
            result = connection.execute(
                text("SELECT * FROM turns WHERE id = :id"),
                {"id": turn_id},
            )
            return row_to_dict(result)

    def list_by_chat(self, chat_id: int) -> list[dict[str, Any]]:
        with self._connection_provider() as connection:
            result = connection.execute(
                text(
                    "SELECT * FROM turns WHERE chat_id = :chat_id "
                    "ORDER BY `order` ASC",
                ),
                {"chat_id": chat_id},
            )
            return rows_to_dicts(result)

    def update_turn(self, turn_id: int, **fields: Any) -> RepositoryResult:
        allowed = {
            "order",
            "user_question",
            "llm_answer_text",
            "llm_thought_text",
            "response_tokens",
            "used_llm_model",
        }
        payload = {key: value for key, value in fields.items() if key in allowed}
        if not payload:
            return RepositoryResult(rows=[], rowcount=0)
        sql, params = dict_to_update(self.table_name, payload, "id = :target_id")
        params["target_id"] = turn_id
        with self._connection_provider() as connection:
            result = connection.execute(text(sql), params)
        return RepositoryResult(rows=None, rowcount=result.rowcount)

    def delete_turn(self, turn_id: int) -> RepositoryResult:
        with self._connection_provider() as connection:
            result = connection.execute(
                text("DELETE FROM turns WHERE id = :id"),
                {"id": turn_id},
            )
        return RepositoryResult(rows=None, rowcount=result.rowcount)
