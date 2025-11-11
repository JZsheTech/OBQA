from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT_HEADER = "root"
ROOT_LEVEL_NAV = "root"


def normalize_element(item: dict[str, Any], *, images: dict[str, str]) -> dict[str, Any]:
    elem_type = (item.get("elem_type") or "text").lower()
    header_name = (item.get("header_name") or ROOT_HEADER).strip()
    level_nav = (item.get("level_nav") or ROOT_LEVEL_NAV).strip()
    prefix = f"[{level_nav}] [{header_name}]"
    text_content = _build_text_content(elem_type, prefix, item)
    text_caption = _extract_caption(elem_type, item)
    bbox_json = json.dumps(item.get("bbox") or item.get("bbox_json") or [])
    page_no = _resolve_page_no(item)
    image_base64 = _resolve_image_blob(elem_type, item, images)
    order_start = _as_order_str(item.get("order_start"))
    order_end = _as_order_str(item.get("order_end"))
    return {
        "elem_type": elem_type,
        "header_name": header_name,
        "header_level": item.get("header_level"),
        "level_nav": level_nav,
        "text_content": text_content,
        "text_caption": text_caption,
        "image_base64": image_base64,
        "bbox_json": bbox_json,
        "page_no": page_no,
        "order": item.get("order"),
        "order_start": order_start,
        "order_end": order_end,
    }


def strip_data_uri_prefix(data: str | None) -> str | None:
    if not data:
        return data
    if data.startswith("data:") and "," in data:
        return data.split(",", 1)[1]
    return data


def _build_text_content(elem_type: str, prefix: str, item: dict[str, Any]) -> str:
    body = ""
    if elem_type == "text":
        body = item.get("text") or ""
    elif elem_type == "header":
        body = item.get("section_summary") or ""
    elif elem_type == "image":
        body = _extract_caption(elem_type, item) or "[figure]"
    elif elem_type == "table":
        caption = _extract_caption(elem_type, item)
        table_body = item.get("table_body") or ""
        body = " ".join(filter(None, [caption, table_body]))
    elif elem_type == "equation":
        body = item.get("text") or item.get("latex") or ""
    combined = " ".join(part for part in [prefix.strip(), body.strip()] if part)
    return combined.strip()


def _extract_caption(elem_type: str, item: dict[str, Any]) -> str | None:
    if elem_type == "image":
        captions = item.get("image_caption") or item.get("caption") or []
        if isinstance(captions, list):
            captions = " ".join(entry.strip() for entry in captions if entry)
        return captions or None
    if elem_type == "table":
        captions = item.get("table_caption") or []
        if isinstance(captions, list):
            captions = " ".join(entry.strip() for entry in captions if entry)
        return captions or None
    return None


def _resolve_page_no(item: dict[str, Any]) -> int | None:
    if item.get("page_no") is not None:
        try:
            return int(item["page_no"])
        except (TypeError, ValueError):
            return None
    page_idx = item.get("page_idx")
    if page_idx is None:
        return None
    try:
        return int(page_idx) + 1
    except (TypeError, ValueError):
        return None


def _resolve_image_blob(elem_type: str, item: dict[str, Any], images: dict[str, str]) -> str | None:
    if elem_type not in {"image", "table", "equation"}:
        return None
    img_path = item.get("img_path")
    if not img_path:
        return None
    key = Path(str(img_path)).name
    data = images.get(key)
    if not data:
        raise ValueError(f"Missing image payload for key {key}")
    return strip_data_uri_prefix(data)


def _as_order_str(value: Any) -> str | None:
    if value is None:
        return None
    return str(value)


__all__ = ["normalize_element", "strip_data_uri_prefix"]
