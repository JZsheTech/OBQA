from __future__ import annotations

import json
import logging
import math
from typing import Any, Callable, ContextManager, Iterable, Mapping, Sequence

from sqlalchemy import text
from sqlalchemy.engine import Connection

from .base import RepositoryResult, dict_to_insert, dict_to_update, row_to_dict, rows_to_dicts
from .db import db_connection
from ..env_setting import VECTOR_DIM

logger = logging.getLogger(__name__)


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

    def list_unembedded(
        self,
        *,
        limit: int = 100,
        collection_id: int | None = None,
        doc_id: int | None = None,
    ) -> list[dict[str, Any]]:
        sql = [
            "SELECT e.id, e.doc_id, e.elem_type, e.text_content, e.text_caption, e.image_base64 ",
            "FROM elements e ",
            "JOIN documents d ON e.doc_id = d.id ",
            "WHERE e.vec_embedding IS NULL",
        ]
        params: dict[str, Any] = {"limit": limit}
        if collection_id is not None:
            sql.append(" AND d.collection_id = :collection_id")
            params["collection_id"] = collection_id
        if doc_id is not None:
            sql.append(" AND e.doc_id = :doc_id")
            params["doc_id"] = doc_id
        sql.append(" ORDER BY e.doc_id ASC, e.`order` ASC LIMIT :limit")
        query = "".join(sql)
        with self._connection_provider() as connection:
            result = connection.execute(text(query), params)
        return rows_to_dicts(result)

    def update_embeddings(self, embeddings: Mapping[int, Sequence[float]]) -> RepositoryResult:
        if not embeddings:
            return RepositoryResult(rows=None, rowcount=0)
        for element_id, vector in embeddings.items():
            if len(vector) != VECTOR_DIM:
                raise ValueError(
                    f"Embedding dimension mismatch for element {element_id}: "
                    f"{len(vector)} != {VECTOR_DIM}",
                )
        sql = text(
            f"UPDATE {self.table_name} "
            f"SET vec_embedding = CAST(:vec_embedding AS VECTOR({VECTOR_DIM})) "
            "WHERE id = :element_id",
        )
        payloads = [
            {
                "vec_embedding": self._serialize_vector(vector),
                "element_id": element_id,
            }
            for element_id, vector in embeddings.items()
        ]
        with self._connection_provider() as connection:
            result = connection.execute(sql, payloads)
        return RepositoryResult(rows=None, rowcount=result.rowcount)

    def topk_by_collection(
        self,
        *,
        collection_id: int,
        query_vec: Sequence[float],
        k: int = 5,
        doc_id: int | None = None,
        elem_types: set[str] | None = None,
        max_candidates: int | None = 2000,
    ) -> list[dict[str, Any]]:
        if len(query_vec) != VECTOR_DIM:
            raise ValueError("query_vec dimension mismatch.")
        candidates = self._fetch_candidates(
            collection_id=collection_id,
            doc_id=doc_id,
            require_vector=True,
            limit=max_candidates,
        )
        normalized_types = {entry.lower() for entry in elem_types} if elem_types else None
        scored: list[dict[str, Any]] = []
        for row in candidates:
            elem_type = (row.get("elem_type") or "").lower()
            if normalized_types and elem_type not in normalized_types:
                continue
            vector = self._deserialize_vector(row.get("vec_embedding"))
            if not vector or len(vector) != len(query_vec):
                continue
            score = self._cosine_similarity(query_vec, vector)
            if score is None:
                continue
            scored.append(
                {
                    "element_id": row["id"],
                    "doc_id": row["doc_id"],
                    "collection_id": row["collection_id"],
                    "page_no": row.get("page_no"),
                    "bbox": self._safe_json_loads(row.get("bbox_json")),
                    "elem_type": elem_type,
                    "score": score,
                    "text_content": row.get("text_content"),
                },
            )
        scored.sort(key=lambda item: item["score"], reverse=True)
        return scored[:k]

    def search_fulltext(
        self,
        *,
        collection_id: int,
        query: str,
        k: int = 5,
        doc_id: int | None = None,
        elem_types: set[str] | None = None,
        max_candidates: int | None = 1000,
    ) -> list[dict[str, Any]]:
        query = (query or "").strip()
        if not query:
            raise ValueError("query text must be provided for fulltext search.")
        normalized_query = query.lower()
        candidates = self._fetch_candidates(
            collection_id=collection_id,
            doc_id=doc_id,
            require_vector=False,
            limit=max_candidates,
        )
        normalized_types = {entry.lower() for entry in elem_types} if elem_types else None
        matches: list[dict[str, Any]] = []
        for row in candidates:
            elem_type = (row.get("elem_type") or "").lower()
            if normalized_types and elem_type not in normalized_types:
                continue
            text_blob = " ".join(
                part.strip()
                for part in [
                    row.get("text_content") or "",
                    row.get("text_caption") or "",
                ]
                if part
            )
            lowered = text_blob.lower()
            count = lowered.count(normalized_query)
            if count <= 0:
                continue
            score = count / max(1, len(lowered))
            matches.append(
                {
                    "element_id": row["id"],
                    "doc_id": row["doc_id"],
                    "collection_id": row["collection_id"],
                    "page_no": row.get("page_no"),
                    "bbox": self._safe_json_loads(row.get("bbox_json")),
                    "elem_type": elem_type,
                    "score": float(score),
                    "text_content": row.get("text_content"),
                },
            )
        matches.sort(key=lambda item: item["score"], reverse=True)
        return matches[:k]

    def _fetch_candidates(
        self,
        *,
        collection_id: int,
        doc_id: int | None,
        require_vector: bool,
        limit: int | None,
    ) -> list[dict[str, Any]]:
        sql_parts = [
            "SELECT e.id, e.doc_id, d.collection_id, e.page_no, e.bbox_json, ",
            "e.elem_type, e.text_content, e.text_caption, e.image_base64, e.vec_embedding ",
            "FROM elements e ",
            "JOIN documents d ON e.doc_id = d.id ",
            "WHERE d.collection_id = :collection_id",
        ]
        params: dict[str, Any] = {"collection_id": collection_id}
        if doc_id is not None:
            sql_parts.append(" AND e.doc_id = :doc_id")
            params["doc_id"] = doc_id
        if require_vector:
            sql_parts.append(" AND e.vec_embedding IS NOT NULL")
        sql_parts.append(" ORDER BY e.doc_id ASC, e.`order` ASC")
        if limit is not None:
            sql_parts.append(" LIMIT :limit")
            params["limit"] = limit
        query = "".join(sql_parts)
        with self._connection_provider() as connection:
            result = connection.execute(text(query), params)
        return rows_to_dicts(result)

    @staticmethod
    def _serialize_vector(vector: Sequence[float]) -> str:
        return json.dumps([float(value) for value in vector], separators=(",", ":"))

    @staticmethod
    def _deserialize_vector(raw_value: Any) -> list[float] | None:
        if raw_value is None:
            return None
        if isinstance(raw_value, (list, tuple)):
            return [float(value) for value in raw_value]
        if isinstance(raw_value, (bytes, bytearray)):
            raw_value = raw_value.decode("utf-8")
        try:
            parsed = json.loads(raw_value)
        except (TypeError, json.JSONDecodeError):
            logger.warning("Unable to decode vec_embedding payload: %s", raw_value)
            return None
        if not isinstance(parsed, list):
            return None
        return [float(value) for value in parsed]

    @staticmethod
    def _safe_json_loads(raw_value: Any) -> Any:
        if raw_value is None:
            return None
        if isinstance(raw_value, (dict, list)):
            return raw_value
        try:
            return json.loads(raw_value)
        except (TypeError, json.JSONDecodeError):
            return None

    @staticmethod
    def _cosine_similarity(vec_a: Sequence[float], vec_b: Sequence[float]) -> float | None:
        if len(vec_a) != len(vec_b):
            return None
        dot = 0.0
        norm_a = 0.0
        norm_b = 0.0
        for a, b in zip(vec_a, vec_b):
            dot += a * b
            norm_a += a * a
            norm_b += b * b
        if norm_a == 0.0 or norm_b == 0.0:
            return None
        return dot / math.sqrt(norm_a * norm_b)
