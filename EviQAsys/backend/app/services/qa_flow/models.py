from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ...env_setting import EVIDENCE_PROMPT_CHAR_LIMIT


@dataclass(slots=True)
class EvidenceText:
    """Normalized textual payload passed into DSPy programs."""

    element_id: int
    elem_type: str
    text_content: str
    score: float | None = None

    def as_prompt_entry(self) -> str:
        snippet = (self.text_content or "").strip()
        if len(snippet) > EVIDENCE_PROMPT_CHAR_LIMIT:
            snippet = f"{snippet[:EVIDENCE_PROMPT_CHAR_LIMIT]}..."
        score_hint = f" score={self.score:.4f}" if self.score is not None else ""
        return f"id={self.element_id} type={self.elem_type}{score_hint}\n{snippet}"


@dataclass(slots=True)
class QATurnResult:
    """M4 QA pipeline result before schema serialization."""

    turn_id: int
    chat_id: int
    answer_text: str
    evidences: list[dict[str, Any]] = field(default_factory=list)


__all__ = ["EvidenceText", "QATurnResult"]
