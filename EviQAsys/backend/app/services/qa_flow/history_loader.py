from __future__ import annotations

from typing import Iterable, Sequence


def format_history_text(
    turns: Sequence[dict[str, object]],
    *,
    max_turns: int = 6,
    max_chars: int = 6000,
) -> str:
    """Render chat history into a trimmed text transcript for memory summarization."""

    if not turns:
        return ""
    relevant = list(turns)[-max_turns:]
    lines: list[str] = []
    for turn in relevant:
        question = (turn.get("user_question") or "").strip() if isinstance(turn, dict) else ""
        answer = (turn.get("llm_answer_text") or "").strip() if isinstance(turn, dict) else ""
        if question:
            lines.append(f"[User] {question}")
        if answer:
            lines.append(f"[Assistant] {answer}")
    transcript = "\n".join(line for line in lines if line).strip()
    if not transcript:
        return ""
    if len(transcript) > max_chars:
        transcript = transcript[-max_chars:]
    return transcript


def select_recent_turns(
    turns: Sequence[dict[str, object]],
    *,
    max_turns: int,
) -> list[dict[str, object]]:
    """Return the most recent turns respecting existing ordering."""
    if max_turns <= 0 or not turns:
        return []
    return list(turns)[-max_turns:]


__all__ = ["format_history_text", "select_recent_turns"]
