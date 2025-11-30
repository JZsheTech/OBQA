from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Iterable

ROOT_HEADER = "root"
ROOT_LEVEL_NAV = "root"
HEADER_NUMBER_PATTERN = re.compile(
    r"""
    ^\s*(
        (?:(?:Appendix|APPENDIX)\s+[A-Za-z0-9]+(?:\.(?:[A-Za-z0-9]+))*)
        |
        (?:\d+(?:\.\d+)*)
        |
        (?:[A-Za-z]\.\s*\d+(?:\.\d+)*)
    )
    """,
    re.VERBOSE | re.IGNORECASE,
)


@dataclass(slots=True)
class HeaderContext:
    level: int
    name: str
    nav_token: str
    order: int


def preprocess_headers(content_list: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    """Augment MinerU content list entries with header hierarchy metadata.

    MinerU marks page headers with ``type == "header"``; these are noise and should
    be treated the same as ``discarded`` entries so they do not reach the elements
    or chunks tables.
    """
    items: list[dict[str, Any]] = []
    for entry in list(content_list):
        if not isinstance(entry, dict):
            continue
        elem_type = (entry.get("type") or "").lower()
        if elem_type in {"discarded", "header"}:
            continue
        items.append(entry)
    processed: list[dict[str, Any]] = []
    header_stack: list[HeaderContext] = []
    order_end_map: dict[int, int] = {}
    last_level_nav: str | None = None
    seen_header = False

    for order, raw in enumerate(items):
        elem_type = (raw.get("type") or "").lower()
        enriched = dict(raw)
        enriched["order"] = order
        is_header = elem_type == "text" and raw.get("text_level") is not None
        if is_header:
            level = max(1, _infer_level(raw))
            if level > len(header_stack) + 1:
                _close_headers_until(header_stack, order_end_map, 1, order - 1, drain=True)
                header_stack.clear()
                level = 1
            _close_headers_until(header_stack, order_end_map, level, order - 1)
            header_name = _clean_text(raw.get("text"))
            nav_token = _build_nav_token(header_name)
            context = HeaderContext(level=level, name=header_name, nav_token=nav_token, order=order)
            header_stack.append(context)
            enriched["elem_type"] = "header"
            enriched["header_level"] = level
            enriched["header_name"] = header_name
        else:
            elem_type = _map_elem_type(elem_type, raw)
            enriched["elem_type"] = elem_type
            context = header_stack[-1] if header_stack else None
            enriched["header_level"] = context.level if context else None
            enriched["header_name"] = context.name if context else ROOT_HEADER

        nav_tokens = [ctx.nav_token for ctx in header_stack]
        if enriched["elem_type"] == "header":
            nav_tokens = nav_tokens[:]  # ensure copy
        if nav_tokens:
            level_nav = " > ".join(nav_tokens)
            last_level_nav = level_nav
            seen_header = True
        else:
            level_nav = last_level_nav if seen_header and last_level_nav else ROOT_LEVEL_NAV
        enriched["level_nav"] = level_nav
        enriched.setdefault("header_name", ROOT_HEADER)
        processed.append(enriched)

    _close_headers_until(header_stack, order_end_map, 1, len(items) - 1, drain=True)

    for item in processed:
        if item.get("elem_type") == "header":
            order = item["order"]
            item["order_start"] = order
            item["order_end"] = order_end_map.get(order, order)

    return processed


def _close_headers_until(
    stack: list[HeaderContext],
    order_end_map: dict[int, int],
    target_level: int,
    end_index: int,
    *,
    drain: bool = False,
) -> None:
    while stack and (drain or stack[-1].level >= target_level):
        context = stack.pop()
        order_end_map[context.order] = max(end_index, context.order)
        if not drain and (not stack or stack[-1].level < target_level):
            break


def _infer_level(raw: dict[str, Any]) -> int:
    text = _clean_text(raw.get("text"))
    number = HEADER_NUMBER_PATTERN.match(text)
    number_level: int | None = None
    if number:
        token = number.group(1)
        number_level = token.count(".") + 1

    text_level = raw.get("text_level")
    if isinstance(text_level, str) and text_level.isdigit():
        text_level = int(text_level)
    elif not isinstance(text_level, int):
        text_level = None

    if number_level is not None and text_level is not None:
        return max(number_level, text_level)
    if number_level is not None:
        return number_level
    if text_level is not None:
        return text_level
    return 1


def _map_elem_type(elem_type: str, raw: dict[str, Any]) -> str:
    if elem_type in {"text", "header", "image", "table", "equation"}:
        return "header" if elem_type == "header" else elem_type
    if elem_type in {"figure"}:
        return "image"
    if raw.get("text_level") is not None:
        return "header"
    return "text"


def _clean_text(value: Any) -> str:
    if not value:
        return ROOT_HEADER
    text = str(value).strip()
    return re.sub(r"\s+", " ", text)


def _build_nav_token(text: str) -> str:
    text = _clean_text(text)
    if text == ROOT_HEADER:
        return ROOT_HEADER
    number_match = HEADER_NUMBER_PATTERN.match(text)
    if number_match:
        token = _normalize_nav_number(number_match.group(1))
        remainder = text[number_match.end(1) :].strip(" .:-")
        if remainder:
            return f"{token} {remainder}"
        return token
    return text or ROOT_HEADER


def _normalize_nav_number(token: str) -> str:
    token = token.strip()
    token = re.sub(r"\s+", " ", token)
    token = re.sub(r"\.\s+", ".", token)
    return token
