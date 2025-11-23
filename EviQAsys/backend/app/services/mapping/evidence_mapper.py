from __future__ import annotations

import re
from typing import Iterable, Mapping, Sequence


# Matches Elem#<id> tokens even when multiple are inside one [...] block.
_ELEM_TAG_RE = re.compile(r"Elem#(?P<id>\d+)")


def build_evidence_no_mapping(history_elements: Iterable[int]) -> dict[int, int]:
    """Build a mapping element_id -> evidence_no by first appearance order.

    history_elements is a sequence of element_ids ordered by their first appearance
    in the chat history. The returned mapping assigns 1-based consecutive numbers.
    """
    mapping: dict[int, int] = {}
    next_no = 1
    for elem_id in history_elements:
        if elem_id not in mapping:
            mapping[elem_id] = next_no
            next_no += 1
    return mapping


def replace_elem_tags_with_evidence(answer_text: str, mapping: Mapping[int, int]) -> str:
    """Replace Elem#<id> tokens with Evidence#<no> according to mapping.

    Works when multiple element ids are inside the same bracket block, e.g.
    `[Elem#1, Elem#2]` becomes `[Evidence#1, Evidence#2]`. Unmapped element_ids
    are left as-is to aid debugging.
    """

    def _sub(m: re.Match[str]) -> str:
        elem_id = int(m.group("id"))
        evidence_no = mapping.get(elem_id)
        return f"Evidence#{evidence_no}" if evidence_no is not None else m.group(0)

    return _ELEM_TAG_RE.sub(_sub, answer_text)


def extract_element_ids_from_answer(answer_text: str) -> list[int]:
    """Return ordered element ids based on Elem#<id> tags in the answer."""
    ids: list[int] = []
    seen: set[int] = set()
    for match in _ELEM_TAG_RE.finditer(answer_text or ""):
        elem_id = int(match.group("id"))
        if elem_id not in seen:
            seen.add(elem_id)
            ids.append(elem_id)
    return ids


def collect_element_ids_from_turns(
    turns: Sequence[Mapping[str, object]],
    *,
    order_key: str = "order",
) -> list[int]:
    """Collect element ids from historical turns ordered by turn sequence."""
    sorted_turns = sorted(
        turns,
        key=lambda row: int(row.get(order_key) or 0),
    )
    sequence: list[int] = []
    for turn in sorted_turns:
        answer = (
            str(turn.get("llm_answer_text") or turn.get("answer_text") or "")
            if isinstance(turn, Mapping)
            else ""
        )
        sequence.extend(extract_element_ids_from_answer(answer))
    return sequence


def build_evidences_payload(
    *,
    mapping: Mapping[int, int],
    elements: Mapping[int, Mapping[str, object]],
    used_element_ids: Sequence[int],
    snippet_max_chars: int = 280,
) -> list[dict[str, object]]:
    """Assemble API payload entries for the elements referenced in the latest turn."""
    payloads: list[dict[str, object]] = []
    added: set[int] = set()
    for elem_id in used_element_ids:
        if elem_id in added:
            continue
        element = elements.get(elem_id)
        if not element:
            continue
        snippet = _select_snippet(element, snippet_max_chars)
        payloads.append(
            {
                "element_id": elem_id,
                "evidence_no": mapping.get(elem_id),
                "document_id": element.get("doc_id") or element.get("document_id"),
                "page_index": element.get("page_no"),
                "bbox": element.get("bbox"),
                "elem_type": element.get("elem_type"),
                "snippet": snippet,
                "text_content": (element.get("text_content") or "").strip() or None,
                "title": element.get("level_nav"),
            },
        )
        added.add(elem_id)
    return payloads


def _select_snippet(element: Mapping[str, object], limit: int) -> str | None:
    text_fields = [
        element.get("text_content"),
        element.get("text_caption"),
    ]
    for field in text_fields:
        snippet = str(field or "").strip()
        if snippet:
            if len(snippet) > limit:
                return f"{snippet[:limit]}..."
            return snippet
    return None


__all__ = [
    "build_evidence_no_mapping",
    "replace_elem_tags_with_evidence",
    "extract_element_ids_from_answer",
    "collect_element_ids_from_turns",
    "build_evidences_payload",
]
