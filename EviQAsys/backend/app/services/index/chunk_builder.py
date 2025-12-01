from __future__ import annotations

import re
from typing import Any, Iterable, Mapping, Sequence

from ...env_setting import CHUNK_SKIP_PATTERNS, MAX_CHARACTOR_CHUNK_SIZE, MIN_CHARACTOR_CHUNK_SIZE


class ChunkBuilder:
    """Builds chunk-level records from normalized elements."""

    def __init__(
        self,
        *,
        min_chars: int = MIN_CHARACTOR_CHUNK_SIZE,
        max_chars: int = MAX_CHARACTOR_CHUNK_SIZE,
        skip_patterns: Sequence[str] = CHUNK_SKIP_PATTERNS,
    ) -> None:
        self._min_chars = max(1, min_chars)
        self._max_chars = max_chars
        if self._max_chars <= self._min_chars:
            raise ValueError("MAX_CHARACTOR_CHUNK_SIZE must be greater than MIN_CHARACTOR_CHUNK_SIZE.")
        self._skip_regexes = [re.compile(pattern) for pattern in skip_patterns if pattern]

    def build_chunks(
        self,
        *,
        doc_id: int,
        collection_id: int,
        elements: Sequence[Mapping[str, Any]],
    ) -> list[dict[str, Any]]:
        records: list[dict[str, Any]] = []
        buffer_elements: list[Mapping[str, Any]] = []
        buffer_texts: list[str] = []
        buffer_pages: list[int | None] = []
        running_chars = 0
        chunk_order = 0
        current_nav: str | None = None
        media_queue: list[dict[str, Any]] = []

        def _reset_text_state() -> None:
            nonlocal buffer_elements, buffer_texts, buffer_pages, running_chars
            buffer_elements = []
            buffer_texts = []
            buffer_pages = []
            running_chars = 0

        def _append_text_chunk() -> None:
            nonlocal chunk_order
            if not buffer_texts:
                _reset_text_state()
                return
            chunk_order += 1
            page_start, page_end = self._resolve_page_bounds(buffer_pages)
            elem_ids = [int(entry["id"]) for entry in buffer_elements if entry.get("id") is not None]
            records.append(
                {
                    "doc_id": doc_id,
                    "collection_id": collection_id,
                    "order": chunk_order,
                    "level_nav": current_nav,
                    "chunk_type": "text",
                    "chunk_text_main": "\n\n".join(buffer_texts).strip(),
                    "elem_ids": elem_ids,
                    "page_start": page_start,
                    "page_end": page_end,
                },
            )
            _reset_text_state()

        def _append_media_queue() -> None:
            nonlocal chunk_order, media_queue
            for media in media_queue:
                chunk_order += 1
                media["order"] = chunk_order
                records.append(media)
            media_queue = []

        def _finish_section() -> None:
            _append_text_chunk()
            _append_media_queue()

        sorted_elements = sorted(elements, key=lambda row: int(row.get("order") or 0))
        for element in sorted_elements:
            elem_type = (element.get("elem_type") or "").lower()
            nav = self._clean_nav(element.get("level_nav"))
            page_no = self._safe_int(element.get("page_no"))

            if current_nav is None:
                current_nav = nav
            elif nav != current_nav:
                _finish_section()
                current_nav = nav

            if elem_type in {"image", "table"}:
                media_text = self._build_media_text(element, elem_type)
                elem_id = element.get("id")
                elem_ids = [int(elem_id)] if elem_id is not None else []
                media_queue.append(
                    {
                        "doc_id": doc_id,
                        "collection_id": collection_id,
                        "level_nav": current_nav,
                        "chunk_type": elem_type,
                        "chunk_text_main": media_text,
                        "elem_ids": elem_ids,
                        "page_start": page_no,
                        "page_end": page_no,
                    },
                )
                continue

            text = self._normalize_textual_element(element)
            if not text:
                continue

            text_len = len(text)
            if text_len > self._max_chars:
                if buffer_texts and running_chars < self._min_chars:
                    # 未达到最小阈值时，将当前超长元素与缓冲合并为同一块，避免标题被孤立。
                    buffer_elements.append(element)
                    buffer_texts.append(text)
                    buffer_pages.append(page_no)
                    running_chars += text_len
                    _append_text_chunk()
                else:
                    _append_text_chunk()
                    chunk_order += 1
                    page_start, page_end = self._resolve_page_bounds([page_no])
                    elem_id = element.get("id")
                    elem_ids = [int(elem_id)] if elem_id is not None else []
                    records.append(
                        {
                            "doc_id": doc_id,
                            "collection_id": collection_id,
                            "order": chunk_order,
                            "level_nav": current_nav,
                            "chunk_type": "text",
                            "chunk_text_main": text,
                            "elem_ids": elem_ids,
                            "page_start": page_start,
                            "page_end": page_end,
                        },
                    )
                    _reset_text_state()
                continue

            prospective_chars = running_chars + text_len
            if prospective_chars > self._max_chars:
                if running_chars >= self._min_chars:
                    _append_text_chunk()
                    buffer_elements.append(element)
                    buffer_texts.append(text)
                    buffer_pages.append(page_no)
                    running_chars = text_len
                else:
                    buffer_elements.append(element)
                    buffer_texts.append(text)
                    buffer_pages.append(page_no)
                    running_chars = prospective_chars
                    _append_text_chunk()
                continue

            buffer_elements.append(element)
            buffer_texts.append(text)
            buffer_pages.append(page_no)
            running_chars = prospective_chars

        if current_nav is not None:
            _finish_section()
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
            text = self._normalize_textual_element(element)
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

    def _normalize_textual_element(self, element: Mapping[str, Any]) -> str:
        base_text = element.get("raw_text_content") or ""
        cleaned = self._strip_control_characters(str(base_text)).strip()
        if self._should_skip_text(cleaned):
            return ""
        return cleaned

    def _build_media_text(self, element: Mapping[str, Any], elem_type: str) -> str:
        parts: list[str] = []
        for field in ("raw_text_content", "text_content"):
            value = self._strip_control_characters(str(element.get(field) or "")).strip()
            if value:
                parts.append(value)
        caption = self._strip_control_characters(str(element.get("text_caption") or "")).strip()
        if caption:
            parts.append(caption)
        unique_parts: list[str] = []
        seen: set[str] = set()
        for part in parts:
            if self._should_skip_text(part):
                continue
            if part in seen:
                continue
            seen.add(part)
            unique_parts.append(part)
        combined = "\n\n".join(unique_parts).strip()
        return combined if combined or elem_type in {"image", "table"} else ""

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

    @staticmethod
    def _resolve_page_bounds(pages: Sequence[int | None]) -> tuple[int | None, int | None]:
        normalized = [page for page in pages if page is not None]
        if not normalized:
            return None, None
        return min(normalized), max(normalized)


__all__ = ["ChunkBuilder"]
