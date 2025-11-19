from __future__ import annotations

import logging

from ..llm.programs import MemorySummarizer

logger = logging.getLogger(__name__)


class MemoryService:
    """High-level helper that owns memory summarization logic."""

    def __init__(self, summarizer: MemorySummarizer | None = None) -> None:
        self._summarizer = summarizer or MemorySummarizer()

    def summarize_history(self, history_text: str) -> str:
        try:
            return self._summarizer.summarize(history_text)
        except Exception as exc:  # pragma: no cover - runtime guard
            logger.warning("Memory summarization failed: %s", exc)
            return ""


__all__ = ["MemoryService"]
