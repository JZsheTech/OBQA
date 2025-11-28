from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, Literal, Sequence
from xml.etree import ElementTree as ET

import requests

logger = logging.getLogger(__name__)

SortBy = Literal["relevance", "submittedDate", "lastUpdatedDate"]
SortOrder = Literal["ascending", "descending"]
DateMode = Literal["submitted", "updated"]

ARXIV_API_URL = "https://export.arxiv.org/api/query"
USER_AGENT = "EviQAsys-Arxiv/0.1"


@dataclass(slots=True)
class ArxivSearchParams:
    all_terms: str | None = None
    title: str | None = None
    abstract: str | None = None
    author: str | None = None
    categories: Sequence[str] | None = None
    date_mode: DateMode | None = None
    date_from: date | None = None
    date_to: date | None = None
    sort_by: SortBy = "relevance"
    sort_order: SortOrder = "descending"
    max_results: int = 20
    id_list: Sequence[str] | None = None


def search_arxiv(params: ArxivSearchParams) -> list[dict[str, Any]]:
    max_results = min(max(params.max_results, 1), 50)
    query = build_search_query(params)
    payload = {
        "search_query": query,
        "start": 0,
        "max_results": max_results,
        "sortBy": params.sort_by,
        "sortOrder": params.sort_order,
    }
    if params.id_list:
        payload["id_list"] = ",".join(params.id_list)
    headers = {"User-Agent": USER_AGENT}
    try:
        response = requests.get(ARXIV_API_URL, params=payload, headers=headers, timeout=(5, 20))
        response.raise_for_status()
    except Exception as exc:
        logger.exception("Failed to query arXiv API")
        raise RuntimeError("arXiv API request failed") from exc
    try:
        return _parse_feed(response.text)
    except Exception as exc:  # noqa: BLE001 - defensive parse guard
        logger.exception("Failed to parse arXiv response feed")
        raise RuntimeError("Failed to parse arXiv API response") from exc


def build_search_query(params: ArxivSearchParams) -> str:
    parts: list[str] = []
    if params.all_terms:
        parts.append(f"all:{params.all_terms}")
    if params.title:
        parts.append(f"ti:{params.title}")
    if params.abstract:
        parts.append(f"abs:{params.abstract}")
    if params.author:
        parts.append(f"au:{params.author}")
    if params.categories:
        cat_expr = " OR ".join(f"cat:{category}" for category in params.categories if category)
        if cat_expr:
            parts.append(f"({cat_expr})")
    if params.date_mode and (params.date_from or params.date_to):
        field = "submittedDate" if params.date_mode == "submitted" else "lastUpdatedDate"
        start = _format_date_for_range(params.date_from or date(1990, 1, 1), start=True)
        end = _format_date_for_range(params.date_to or date.today(), start=False)
        parts.append(f"{field}:[{start} TO {end}]")
    if not parts:
        return "all:electron"
    return " AND ".join(parts)


def _parse_feed(xml_text: str) -> list[dict[str, Any]]:
    ns = {
        "atom": "http://www.w3.org/2005/Atom",
        "arxiv": "http://arxiv.org/schemas/atom",
    }
    root = ET.fromstring(xml_text)
    entries = []
    for entry in root.findall("atom:entry", ns):
        entry_id = _extract_text(entry, "id", ns) or ""
        arxiv_id, version = _parse_arxiv_id(entry_id)
        authors = [
            node.text.strip()
            for node in entry.findall("atom:author/atom:name", ns)
            if node.text and node.text.strip()
        ]
        categories = [
            node.attrib.get("term")
            for node in entry.findall("atom:category", ns)
            if node.attrib.get("term")
        ]
        primary_category = None
        primary_node = entry.find("arxiv:primary_category", ns)
        if primary_node is not None:
            primary_category = primary_node.attrib.get("term")
        abs_url = _extract_abs_url(entry, ns) or entry_id
        pdf_url = _extract_pdf_url(entry, ns)
        arxiv_id, version = _derive_arxiv_id(entry_id, abs_url, pdf_url)
        if abs_url is None and arxiv_id:
            abs_url = f"https://arxiv.org/abs/{arxiv_id}{version or ''}"
        if pdf_url is None and arxiv_id:
            pdf_url = f"https://arxiv.org/pdf/{arxiv_id}{version or ''}"
        entries.append(
            {
                "arxiv_id": arxiv_id,
                "version": version,
                "title": _clean_text(_extract_text(entry, "title", ns)) or "",
                "summary": _clean_text(_extract_text(entry, "summary", ns)),
                "authors": authors,
                "primary_category": primary_category,
                "categories": categories,
                "pdf_url": pdf_url,
                "abs_url": abs_url or pdf_url,
                "doi": _extract_text(entry, "doi", ns),
                "journal_ref": _extract_text(entry, "journal_ref", ns),
                "published": _parse_datetime(_extract_text(entry, "published", ns)),
                "updated": _parse_datetime(_extract_text(entry, "updated", ns)),
            },
        )
    return entries


def _extract_text(entry: ET.Element, tag: str, ns: dict[str, str]) -> str | None:
    node = entry.find(f"atom:{tag}", ns) or entry.find(f"arxiv:{tag}", ns) or entry.find(tag)
    if node is None or node.text is None:
        for child in entry.iter():
            if child.tag.split("}", 1)[-1] == tag and child.text:
                return child.text.strip()
        return None
    return node.text.strip()


def _extract_abs_url(entry: ET.Element, ns: dict[str, str]) -> str | None:
    for link in entry.findall("atom:link", ns):
        href = link.attrib.get("href")
        if not href:
            continue
        rel = link.attrib.get("rel")
        link_type = link.attrib.get("type", "")
        if rel in (None, "alternate") and (not link_type or "html" in link_type):
            return href
    return _extract_text(entry, "id", ns)


def _extract_pdf_url(entry: ET.Element, ns: dict[str, str]) -> str | None:
    for link in entry.findall("atom:link", ns):
        href = link.attrib.get("href")
        if not href:
            continue
        if link.attrib.get("type") == "application/pdf":
            return href
        if link.attrib.get("title") == "pdf":
            return href
    return None


def _format_date_for_range(d: date, *, start: bool) -> str:
    stamp = d.strftime("%Y%m%d")
    return stamp + ("000000" if start else "235959")


def _parse_datetime(raw: str | None) -> datetime | None:
    if not raw:
        return None
    normalized = raw.strip()
    if normalized.endswith("Z"):
        normalized = normalized.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(normalized)
    except ValueError:
        return None


def _derive_arxiv_id(entry_id: str | None, abs_url: str | None, pdf_url: str | None) -> tuple[str, str | None]:
    for candidate in (entry_id, abs_url, pdf_url):
        if not candidate:
            continue
        arxiv_id, version = _parse_arxiv_id(candidate)
        if arxiv_id:
            return arxiv_id, version
    return "", None


def _parse_arxiv_id(entry_id: str) -> tuple[str, str | None]:
    candidate = entry_id.rsplit("/", 1)[-1] if entry_id else ""
    match = re.match(r"(?P<id>.+?)(?:v(?P<version>\d+))?$", candidate)
    if not match:
        return candidate, None
    base_id = match.group("id") or candidate
    version = match.group("version")
    version_label = f"v{version}" if version else None
    return base_id, version_label


def _clean_text(value: str | None) -> str | None:
    if value is None:
        return None
    return re.sub(r"\s+", " ", value).strip()


__all__ = ["ArxivSearchParams", "search_arxiv", "build_search_query"]
