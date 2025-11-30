from __future__ import annotations

import re
from typing import Any, Iterable, Mapping, Sequence

from ...env_setting import CHUNK_SKIP_PATTERNS, MAX_ELEM_CHUNK_SIZE, MIN_CHARACTOR_CHUNK_SIZE


class ChunkBuilder:
    """Builds chunk-level records from normalized elements."""

    def __init__(
        self,
        *,
        min_chars: int = MIN_CHARACTOR_CHUNK_SIZE,
        max_elem: int = MAX_ELEM_CHUNK_SIZE,
        skip_patterns: Sequence[str] = CHUNK_SKIP_PATTERNS,
    ) -> None:
        self._min_chars = max(1, min_chars)
        self._max_elem = max(1, max_elem)
        self._skip_regexes = [re.compile(pattern) for pattern in skip_patterns if pattern]

    def build_chunks(
        self,
        *,
        doc_id: int,
        collection_id: int,
        elements: Sequence[Mapping[str, Any]],
    ) -> list[dict[str, Any]]:
        records: list[dict[str, Any]] = []
        buffer: list[Mapping[str, Any]] = []
        buffer_texts: list[str] = []
        buffer_pages: list[int] = []
        current_nav: str | None = None
        running_chars = 0
        chunk_order = 0

        def flush_text_chunk() -> None:
            nonlocal buffer, buffer_texts, buffer_pages, running_chars, chunk_order
            if not buffer or not buffer_texts:
                buffer = []
                buffer_texts = []
                buffer_pages = []
                running_chars = 0
                return
            chunk_order += 1
            elem_ids = [int(entry["id"]) for entry in buffer if entry.get("id") is not None]
            records.append(
                {
                    "doc_id": doc_id,
                    "collection_id": collection_id,
                    "order": chunk_order,
                    "level_nav": current_nav,
                    "chunk_type": "text",
                    "chunk_text_main": "\n\n".join(buffer_texts).strip(),
                    "elem_ids": elem_ids,
                    "page_start": min(buffer_pages) if buffer_pages else None,
                    "page_end": max(buffer_pages) if buffer_pages else None,
                },
            )
            buffer = []
            buffer_texts = []
            buffer_pages = []
            running_chars = 0

        sorted_elements = sorted(
            elements,
            key=lambda row: int(row.get("order") or 0),
        )
        for element in sorted_elements:
            elem_type = (element.get("elem_type") or "").lower()
            nav = self._clean_nav(element.get("level_nav"))
            page_no = self._safe_int(element.get("page_no"))
            text = self._normalize_text(element, elem_type)
            if elem_type in {"image", "table"}:
                flush_text_chunk()
                if not text and text != "":
                    continue
                chunk_order += 1
                elem_id = element.get("id")
                elem_ids = [int(elem_id)] if elem_id is not None else []
                records.append(
                    {
                        "doc_id": doc_id,
                        "collection_id": collection_id,
                        "order": chunk_order,
                        "level_nav": nav,
                        "chunk_type": elem_type,
                        "chunk_text_main": text,
                        "elem_ids": elem_ids,
                        "page_start": page_no,
                        "page_end": page_no,
                    },
                )
                continue

            if current_nav != nav:
                flush_text_chunk()
                current_nav = nav
            if not text:
                continue
            buffer.append(element)
            buffer_texts.append(text)
            if page_no is not None:
                buffer_pages.append(page_no)
            running_chars += len(text)
            if running_chars >= self._min_chars and len(buffer) >= self._max_elem:
                flush_text_chunk()

        flush_text_chunk()
        return [record for record in records if record.get("chunk_text_main") or record.get("chunk_type") in {"image", "table"}]

    def build_page_chunks(
        self,
        *,
        doc_id: int,
        collection_id: int,
        elements: Sequence[Mapping[str, Any]],
    ) -> list[dict[str, Any]]:
        grouped: dict[int, dict[str, Any]] = {}
        sorted_elements = sorted(
            elements,
            key=lambda row: int(row.get("order") or 0),
        )
        for element in sorted_elements:
            elem_type = (element.get("elem_type") or "").lower()
            if elem_type in {"image", "table"}:
                continue
            page_no = self._safe_int(element.get("page_no"))
            if page_no is None:
                continue
            text = self._normalize_text(element, elem_type)
            if not text:
                continue
            bucket = grouped.setdefault(
                page_no,
                {
                    "doc_id": doc_id,
                    "collection_id": collection_id,
                    "chunk_text_main": [],
                    "elem_ids": [],
                    "page_no": page_no,
                    "chunk_type": "text",
                },
            )
            bucket["chunk_text_main"].append(text)
            elem_id = element.get("id")
            if elem_id is not None:
                bucket["elem_ids"].append(int(elem_id))
        records: list[dict[str, Any]] = []
        for page_no in sorted(grouped.keys()):
            bucket = grouped[page_no]
            text_main = "\n\n".join(bucket["chunk_text_main"]).strip()
            if not text_main:
                continue
            records.append(
                {
                    "doc_id": doc_id,
                    "collection_id": collection_id,
                    "chunk_text_main": text_main,
                    "elem_ids": bucket["elem_ids"],
                    "page_no": page_no,
                    "chunk_type": "text",
                },
            )
        return records

    def _normalize_text(self, element: Mapping[str, Any], elem_type: str) -> str:
        base_text = element.get("raw_text_content") or ""
        if not base_text and elem_type in {"image", "table"}:
            base_text = element.get("text_caption") or ""
        cleaned = self._strip_control_characters(str(base_text))
        cleaned = cleaned.strip()
        if self._should_skip_text(cleaned):
            return ""
        return cleaned

    def _clean_nav(self, level_nav: Any) -> str:
        value = str(level_nav or "").strip()
        return value or "root"

    @staticmethod
    def _safe_int(value: Any) -> int | None:
        try:
            return int(value) if value is not None else None
        except (TypeError, ValueError):
            return None

    def _should_skip_text(self, text: str) -> bool:
        if not text:
            return True
        for regex in self._skip_regexes:
            if regex.search(text):
                return True
        return False

    @staticmethod
    def _strip_control_characters(text: str) -> str:
        return "".join(ch for ch in text if ch >= " " or ch in {"\n", "\t"})


__all__ = ["ChunkBuilder"]
