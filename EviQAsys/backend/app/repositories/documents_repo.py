from __future__ import annotations

from typing import Any, Callable, ContextManager

from sqlalchemy import text
from sqlalchemy.engine import Connection

from .base import RepositoryResult, dict_to_insert, dict_to_update, row_to_dict, rows_to_dicts
from .db import db_connection


class DocumentsRepository:
    """Non-ORM gateway for the documents table."""

    table_name = "documents"

    def __init__(
        self,
        connection_provider: Callable[[], ContextManager[Connection]] = db_connection,
    ) -> None:
        self._connection_provider = connection_provider

    def create_document(
        self,
        *,
        collection_id: int,
        title: str | None = None,
        file_name: str | None = None,
        file_path: str | None = None,
        num_pages: int | None = None,
    ) -> dict[str, Any]:
        payload = {
            "collection_id": collection_id,
            "title": title,
            "file_name": file_name,
            "file_path": file_path,
            "num_pages": num_pages,
        }
        sql, params = dict_to_insert(self.table_name, payload)
        with self._connection_provider() as connection:
            result = connection.execute(text(sql), params)
            doc_id = result.lastrowid
            fetched = connection.execute(
                text(
                    "SELECT id, collection_id, title, file_name, file_path, num_pages, created_at "
                    "FROM documents WHERE id = :id",
                ),
                {"id": doc_id},
            )
            row = row_to_dict(fetched)
        return row or {}

    def get_by_id(self, document_id: int) -> dict[str, Any] | None:
        with self._connection_provider() as connection:
            result = connection.execute(
                text(
                    "SELECT id, collection_id, title, file_name, file_path, num_pages, created_at "
                    "FROM documents WHERE id = :id",
                ),
                {"id": document_id},
            )
            return row_to_dict(result)

    def list_by_collection(self, collection_id: int) -> list[dict[str, Any]]:
        with self._connection_provider() as connection:
            result = connection.execute(
                text(
                    "SELECT id, collection_id, title, file_name, file_path, num_pages, created_at "
                    "FROM documents WHERE collection_id = :collection_id "
                    "ORDER BY created_at DESC, id DESC",
                ),
                {"collection_id": collection_id},
            )
            return rows_to_dicts(result)

    def update_document(self, document_id: int, **fields: Any) -> RepositoryResult:
        allowed_fields = {"title", "file_name", "file_path", "num_pages"}
        payload = {key: value for key, value in fields.items() if key in allowed_fields}
        if not payload:
            return RepositoryResult(rows=[], rowcount=0)
        sql, params = dict_to_update(self.table_name, payload, "id = :target_id")
        params["target_id"] = document_id
        with self._connection_provider() as connection:
            result = connection.execute(text(sql), params)
        return RepositoryResult(rows=None, rowcount=result.rowcount)

    def delete_document(self, document_id: int) -> RepositoryResult:
        with self._connection_provider() as connection:
            result = connection.execute(
                text("DELETE FROM documents WHERE id = :id"),
                {"id": document_id},
            )
        return RepositoryResult(rows=None, rowcount=result.rowcount)
