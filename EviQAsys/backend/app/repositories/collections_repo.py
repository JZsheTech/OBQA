from __future__ import annotations

from typing import Any, Callable, ContextManager

from sqlalchemy import text
from sqlalchemy.engine import Connection

from .base import RepositoryResult, dict_to_insert, dict_to_update, row_to_dict, rows_to_dicts
from .db import db_connection


class CollectionsRepository:
    """CRUD helpers for the collections table."""

    table_name = "collections"

    def __init__(
        self,
        connection_provider: Callable[[], ContextManager[Connection]] = db_connection,
    ) -> None:
        self._connection_provider = connection_provider

    def create_collection(self, *, name: str, description: str | None = None) -> dict[str, Any]:
        payload = {"name": name, "description": description}
        sql, params = dict_to_insert(self.table_name, payload)
        with self._connection_provider() as connection:
            result = connection.execute(text(sql), params)
            new_id = result.lastrowid
            fetched = connection.execute(
                text(
                    "SELECT id, name, description, created_at "
                    "FROM collections WHERE id = :id",
                ),
                {"id": new_id},
            )
            row = row_to_dict(fetched)
        return row or {}

    def get_by_id(self, collection_id: int) -> dict[str, Any] | None:
        with self._connection_provider() as connection:
            result = connection.execute(
                text(
                    "SELECT id, name, description, created_at "
                    "FROM collections WHERE id = :id",
                ),
                {"id": collection_id},
            )
            return row_to_dict(result)

    def list_collections(self) -> list[dict[str, Any]]:
        with self._connection_provider() as connection:
            result = connection.execute(
                text(
                    "SELECT id, name, description, created_at "
                    "FROM collections ORDER BY created_at DESC, id DESC",
                ),
            )
            return rows_to_dicts(result)

    def search_collections(self, *, field: str, keyword: str) -> list[dict[str, Any]]:
        """Search collections by the given field using a case-insensitive LIKE."""
        normalized_field = field.lower()
        if normalized_field not in {"name", "description"}:
            raise ValueError("Unsupported search field.")
        trimmed_keyword = (keyword or "").strip()
        if not trimmed_keyword:
            return self.list_collections()
        like_pattern = f"%{trimmed_keyword.lower()}%"
        with self._connection_provider() as connection:
            result = connection.execute(
                text(
                    "SELECT id, name, description, created_at "
                    f"FROM collections WHERE LOWER({normalized_field}) LIKE :pattern "
                    "ORDER BY created_at DESC, id DESC",
                ),
                {"pattern": like_pattern},
            )
            return rows_to_dicts(result)

    def update_collection(self, collection_id: int, *, name: str | None = None, description: str | None = None) -> RepositoryResult:
        payload: dict[str, Any] = {}
        if name is not None:
            payload["name"] = name
        if description is not None:
            payload["description"] = description
        if not payload:
            return RepositoryResult(rows=[], rowcount=0)
        sql, params = dict_to_update(self.table_name, payload, "id = :target_id")
        params["target_id"] = collection_id
        with self._connection_provider() as connection:
            result = connection.execute(text(sql), params)
        return RepositoryResult(rows=None, rowcount=result.rowcount)

    def delete_collection(self, collection_id: int) -> RepositoryResult:
        with self._connection_provider() as connection:
            result = connection.execute(
                text("DELETE FROM collections WHERE id = :id"),
                {"id": collection_id},
            )
        return RepositoryResult(rows=None, rowcount=result.rowcount)
