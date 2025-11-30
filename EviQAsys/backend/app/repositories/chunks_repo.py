from __future__ import annotations

import json
import logging
import math
from typing import Any, Callable, ContextManager, Iterable, Mapping, Sequence

from sqlalchemy import bindparam, text
from sqlalchemy.engine import Connection

from .base import RepositoryResult, dict_to_update, row_to_dict, rows_to_dicts
from .db import db_connection
from ..env_setting import VECTOR_DIM

logger = logging.getLogger(__name__)


class ChunksRepository:
    """Gateway for the chunk-level index table."""

    table_name = "chunks"
    writable_fields: set[str] = {
        "doc_id",
        "collection_id",
        "order",
        "level_nav",
        "chunk_type",
        "chunk_text_main",
        "elem_ids",
        "page_start",
        "page_end",
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
            payload["chunk_type"] = (payload.get("chunk_type") or "").lower() or None
            payload["elem_ids"] = self._serialize_elem_ids(record.get("elem_ids"))
            if payload.get("doc_id") is None:
                raise ValueError("doc_id is required for chunk rows.")
            if payload.get("collection_id") is None:
                raise ValueError("collection_id is required for chunk rows.")
            if payload.get("order") is None:
                raise ValueError("order is required for chunk rows.")
            if payload.get("chunk_type") not in {"text", "image", "table"}:
                raise ValueError(f"Unsupported chunk_type: {payload.get('chunk_type')}")
            rows.append(payload)
        if not rows:
            return RepositoryResult(rows=None, rowcount=0)

        inserted = 0
        columns = sorted({column for row in rows for column in row.keys() if row[column] is not None or column in {"doc_id", "collection_id", "order", "chunk_type"}})
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
                text(
                    f"SELECT * FROM {self.table_name} WHERE doc_id = :doc_id ORDER BY `order` ASC",
                ),
                {"doc_id": doc_id},
            )
            rows = rows_to_dicts(result)
        for row in rows:
            row["elem_ids"] = self._deserialize_elem_ids(row.get("elem_ids"))
        return rows

    def list_by_ids(self, chunk_ids: Iterable[int]) -> list[dict[str, Any]]:
        normalized = [int(chunk_id) for chunk_id in dict.fromkeys(chunk_ids) if chunk_id is not None]
        if not normalized:
            return []
        query = text(
            f"SELECT * FROM {self.table_name} WHERE id IN :ids",
        ).bindparams(bindparam("ids", expanding=True))
        with self._connection_provider() as connection:
            result = connection.execute(query, {"ids": normalized})
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
        chunk_types: set[str] | None = None,
    ) -> list[dict[str, Any]]:
        sql = [
            "SELECT id, doc_id, collection_id, chunk_type, chunk_text_main, elem_ids, page_start, page_end ",
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
        if chunk_types:
            sql.append(" AND chunk_type IN :chunk_types")
            params["chunk_types"] = tuple(chunk_types)
        sql.append(" ORDER BY doc_id ASC, `order` ASC LIMIT :limit")
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
                    f"Embedding dimension mismatch for chunk {chunk_id}: {len(vector)} != {VECTOR_DIM}",
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
        chunk_types: set[str] | None = None,
        page_filters: Sequence[tuple[int, int]] | None = None,
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
        normalized_types = {entry.lower() for entry in chunk_types} if chunk_types else None
        results: list[dict[str, Any]] = []
        for row in candidates:
            chunk_type = (row.get("chunk_type") or "").lower()
            if normalized_types and chunk_type not in normalized_types:
                continue
            if page_filters and not self._match_page_filters(row, page_filters):
                continue
            vector = self._deserialize_vector(row.get("vec_embedding"))
            if not vector or len(vector) != len(query_vec):
                continue
            score = self._cosine_similarity(query_vec, vector)
            if score is None:
                continue
            results.append(self._format_row(row, score=score))
        results.sort(key=lambda item: item["score"], reverse=True)
        return results[:k]

    def search_fulltext(
        self,
        *,
        collection_id: int,
        query: str,
        k: int = 5,
        doc_id: int | None = None,
        chunk_types: set[str] | None = None,
        page_filters: Sequence[tuple[int, int]] | None = None,
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
        normalized_types = {entry.lower() for entry in chunk_types} if chunk_types else None
        matches: list[dict[str, Any]] = []
        for row in candidates:
            chunk_type = (row.get("chunk_type") or "").lower()
            if normalized_types and chunk_type not in normalized_types:
                continue
            if page_filters and not self._match_page_filters(row, page_filters):
                continue
            text_blob = (row.get("chunk_text_main") or "").strip()
            lowered = text_blob.lower()
            count = lowered.count(normalized_query)
            if count <= 0:
                continue
            score = count / max(1, len(lowered))
            matches.append(self._format_row(row, score=float(score)))
        matches.sort(key=lambda item: item["score"], reverse=True)
        return matches[:k]

    def search_hybrid(
        self,
        *,
        collection_id: int,
        query: str,
        query_vec: Sequence[float],
        k: int = 5,
        doc_id: int | None = None,
        chunk_types: set[str] | None = None,
        page_filters: Sequence[tuple[int, int]] | None = None,
        vector_weight: float = 0.65,
        fulltext_weight: float = 0.35,
        max_candidates: int | None = 200,
    ) -> list[dict[str, Any]]:
        if len(query_vec) != VECTOR_DIM:
            raise ValueError("query_vec dimension mismatch.")
        query = (query or "").strip()
        if not query:
            raise ValueError("query text must be provided for hybrid search.")
        candidate_limit = min(max(k, 20), max_candidates or max(k, 20))
        vector_rows = self.topk_by_collection(
            collection_id=collection_id,
            query_vec=query_vec,
            k=candidate_limit,
            doc_id=doc_id,
            chunk_types=chunk_types,
            page_filters=page_filters,
            max_candidates=max_candidates,
        )
        fulltext_rows = self.search_fulltext(
            collection_id=collection_id,
            query=query,
            k=candidate_limit,
            doc_id=doc_id,
            chunk_types=chunk_types,
            page_filters=page_filters,
            max_candidates=max_candidates,
        )
        max_fulltext_score = max((float(row.get("score") or 0.0) for row in fulltext_rows), default=0.0)
        vector_map = {int(row["chunk_id"]): row for row in vector_rows}
        fulltext_map = {int(row["chunk_id"]): row for row in fulltext_rows}
        combined: dict[int, dict[str, Any]] = {}
        for chunk_id, row in vector_map.items():
            combined[chunk_id] = {
                **row,
                "vector_score": float(row.get("score") or 0.0),
            }
        for chunk_id, row in fulltext_map.items():
            payload = combined.get(chunk_id, {**row})
            payload["fulltext_score"] = float(row.get("score") or 0.0)
            combined[chunk_id] = payload

        def _normalize_vector_score(score: float | None) -> float | None:
            if score is None:
                return None
            return max(0.0, min(1.0, (float(score) + 1.0) / 2.0))

        def _normalize_fulltext_score(score: float | None, *, max_score: float) -> float | None:
            if score is None:
                return None
            numeric = max(0.0, float(score))
            if max_score > 0.0:
                return min(1.0, numeric / max_score)
            return numeric

        def _blend_scores(vector_score: float | None, text_score: float | None) -> float | None:
            weights = []
            blended = 0.0
            if vector_score is not None:
                weights.append(vector_weight)
                blended += vector_weight * vector_score
            if text_score is not None:
                weights.append(fulltext_weight)
                blended += fulltext_weight * text_score
            total = sum(weights)
            if total <= 0.0:
                return None
            return blended / total

        scored_results: list[dict[str, Any]] = []
        for chunk_id, payload in combined.items():
            vector_score = _normalize_vector_score(payload.get("vector_score"))
            text_score = _normalize_fulltext_score(payload.get("fulltext_score"), max_score=max_fulltext_score)
            blended_score = _blend_scores(vector_score, text_score)
            if blended_score is None:
                continue
            payload["score"] = blended_score
            scored_results.append(payload)

        scored_results.sort(key=lambda item: item["score"], reverse=True)
        return scored_results[:k]

    def _fetch_candidates(
        self,
        *,
        collection_id: int,
        doc_id: int | None,
        require_vector: bool,
        limit: int | None,
    ) -> list[dict[str, Any]]:
        sql_parts = [
            "SELECT * FROM chunks WHERE collection_id = :collection_id",
        ]
        params: dict[str, Any] = {"collection_id": collection_id}
        if doc_id is not None:
            sql_parts.append(" AND doc_id = :doc_id")
            params["doc_id"] = doc_id
        if require_vector:
            sql_parts.append(" AND vec_embedding IS NOT NULL")
        sql_parts.append(" ORDER BY doc_id ASC, `order` ASC")
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

    def _match_page_filters(self, row: Mapping[str, Any], filters: Sequence[tuple[int, int]]) -> bool:
        if not filters:
            return True
        doc_id = int(row.get("doc_id") or 0)
        page_start = row.get("page_start")
        page_end = row.get("page_end")
        for filter_doc, page_no in filters:
            if filter_doc != doc_id:
                continue
            if page_start is not None and page_end is not None:
                if int(page_start) <= page_no <= int(page_end):
                    return True
        return False

    def _format_row(self, row: Mapping[str, Any], *, score: float) -> dict[str, Any]:
        return {
            "chunk_id": int(row["id"]),
            "doc_id": int(row["doc_id"]),
            "collection_id": int(row["collection_id"]),
            "order": row.get("order"),
            "level_nav": row.get("level_nav"),
            "chunk_type": (row.get("chunk_type") or "").lower(),
            "chunk_text_main": row.get("chunk_text_main"),
            "elem_ids": self._deserialize_elem_ids(row.get("elem_ids")),
            "page_start": row.get("page_start"),
            "page_end": row.get("page_end"),
            "score": float(score),
        }


__all__ = ["ChunksRepository"]
