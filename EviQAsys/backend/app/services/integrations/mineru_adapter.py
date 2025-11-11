from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import requests

from ...env_setting import MinerUSettings, get_mineru_settings

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class MinerUParseResult:
    md_text: str | None
    content_list: list[dict[str, Any]]
    images: dict[str, str]


class MinerUAdapter:
    """HTTP adapter that sends PDF files to a local MinerU service."""

    def __init__(self, settings: MinerUSettings | None = None) -> None:
        self._settings = settings or get_mineru_settings()
        if self._settings.mode.lower() != "http":
            raise ValueError("Only HTTP MinerU mode is supported in M2.")

    def parse(self, file_path: str | Path, *, file_name: str | None = None) -> MinerUParseResult:
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"PDF not found: {path}")
        payload = self._build_payload()
        pdf_name = file_name or path.name
        logger.info("Submitting PDF %s to MinerU at %s", pdf_name, self._settings.endpoint)
        with path.open("rb") as stream:
            files = {"files": (pdf_name, stream, "application/pdf")}
            response = requests.post(
                self._settings.endpoint,
                data=payload,
                files=files,
                timeout=self._settings.timeout_s,
            )
        try:
            response.raise_for_status()
        except requests.HTTPError as exc:  # pragma: no cover - network failure path
            body_preview = response.text[:500]
            logger.error("MinerU request failed (%s): %s", exc, body_preview)
            raise RuntimeError("MinerU service returned an error.") from exc
        data = response.json()
        result_key = path.stem
        results = data.get("results") or {}
        if result_key not in results:
            raise RuntimeError(f"MinerU response missing key for {result_key}")
        parsed = results[result_key]
        content_list_raw = parsed.get("content_list")
        content_list = self._normalize_content_list(content_list_raw)
        md_text = parsed.get("md_content")
        images: dict[str, str] = parsed.get("images") or {}
        logger.info("MinerU returned %d elements for %s", len(content_list), pdf_name)
        return MinerUParseResult(md_text=md_text, content_list=content_list, images=images)

    def _build_payload(self) -> dict[str, Any]:
        lang_list = list(self._settings.lang_list) or ["en"]
        return {
            "output_dir": None,
            "lang_list": lang_list,
            "backend": self._settings.backend,
            "parse_method": "auto",
            "formula_enable": True,
            "table_enable": True,
            "return_md": True,
            "return_middle_json": False,
            "return_model_output": False,
            "return_content_list": True,
            "return_images": True,
            "response_format_zip": False,
            "start_page_id": 0,
            "end_page_id": 99999,
        }

    @staticmethod
    def _normalize_content_list(raw: Any) -> list[dict[str, Any]]:
        if raw is None:
            return []
        if isinstance(raw, str):
            try:
                return json.loads(raw)
            except json.JSONDecodeError as exc:
                raise ValueError("Invalid MinerU content_list JSON.") from exc
        if isinstance(raw, list):
            return raw
        raise TypeError("content_list must be a JSON string or a list.")


__all__ = ["MinerUAdapter", "MinerUParseResult"]
