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
        prefix = f"[Elem#{self.element_id}] ({self.elem_type}){score_hint}"
        return f"{prefix}\n{snippet}"


@dataclass(slots=True)
class CandidateElement:
    """Element payload passed into AnswerAgent."""

    element_id: int
    elem_type: str
    doc_id: int | None = None
    page_no: int | None = None
    bbox: list[float] | None = None
    text_content: str | None = None
    image_base64: str | None = None
    text_caption: str | None = None
    level_nav: str | None = None

    def as_answer_dict(self) -> dict[str, object]:
        return {
            "element_id": self.element_id,
            "elem_type": self.elem_type,
            "doc_id": self.doc_id,
            "page_no": self.page_no,
            "bbox": self.bbox,
            "text_content": self.text_content,
            "text_caption": self.text_caption,
            "image_base64": self.image_base64,
            "level_nav": self.level_nav,
        }


@dataclass(slots=True)
class QATurnResult:
    """M4 QA pipeline result before schema serialization."""

    turn_id: int
    chat_id: int
    answer_text: str
    evidences: list[dict[str, Any]] = field(default_factory=list)


__all__ = ["EvidenceText", "CandidateElement", "QATurnResult"]
