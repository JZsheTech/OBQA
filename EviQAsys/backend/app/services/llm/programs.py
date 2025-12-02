from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Iterable, Sequence

from ...env_setting import LLMSettings, get_llm_settings
from ..qa_flow.models import EvidenceText

logger = logging.getLogger(__name__)

try:  # pragma: no cover - dspY import tested indirectly in runtime
    import dspy
except ImportError:  # pragma: no cover
    dspy = None


@dataclass(slots=True)
class RetrievalDecision:
    need_retrieve: bool
    element_types: list[str]


class DSPyPredictorFactory:
    """Creates DSPy Predict modules without mutating global settings (text LLM only)."""

    def __init__(self, *, text_llm_settings: LLMSettings | None = None, settings: LLMSettings | None = None) -> None:
        # `settings` kept for backward compatibility with older call sites.
        self._text_settings = text_llm_settings or settings or get_llm_settings()
        self._lm = None
        self._lm_params = {
            "model": f"openai/{self._text_settings.model}",
            "api_key": self._text_settings.api_key,
            "api_base": self._text_settings.api_base,
            "temperature": self._text_settings.temperature,
            "max_tokens": self._text_settings.max_output_tokens,
        }
        if dspy is not None:
            self._lm = self._init_lm()

    def _init_lm(self) -> object | None:
        try:
            lm_kwargs = {key: value for key, value in self._lm_params.items() if key != "model"}
            return dspy.LM(self._lm_params["model"], **lm_kwargs)
        except Exception as exc:  # pragma: no cover - initialization guard
            logger.warning("Failed to initialize DSPy LM: %s", exc)
            return None

    def create_predictor(self, signature_cls: type) -> object | None:
        if self._lm is None or dspy is None:
            return None
        try:
            predictor = dspy.Predict(signature_cls)
            predictor.set_lm(self._lm)
        except Exception as exc:  # pragma: no cover - runtime guard
            logger.warning("Failed to build DSPy predictor: %s", exc)
            return None
        return predictor


class MemorySummarizer:
    def __init__(
        self,
        *,
        predictor_factory: DSPyPredictorFactory | None = None,
        max_summary_chars: int = 1200,
        max_history_chars: int = 6000,
    ) -> None:
        self._predictor_factory = predictor_factory or DSPyPredictorFactory()
        self._max_summary_chars = max_summary_chars
        self._max_history_chars = max_history_chars

    def summarize(self, history_text: str) -> str:
        history = (history_text or "").strip()
        if not history:
            return ""
        history = history[-self._max_history_chars :]
        predictor = self._predictor_factory.create_predictor(_MemorySummarySignature)
        if predictor is None:
            return self._fallback(history)
        try:
            result = predictor(history_text=history)
            summary = (getattr(result, "memory_summary", "") or "").strip()
        except Exception as exc:  # pragma: no cover - runtime failure guard
            logger.warning("Memory summarizer failed: %s", exc)
            summary = ""
        if not summary:
            return self._fallback(history)
        return summary[: self._max_summary_chars]

    def _fallback(self, history: str) -> str:
        lines = history.strip().splitlines()
        if len(lines) <= 4:
            return history[-self._max_summary_chars :]
        last_lines = "\n".join(lines[-6:])
        return last_lines[-self._max_summary_chars :]


class RetrievalDecider:
    def __init__(
        self,
        *,
        predictor_factory: DSPyPredictorFactory | None = None,
        default_types: Sequence[str] | None = None,
    ) -> None:
        self._predictor_factory = predictor_factory or DSPyPredictorFactory()
        self._default_types = [entry for entry in (default_types or ["text", "header", "table", "image"]) if entry]

    def decide(self, question: str, memory_summary: str) -> RetrievalDecision:
        question = (question or "").strip()
        if not question:
            return RetrievalDecision(False, list(self._default_types))
        predictor = self._predictor_factory.create_predictor(_RetrievalDecisionSignature)
        if predictor is None:
            return self._fallback_decision(question)
        payload = None
        try:
            result = predictor(question=question, memory_summary=memory_summary)
            raw_json = (getattr(result, "decision_json", "") or "").strip()
            payload = json.loads(raw_json) if raw_json else None
        except Exception as exc:  # pragma: no cover - parse fallback
            logger.warning("RetrievalDecider failed, falling back to heuristics: %s", exc)
        if not isinstance(payload, dict):
            return self._fallback_decision(question)
        need_retrieve = bool(payload.get("need_retrieve"))
        elem_types = _normalize_types(payload.get("element_types"))
        if not elem_types:
            elem_types = list(self._default_types)
        return RetrievalDecision(need_retrieve, elem_types)

    def _fallback_decision(self, question: str) -> RetrievalDecision:
        lowered = question.lower()
        keywords = {"figure", "table", "dataset", "result", "explain", "how", "compare"}
        need_retrieve = any(word in lowered for word in keywords) or len(lowered) > 40
        elem_types = list(self._default_types)
        if any(keyword in lowered for keyword in {"figure", "image", "diagram"}):
            if "image" not in elem_types:
                elem_types.append("image")
        if any(keyword in lowered for keyword in {"table"}):
            if "table" not in elem_types:
                elem_types.append("table")
        return RetrievalDecision(need_retrieve, elem_types)


