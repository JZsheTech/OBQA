from __future__ import annotations

import re
from typing import Iterable, Mapping


_ELEM_TAG_RE = re.compile(r"\[Elem#(?P<id>\d+)\]")


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
    """Replace [Elem#<id>] tags with [Evidence#<no>] according to mapping.

    Unmapped element_ids are left as-is, to aid debugging.
    """

    def _sub(m: re.Match[str]) -> str:
        elem_id = int(m.group("id"))
        evidence_no = mapping.get(elem_id)
        return f"[Evidence#{evidence_no}]" if evidence_no is not None else m.group(0)

    return _ELEM_TAG_RE.sub(_sub, answer_text)

