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

    def bulk_create(self, records: Iterable[dict[str, Any]]) -> RepositoryResult:
        payloads = []
        for record in records:
            payload = {key: record[key] for key in record if key in self.writable_fields}
            if not payload:
                continue
            payloads.append(payload)
        inserted = 0
        with self._connection_provider() as connection:
            for payload in payloads:
                sql, params = dict_to_insert(self.table_name, payload)
                connection.execute(text(sql), params)
                inserted += 1
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
