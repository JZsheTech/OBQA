from __future__ import annotations

import logging
from typing import Any

import requests

from ...env_setting import VisionVQASettings, get_vision_vqa_settings
from ...repositories import ElementsRepository

logger = logging.getLogger(__name__)


class VisionVQAError(RuntimeError):
    """Raised when visual question answering calls fail."""


class VisionVQAClient:
    """Minimal OpenAI-compatible visual question answering helper."""

    def __init__(
        self,
        *,
        elements_repo: ElementsRepository | None = None,
        settings: VisionVQASettings | None = None,
        session: requests.Session | None = None,
    ) -> None:
        self._elements_repo = elements_repo or ElementsRepository()
        self._settings = settings or get_vision_vqa_settings()
        self._session = session or requests.Session()

    def summarize(
        self,
        *,
        element_id: int,
        derived_question: str,
        local_context: str | None = None,
    ) -> str:
        element = self._elements_repo.get_by_id(element_id)
        if not element:
            raise VisionVQAError(f"Element {element_id} not found.")
        image_payload = (element.get("image_base64") or "").strip()
        if not image_payload:
            raise VisionVQAError(f"Element {element_id} does not contain image data.")
        caption = element.get("text_caption") or ""
        prompt = self._build_prompt(derived_question, caption, local_context or "")
        payload = {
            "model": self._settings.model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You describe figures and tables for paper reading. "
                        "Return 2-3 sentences and avoid markdown."
                    ),
                },
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {"url": self._ensure_data_uri(image_payload)},
                        },
                    ],
                },
            ],
            "max_tokens": self._settings.max_tokens,
        }
        headers = {"Content-Type": "application/json"}
        if self._settings.api_key:
            headers[self._settings.api_key_header] = self._settings.api_key
        try:
            response = self._session.post(
                self._settings.endpoint,
                json=payload,
                headers=headers,
                timeout=self._settings.timeout_s,
            )
            response.raise_for_status()
            data = response.json()
        except Exception as exc:
            raise VisionVQAError("Vision VQA request failed.") from exc
        summary = self._extract_text(data)
        if not summary:
            raise VisionVQAError("Vision VQA returned empty response.")
        return summary.strip()

    @staticmethod
    def _build_prompt(question: str, caption: str, context: str) -> str:
        parts = [f"Question: {question.strip() or 'Describe this figure.'}"]
        if caption:
            parts.append(f"Caption: {caption.strip()}")
        if context:
            parts.append(f"Nearby text: {context.strip()}")
        return "\n".join(parts)

    @staticmethod
    def _ensure_data_uri(image_b64: str) -> str:
        data = image_b64.strip()
        if data.startswith("data:"):
            return data
        return f"data:image/png;base64,{data}"

    @staticmethod
    def _extract_text(payload: Any) -> str:
        if isinstance(payload, dict):
            choices = payload.get("choices")
            if isinstance(choices, list) and choices:
                message = choices[0].get("message")
                if isinstance(message, dict):
                    content = message.get("content")
                    if isinstance(content, list):
                        texts = [item.get("text") for item in content if isinstance(item, dict)]
                        joined = "\n".join(entry for entry in texts if entry)
                        if joined:
                            return joined
                    if isinstance(content, str):
                        return content
            result = payload.get("result")
            if isinstance(result, str):
                return result
        if isinstance(payload, str):
            return payload
        logger.debug("Vision VQA payload unrecognized: %s", payload)
        return ""


__all__ = ["VisionVQAClient", "VisionVQAError"]
