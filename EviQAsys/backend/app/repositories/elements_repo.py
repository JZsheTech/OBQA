from __future__ import annotations

from typing import Any, Callable, ContextManager, Iterable

from sqlalchemy import text
from sqlalchemy.engine import Connection

from .base import RepositoryResult, dict_to_insert, dict_to_update, row_to_dict, rows_to_dicts
from .db import db_connection


class ElementsRepository:
    """Direct SQL helpers for the elements table."""

    table_name = "elements"
    writable_fields: set[str] = {
        "doc_id",
        "order",
        "elem_type",
        "header_name",
        "header_level",
        "level_nav",
        "text_content",
        "text_caption",
        "image_base64",
        "bbox_json",
        "page_no",
        "vec_embedding",
        "order_start",
        "order_end",
    }

    def __init__(
        self,
        connection_provider: Callable[[], ContextManager[Connection]] = db_connection,
    ) -> None:
        self._connection_provider = connection_provider

    def create_element(self, data: dict[str, Any]) -> dict[str, Any]:
        payload = {key: data[key] for key in data if key in self.writable_fields}
        if "doc_id" not in payload:
            raise ValueError("doc_id is required to create an element.")
        sql, params = dict_to_insert(self.table_name, payload)
        with self._connection_provider() as connection:
            result = connection.execute(text(sql), params)
            element_id = result.lastrowid
            fetched = connection.execute(
                text("SELECT * FROM elements WHERE id = :id"),
                {"id": element_id},
            )
            row = row_to_dict(fetched)
        return row or {}

    def batch_insert(self, records: Iterable[dict[str, Any]], *, batch_size: int = 32) -> RepositoryResult:
        rows: list[dict[str, Any]] = []
        for record in records:
            payload = {key: record.get(key) for key in self.writable_fields}
            if payload.get("doc_id") is None:
                raise ValueError("doc_id is required for element rows.")
            if payload.get("order") is None:
                raise ValueError("order is required for element rows.")
            if payload.get("elem_type") is None:
                raise ValueError("elem_type is required for element rows.")
            rows.append(payload)
        if not rows:
            return RepositoryResult(rows=None, rowcount=0)

        inserted = 0
        columns = sorted({column for row in rows for column in row.keys() if row[column] is not None or column in {"doc_id", "order", "elem_type"}})
        placeholders = ", ".join(f":{column}" for column in columns)
        columns_clause = ", ".join(f"`{column}`" for column in columns)
        sql = f"INSERT INTO {self.table_name} ({columns_clause}) VALUES ({placeholders})"

        def _chunk(payloads: list[dict[str, Any]], size: int) -> Iterable[list[dict[str, Any]]]:
            for start in range(0, len(payloads), size):
                yield payloads[start : start + size]

        with self._connection_provider() as connection:
            for chunk in _chunk(rows, max(1, batch_size)):
                normalized_chunk = [{column: row.get(column) for column in columns} for row in chunk]
                connection.execute(text(sql), normalized_chunk)
                inserted += len(chunk)

        return RepositoryResult(rows=None, rowcount=inserted)

    def get_by_id(self, element_id: int) -> dict[str, Any] | None:
        with self._connection_provider() as connection:
            result = connection.execute(
                text("SELECT * FROM elements WHERE id = :id"),
                {"id": element_id},
            )
            return row_to_dict(result)

    def list_by_document(self, doc_id: int) -> list[dict[str, Any]]:
        with self._connection_provider() as connection:
            result = connection.execute(
                text(
                    "SELECT * FROM elements WHERE doc_id = :doc_id "
                    "ORDER BY `order` ASC",
                ),
                {"doc_id": doc_id},
            )
            return rows_to_dicts(result)

    def update_element(self, element_id: int, **fields: Any) -> RepositoryResult:
        payload = {key: value for key, value in fields.items() if key in self.writable_fields}
        if not payload:
            return RepositoryResult(rows=[], rowcount=0)
        sql, params = dict_to_update(self.table_name, payload, "id = :target_id")
        params["target_id"] = element_id
        with self._connection_provider() as connection:
            result = connection.execute(text(sql), params)
        return RepositoryResult(rows=None, rowcount=result.rowcount)

    def delete_by_document(self, doc_id: int) -> RepositoryResult:
        with self._connection_provider() as connection:
            result = connection.execute(
                text("DELETE FROM elements WHERE doc_id = :doc_id"),
                {"doc_id": doc_id},
            )
        return RepositoryResult(rows=None, rowcount=result.rowcount)

    # TODO: add vector similarity search helpers in M3 when embeddings are available.
