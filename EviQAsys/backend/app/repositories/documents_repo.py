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
        file_sha256: str | None = None,
        file_size_bytes: int | None = None,
        num_pages: int | None = None,
        abstract: str | None = None,
        meta_info: dict[str, Any] | None = None,
        md_text: str | None = None,
        element_count: int | None = None,
    ) -> dict[str, Any]:
        payload = {
            "collection_id": collection_id,
            "title": title,
            "file_name": file_name,
            "file_path": file_path,
            "file_sha256": file_sha256,
            "file_size_bytes": file_size_bytes,
            "num_pages": num_pages,
            "abstract": abstract,
            "meta_info": meta_info,
            "md_text": md_text,
            "element_count": element_count,
        }
        sql, params = dict_to_insert(self.table_name, payload)
        with self._connection_provider() as connection:
            result = connection.execute(text(sql), params)
            doc_id = result.lastrowid
            fetched = connection.execute(
                text(
                    "SELECT id, collection_id, title, md_text, abstract, file_name, file_path, file_sha256, "
                    "file_size_bytes, num_pages, element_count, meta_info, created_at "
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
                    "SELECT id, collection_id, title, md_text, abstract, file_name, file_path, file_sha256, "
                    "file_size_bytes, num_pages, element_count, meta_info, created_at "
                    "FROM documents WHERE id = :id",
                ),
                {"id": document_id},
            )
            return row_to_dict(result)

    def list_by_collection(self, collection_id: int) -> list[dict[str, Any]]:
        with self._connection_provider() as connection:
            result = connection.execute(
                text(
                    "SELECT id, collection_id, title, md_text, abstract, file_name, file_path, file_sha256, "
                    "file_size_bytes, num_pages, element_count, meta_info, created_at "
                    "FROM documents WHERE collection_id = :collection_id "
                    "ORDER BY created_at DESC, id DESC",
                ),
                {"collection_id": collection_id},
            )
            return rows_to_dicts(result)

    def search_in_collection(self, collection_id: int, *, field: str, keyword: str) -> list[dict[str, Any]]:
        """Search documents within a collection by title/abstract/md_text using case-insensitive LIKE."""
        normalized_field = (field or "").strip().lower()
        field_mapping = {
            "title": "LOWER(COALESCE(title,''))",
            "abstract": "LOWER(COALESCE(abstract,''))",
            "md_text": "LOWER(COALESCE(md_text,''))",
        }
        if normalized_field not in field_mapping:
            raise ValueError("Unsupported search field for documents.")
        trimmed_keyword = (keyword or "").strip()
        if not trimmed_keyword:
            return self.list_by_collection(collection_id)
        like_pattern = f"%{trimmed_keyword.lower()}%"
        predicate = field_mapping[normalized_field]
        with self._connection_provider() as connection:
            result = connection.execute(
                text(
                    "SELECT id, collection_id, title, md_text, abstract, file_name, file_path, file_sha256, "
                    "file_size_bytes, num_pages, element_count, meta_info, created_at "
                    "FROM documents WHERE collection_id = :collection_id "
                    f"AND {predicate} LIKE :pattern "
                    "ORDER BY created_at DESC, id DESC",
                ),
                {"collection_id": collection_id, "pattern": like_pattern},
            )
            return rows_to_dicts(result)

    def update_document(self, document_id: int, **fields: Any) -> RepositoryResult:
        allowed_fields = {
            "title",
            "file_name",
            "file_path",
            "file_sha256",
            "file_size_bytes",
            "num_pages",
            "element_count",
            "abstract",
            "meta_info",
            "md_text",
        }
        payload = {key: value for key, value in fields.items() if key in allowed_fields}
        if not payload:
            return RepositoryResult(rows=[], rowcount=0)
        sql, params = dict_to_update(self.table_name, payload, "id = :target_id")
        params["target_id"] = document_id
        with self._connection_provider() as connection:
            result = connection.execute(text(sql), params)
        return RepositoryResult(rows=None, rowcount=result.rowcount)

    def find_duplicate(
        self,
        *,
        collection_id: int,
        file_name: str,
        file_sha256: str,
    ) -> dict[str, Any] | None:
        with self._connection_provider() as connection:
            result = connection.execute(
                text(
                    "SELECT id, collection_id, title, md_text, abstract, file_name, file_path, file_sha256, "
                    "file_size_bytes, num_pages, element_count, meta_info, created_at "
                    "FROM documents "
                    "WHERE collection_id = :collection_id AND file_name = :file_name "
                    "AND file_sha256 = :file_sha256 "
                    "ORDER BY created_at DESC LIMIT 1",
                ),
                {
                    "collection_id": collection_id,
                    "file_name": file_name,
                    "file_sha256": file_sha256,
                },
            )
            return row_to_dict(result)

    def delete_document(self, document_id: int) -> RepositoryResult:
        with self._connection_provider() as connection:
            result = connection.execute(
                text("DELETE FROM documents WHERE id = :id"),
                {"id": document_id},
            )
        return RepositoryResult(rows=None, rowcount=result.rowcount)
