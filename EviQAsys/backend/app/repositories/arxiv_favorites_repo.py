from __future__ import annotations

import json
from typing import Any, Callable, ContextManager, Tuple

from sqlalchemy import text
from sqlalchemy.engine import Connection

from .base import RepositoryResult, dict_to_insert, dict_to_update, row_to_dict, rows_to_dicts
from .db import db_connection


def _to_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item) for item in value]
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            if isinstance(parsed, list):
                return [str(item) for item in parsed]
        except json.JSONDecodeError:
            return [value]
    return []


class ArxivFavoritesRepository:
    table_name = "arxiv_favorite_doc"

    def __init__(
        self,
        connection_provider: Callable[[], ContextManager[Connection]] = db_connection,
    ) -> None:
        self._connection_provider = connection_provider

    def upsert_favorite(
        self,
        *,
        arxiv_id: str,
        version: str | None,
        title: str,
        summary: str | None,
        authors: list[str] | None,
        primary_category: str | None,
        categories: list[str] | None,
        pdf_url: str | None,
        abs_url: str | None,
        doi: str | None,
        journal_ref: str | None,
        tags: str | None,
        note: str | None,
        published: Any | None,
        updated: Any | None,
    ) -> dict[str, Any]:
        authors_json = json.dumps(authors or [], ensure_ascii=False)
        categories_json = json.dumps(categories or [], ensure_ascii=False)
        insert_payload = {
            "arxiv_id": arxiv_id,
            "version": version,
            "title": title,
            "summary": summary,
            "authors": authors_json,
            "primary_category": primary_category,
            "categories": categories_json,
            "pdf_url": pdf_url,
            "abs_url": abs_url,
            "doi": doi,
            "journal_ref": journal_ref,
            "tags": tags,
            "note": note,
            "published": published,
            "updated": updated,
        }
        update_payload = {
            **insert_payload,
        }
        with self._connection_provider() as connection:
            existing = connection.execute(
                text(
                    "SELECT id FROM arxiv_favorite_doc WHERE arxiv_id = :arxiv_id LIMIT 1",
                ),
                {"arxiv_id": arxiv_id},
            )
            row = row_to_dict(existing)
            if row:
                sql, params = dict_to_update(self.table_name, update_payload, "id = :target_id")
                params["target_id"] = row["id"]
                connection.execute(text(sql), params)
                fetched = connection.execute(
                    text(self._base_query() + " WHERE afd.id = :id LIMIT 1"),
                    {"id": row["id"]},
                )
                return self._decode_row(row_to_dict(fetched) or {})

            sql, params = dict_to_insert(self.table_name, insert_payload)
            result = connection.execute(text(sql), params)
            favorite_id = result.lastrowid
            fetched = connection.execute(
                text(self._base_query() + " WHERE afd.id = :id LIMIT 1"),
                {"id": favorite_id},
            )
            return self._decode_row(row_to_dict(fetched) or {})

    def get_by_id(self, favorite_id: int) -> dict[str, Any] | None:
        with self._connection_provider() as connection:
            result = connection.execute(
                text(self._base_query() + " WHERE afd.id = :favorite_id LIMIT 1"),
                {"favorite_id": favorite_id},
            )
            row = row_to_dict(result)
            return self._decode_row(row) if row else None

    def list_favorites(
        self,
        *,
        page: int,
        page_size: int,
        keyword: str | None = None,
        author: str | None = None,
        category: str | None = None,
        tag: str | None = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
    ) -> Tuple[list[dict[str, Any]], int]:
        normalized_sort = sort_by if sort_by in {"created_at", "published", "updated"} else "created_at"
        normalized_order = "DESC" if str(sort_order).lower() == "desc" else "ASC"
        clauses = []
        params: dict[str, Any] = {}
        if keyword:
            clauses.append("(LOWER(afd.title) LIKE :kw OR LOWER(afd.summary) LIKE :kw)")
            params["kw"] = f"%{keyword.lower()}%"
        if author:
            clauses.append("LOWER(CAST(afd.authors AS CHAR)) LIKE :author")
            params["author"] = f"%{author.lower()}%"
        if category:
            clauses.append("LOWER(CAST(afd.categories AS CHAR)) LIKE :category")
            params["category"] = f"%{category.lower()}%"
        if tag:
            clauses.append("LOWER(afd.tags) LIKE :tag")
            params["tag"] = f"%{tag.lower()}%"
        where_clause = ""
        if clauses:
            where_clause = " WHERE " + " AND ".join(clauses)

        offset = max(0, (page - 1) * page_size)

        count_sql = "SELECT COUNT(*) AS total FROM arxiv_favorite_doc afd" + where_clause
        query_sql = (
            self._base_query()
            + where_clause
            + f" ORDER BY afd.{normalized_sort} {normalized_order} "
            "LIMIT :limit OFFSET :offset"
        )

        with self._connection_provider() as connection:
            total_result = connection.execute(text(count_sql), params)
            total_row = total_result.first()
            total = int(total_row[0]) if total_row else 0

            params_with_limit = {**params, "limit": page_size, "offset": offset}
            rows = connection.execute(text(query_sql), params_with_limit)
            decoded = [self._decode_row(row) for row in rows_to_dicts(rows)]
            return decoded, total

    def update_favorite(self, favorite_id: int, *, tags: str | None = None, note: str | None = None) -> RepositoryResult:
        payload = {}
        if tags is not None:
            payload["tags"] = tags
        if note is not None:
            payload["note"] = note
        if not payload:
            return RepositoryResult(rows=None, rowcount=0)
        sql, params = dict_to_update(self.table_name, payload, "id = :target_id")
        params["target_id"] = favorite_id
        with self._connection_provider() as connection:
            result = connection.execute(text(sql), params)
        return RepositoryResult(rows=None, rowcount=result.rowcount)

    def delete_favorite(self, favorite_id: int) -> RepositoryResult:
        with self._connection_provider() as connection:
            result = connection.execute(
                text("DELETE FROM arxiv_favorite_doc WHERE id = :favorite_id"),
                {"favorite_id": favorite_id},
            )
        return RepositoryResult(rows=None, rowcount=result.rowcount)

    def link_document(self, *, favorite_id: int, document_id: int) -> None:
        with self._connection_provider() as connection:
            connection.execute(
                text(
                    "UPDATE arxiv_favorite_doc SET document_id = :document_id WHERE id = :favorite_id",
                ),
                {"document_id": document_id, "favorite_id": favorite_id},
            )
            connection.execute(
                text(
                    "UPDATE documents SET arxiv_favorite_id = :favorite_id WHERE id = :document_id",
                ),
                {"favorite_id": favorite_id, "document_id": document_id},
            )

    def _base_query(self) -> str:
        return (
            "SELECT afd.id, afd.arxiv_id, afd.version, afd.title, afd.summary, afd.authors, afd.primary_category, "
            "afd.categories, afd.pdf_url, afd.abs_url, afd.doi, afd.journal_ref, afd.tags, afd.note, "
            "afd.published, afd.updated, afd.document_id, afd.created_at, afd.updated_at, "
            "d.title AS document_title, d.collection_id AS document_collection_id "
            "FROM arxiv_favorite_doc afd "
            "LEFT JOIN documents d ON afd.document_id = d.id"
        )

    def _decode_row(self, row: dict[str, Any]) -> dict[str, Any]:
        if not row:
            return {}
        return {
            **row,
            "authors": _to_list(row.get("authors")),
            "categories": _to_list(row.get("categories")),
        }


__all__ = ["ArxivFavoritesRepository"]
