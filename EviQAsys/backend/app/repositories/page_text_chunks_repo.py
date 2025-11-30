from __future__ import annotations

import json
import logging
import math
from typing import Any, Callable, ContextManager, Iterable, Mapping, Sequence

from sqlalchemy import bindparam, text
from sqlalchemy.engine import Connection

from .base import RepositoryResult, rows_to_dicts
from .db import db_connection
from ..env_setting import VECTOR_DIM

logger = logging.getLogger(__name__)


class PageTextChunksRepository:
    """Gateway for page-level aggregated text chunks."""

    table_name = "page_text_chunks"
    writable_fields: set[str] = {
        "doc_id",
        "collection_id",
        "chunk_text_main",
        "elem_ids",
        "page_no",
        "chunk_type",
        "vec_embedding",
    }

    def __init__(
        self,
        connection_provider: Callable[[], ContextManager[Connection]] = db_connection,
    ) -> None:
        self._connection_provider = connection_provider

    def batch_insert(self, records: Iterable[dict[str, Any]], *, batch_size: int = 32) -> RepositoryResult:
        rows: list[dict[str, Any]] = []
        for record in records:
            payload = {key: record.get(key) for key in self.writable_fields}
            payload["chunk_type"] = (payload.get("chunk_type") or "text").lower()
            payload["elem_ids"] = self._serialize_elem_ids(record.get("elem_ids"))
            if payload.get("doc_id") is None:
                raise ValueError("doc_id is required for page_text_chunks.")
            if payload.get("collection_id") is None:
                raise ValueError("collection_id is required for page_text_chunks.")
            if payload.get("page_no") is None:
                raise ValueError("page_no is required for page_text_chunks.")
            rows.append(payload)
        if not rows:
            return RepositoryResult(rows=None, rowcount=0)

        inserted = 0
        columns = sorted({column for row in rows for column in row.keys() if row[column] is not None or column in {"doc_id", "collection_id", "page_no", "chunk_type"}})
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

    def delete_by_document(self, doc_id: int) -> RepositoryResult:
        with self._connection_provider() as connection:
            result = connection.execute(
                text(f"DELETE FROM {self.table_name} WHERE doc_id = :doc_id"),
                {"doc_id": doc_id},
            )
        return RepositoryResult(rows=None, rowcount=result.rowcount)

    def list_by_document(self, doc_id: int) -> list[dict[str, Any]]:
        with self._connection_provider() as connection:
            result = connection.execute(
                text(f"SELECT * FROM {self.table_name} WHERE doc_id = :doc_id ORDER BY page_no ASC"),
                {"doc_id": doc_id},
            )
            rows = rows_to_dicts(result)
        for row in rows:
            row["elem_ids"] = self._deserialize_elem_ids(row.get("elem_ids"))
        return rows

    def list_unembedded(
        self,
        *,
        limit: int = 100,
        collection_id: int | None = None,
        doc_id: int | None = None,
    ) -> list[dict[str, Any]]:
        sql = [
            "SELECT id, doc_id, collection_id, chunk_text_main, elem_ids, page_no ",
            f"FROM {self.table_name} ",
            "WHERE vec_embedding IS NULL",
        ]
        params: dict[str, Any] = {"limit": limit}
        if collection_id is not None:
            sql.append(" AND collection_id = :collection_id")
            params["collection_id"] = collection_id
        if doc_id is not None:
            sql.append(" AND doc_id = :doc_id")
            params["doc_id"] = doc_id
        sql.append(" ORDER BY doc_id ASC, page_no ASC LIMIT :limit")
        query = "".join(sql)
        with self._connection_provider() as connection:
            result = connection.execute(text(query), params)
            rows = rows_to_dicts(result)
        for row in rows:
            row["elem_ids"] = self._deserialize_elem_ids(row.get("elem_ids"))
        return rows

    def update_embeddings(self, embeddings: Mapping[int, Sequence[float]]) -> RepositoryResult:
        if not embeddings:
            return RepositoryResult(rows=None, rowcount=0)
        for chunk_id, vector in embeddings.items():
            if len(vector) != VECTOR_DIM:
                raise ValueError(
                    f"Embedding dimension mismatch for page chunk {chunk_id}: {len(vector)} != {VECTOR_DIM}",
                )
        sql = text(
            f"UPDATE {self.table_name} "
            f"SET vec_embedding = :vec_embedding "
            "WHERE id = :chunk_id",
        )
        payloads = [
            {
                "vec_embedding": self._serialize_vector(vector),
                "chunk_id": chunk_id,
            }
            for chunk_id, vector in embeddings.items()
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
        results: list[dict[str, Any]] = []
        for row in candidates:
            vector = self._deserialize_vector(row.get("vec_embedding"))
            if not vector or len(vector) != len(query_vec):
                continue
            score = self._cosine_similarity(query_vec, vector)
            if score is None:
                continue
            results.append(
                {
                    "page_chunk_id": int(row["id"]),
                    "doc_id": int(row["doc_id"]),
                    "collection_id": int(row["collection_id"]),
                    "page_no": row.get("page_no"),
                    "elem_ids": self._deserialize_elem_ids(row.get("elem_ids")),
                    "chunk_text_main": row.get("chunk_text_main"),
                    "score": float(score),
                },
            )
        results.sort(key=lambda item: item["score"], reverse=True)
        return results[:k]

    def _fetch_candidates(
        self,
        *,
        collection_id: int,
        doc_id: int | None,
        require_vector: bool,
        limit: int | None,
    ) -> list[dict[str, Any]]:
        sql_parts = [
            "SELECT * FROM page_text_chunks WHERE collection_id = :collection_id",
        ]
        params: dict[str, Any] = {"collection_id": collection_id}
        if doc_id is not None:
            sql_parts.append(" AND doc_id = :doc_id")
            params["doc_id"] = doc_id
        if require_vector:
            sql_parts.append(" AND vec_embedding IS NOT NULL")
        sql_parts.append(" ORDER BY doc_id ASC, page_no ASC")
        if limit is not None:
            sql_parts.append(" LIMIT :limit")
            params["limit"] = limit
        query = "".join(sql_parts)
        with self._connection_provider() as connection:
            result = connection.execute(text(query), params)
        rows = rows_to_dicts(result)
        for row in rows:
            row["elem_ids"] = self._deserialize_elem_ids(row.get("elem_ids"))
        return rows

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
    def _serialize_elem_ids(elem_ids: Any) -> str | None:
        if elem_ids is None:
            return None
        if isinstance(elem_ids, str):
            return elem_ids
        if not isinstance(elem_ids, Iterable):
            return None
        normalized = [int(elem_id) for elem_id in dict.fromkeys(elem_ids) if elem_id is not None]
        if not normalized:
            return None
        return json.dumps(normalized, separators=(",", ":"))

    @staticmethod
    def _deserialize_elem_ids(raw_value: Any) -> list[int]:
        if raw_value is None:
            return []
        if isinstance(raw_value, (list, tuple)):
            return [int(value) for value in raw_value if value is not None]
        if isinstance(raw_value, (bytes, bytearray)):
            raw_value = raw_value.decode("utf-8")
        try:
            parsed = json.loads(raw_value)
        except (TypeError, json.JSONDecodeError):
            return []
        if not isinstance(parsed, list):
            return []
        return [int(value) for value in parsed if value is not None]

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


__all__ = ["PageTextChunksRepository"]