class QueryRewriter:
    def __init__(
        self,
        *,
        predictor_factory: DSPyPredictorFactory | None = None,
        max_length: int = 240,
    ) -> None:
        self._predictor_factory = predictor_factory or DSPyPredictorFactory()
        self._max_length = max_length

    def rewrite(self, question: str, memory_summary: str) -> str:
        question = (question or "").strip()
        if not question:
            return ""
        predictor = self._predictor_factory.create_predictor(_QueryRewriteSignature)
        if predictor is None:
            return self._fallback(question, memory_summary)
        try:
            result = predictor(question=question, memory_summary=memory_summary)
            rewritten = (getattr(result, "search_query", "") or "").strip()
        except Exception as exc:  # pragma: no cover - runtime guard
            logger.warning("QueryRewriter failed: %s", exc)
            rewritten = ""
        if not rewritten:
            return self._fallback(question, memory_summary)
        return rewritten[: self._max_length]

    def _fallback(self, question: str, memory_summary: str) -> str:
        summary_tokens = (memory_summary or "").split()
        prefix = " ".join(summary_tokens[:8])
        rewritten = f"{prefix} {question}".strip()
        if len(rewritten) > self._max_length:
            return rewritten[: self._max_length]
        return rewritten


class ImageQuestionGenerator:
    def __init__(
        self,
        *,
        predictor_factory: DSPyPredictorFactory | None = None,
        max_length: int = 400,
    ) -> None:
        self._predictor_factory = predictor_factory or DSPyPredictorFactory()
        self._max_length = max_length

    def generate(self, *, question: str, memory_summary: str, local_context: str) -> str:
        predictor = self._predictor_factory.create_predictor(_ImageQuestionSignature)
        if predictor is None:
            return self._fallback(question, local_context)
        try:
            result = predictor(
                question=question,
                memory_summary=memory_summary,
                local_context=local_context,
            )
            followup = (getattr(result, "image_question", "") or "").strip()
        except Exception as exc:  # pragma: no cover - runtime guard
            logger.warning("ImageQuestionGenerator failed: %s", exc)
            followup = ""
        if not followup:
            followup = self._fallback(question, local_context)
        return followup[: self._max_length]

    def _fallback(self, question: str, local_context: str) -> str:
        base = question.strip() or "Describe the figure."
        context = (local_context or "").strip()
        if context:
            return f"{base} Relate the answer to: {context[:200]}"
        return base


class AnswerComposer:
    def __init__(
        self,
        *,
        predictor_factory: DSPyPredictorFactory | None = None,
    ) -> None:
        self._predictor_factory = predictor_factory or DSPyPredictorFactory()

    def compose(
        self,
        *,
        question: str,
        memory_summary: str,
        text_evidences: Sequence[EvidenceText],
        image_evidences: Sequence[EvidenceText],
    ) -> str:
        payload = _format_evidence_prompt(text_evidences, image_evidences)
        predictor = self._predictor_factory.create_predictor(_AnswerComposerSignature)
        if predictor is None:
            return self._fallback_answer(question, text_evidences, image_evidences)
        try:
            result = predictor(
                question=question,
                memory_summary=memory_summary,
                evidence_context=payload,
            )
            answer = (getattr(result, "answer_text", "") or "").strip()
        except Exception as exc:  # pragma: no cover - runtime guard
            logger.warning("AnswerComposer failed: %s", exc)
            answer = ""
        if not answer:
            answer = self._fallback_answer(question, text_evidences, image_evidences)
        return answer

    @staticmethod
    def _fallback_answer(
        question: str,
        text_evidences: Sequence[EvidenceText],
        image_evidences: Sequence[EvidenceText],
    ) -> str:
        usable = list(text_evidences) + list(image_evidences)
        if not usable:
            return (
                "I do not have enough indexed evidence yet to answer this question reliably. "
                "Please try rephrasing the question after documents are parsed."
            )
        first = usable[0]
        snippet = first.text_content.strip()[:240]
        return f"{snippet}\n\n[Elem#{first.element_id}]"


def _normalize_types(value: object) -> list[str]:
    if isinstance(value, str):
        return [entry for entry in value.split(",") if entry]
    if isinstance(value, Iterable):
        normalized: list[str] = []
        for entry in value:
            if not entry:
                continue
            normalized.append(str(entry).strip())
        return normalized
    return []


def _format_evidence_prompt(
    text_evidences: Sequence[EvidenceText],
    image_evidences: Sequence[EvidenceText],
) -> str:
    if not text_evidences and not image_evidences:
        return "No external evidences. Answer using only prior knowledge."
    lines: list[str] = [
        "For each statement that references evidence you must cite `[Elem#<element_id>]`.",
        "If multiple evidences support the same statement, cite them together like `[Elem#<element_id1>, Elem#<element_id2>]`.",
        "Available textual evidences:",
    ]
    if not text_evidences:
        lines.append("- none")
    else:
        for idx, ev in enumerate(text_evidences, 1):
            lines.append(f"{idx}. {ev.as_prompt_entry()}")
    lines.append("Available image evidences (converted to text):")
    if not image_evidences:
        lines.append("- none")
    else:
        for idx, ev in enumerate(image_evidences, 1):
            lines.append(f"{idx}. {ev.as_prompt_entry()}")
    return "\n".join(lines)


if dspy is not None:

    class _MemorySummarySignature(dspy.Signature):  # type: ignore[misc]
        history_text = dspy.InputField(
            desc="Concise transcript of alternating [User]/[Assistant] utterances.",
        )
        memory_summary = dspy.OutputField(
            desc="Short bullets capturing important facts from history_text.",
        )

    class _RetrievalDecisionSignature(dspy.Signature):  # type: ignore[misc]
        question = dspy.InputField(desc="Current user question that may need retrieval.")
        memory_summary = dspy.InputField(desc="Summary of previous turns.")
        decision_json = dspy.OutputField(
            desc=(
                "Respond with JSON: {\"need_retrieve\": bool, "
                "\"element_types\": [\"text\",\"header\",\"image\",\"table\",\"equation\"]}"
            ),
        )

    class _QueryRewriteSignature(dspy.Signature):  # type: ignore[misc]
        question = dspy.InputField(desc="Original user wording.")
        memory_summary = dspy.InputField(desc="Helpful prior discussion summary.")
        search_query = dspy.OutputField(
            desc="Short query optimized for dense retrieval over parsed paper elements.",
        )

    class _AnswerComposerSignature(dspy.Signature):  # type: ignore[misc]
        question = dspy.InputField(desc="Question to address.")
        memory_summary = dspy.InputField(desc="Summarized chat context.")
        evidence_context = dspy.InputField(
            desc=(
                "List of evidences. Every claim that uses an evidence MUST cite it as [Elem#<element_id>]. "
                "If multiple evidences support one claim, cite them together like [Elem#1046, Elem#1346]. "
                "Never invent new identifiers."
            ),
        )
        answer_text = dspy.OutputField(
            desc=(
                "Well-structured answer. Cite sources inline via [Elem#<element_id>] "
                "or combined like [Elem#1046, Elem#1346] when multiple apply."
            ),
        )

    class _ImageQuestionSignature(dspy.Signature):  # type: ignore[misc]
        question = dspy.InputField(desc="Original user request.")
        memory_summary = dspy.InputField(desc="Optional prior turns summary.")
        local_context = dspy.InputField(
            desc="Caption plus nearby text describing the image element.",
        )
        image_question = dspy.OutputField(
            desc="Short follow-up question to ask a vision model about the image.",
        )

else:  # pragma: no cover - fallback definitions for static analyzers

    class _MemorySummarySignature:  # type: ignore[too-many-ancestors]
        pass

    class _RetrievalDecisionSignature:
        pass

    class _QueryRewriteSignature:
        pass

    class _AnswerComposerSignature:
        pass

    class _ImageQuestionSignature:
        pass


__all__ = [
    "DSPyPredictorFactory",
    "MemorySummarizer",
    "RetrievalDecider",
    "RetrievalDecision",
    "QueryRewriter",
    "AnswerComposer",
    "ImageQuestionGenerator",
]
