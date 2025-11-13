from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Mapping, Sequence

import requests

from ...env_setting import EmbeddingSettings, VECTOR_DIM, get_embedding_settings

logger = logging.getLogger(__name__)


class EmbeddingServiceError(RuntimeError):
    """Raised when embedding requests fail."""


class EmbeddingDimensionMismatchError(EmbeddingServiceError):
    """Raised when the returned embedding dimension differs from VECTOR_DIM."""


@dataclass(slots=True)
class EmbeddingResponse:
    embedding: list[float]
    model: str | None = None
    usage: Mapping[str, Any] | None = None


class EmbeddingService:
    """Thin wrapper around OpenAI-compatible `/v1/embeddings` endpoints."""

    def __init__(
        self,
        *,
        settings: EmbeddingSettings | None = None,
        session: requests.Session | None = None,
        vector_dim: int | None = None,
    ) -> None:
        self._settings = settings or get_embedding_settings()
        self._session = session or requests.Session()
        self._vector_dim = vector_dim or VECTOR_DIM

    def embed_message(self, content_blocks: Sequence[Mapping[str, Any]]) -> list[float]:
        if not content_blocks:
            raise ValueError("content_blocks must include at least one block.")
        payload = self._build_payload(list(content_blocks))
        response = self._send_request(payload)
        self._ensure_dimension(response.embedding)
        return response.embedding

    def embed_text(self, text: str) -> list[float]:
        text = (text or "").strip()
        if not text:
            raise ValueError("text must be non-empty for embedding.")
        return self.embed_message([{"type": "text", "text": text}])

    def embed_text_image(self, text: str, image_b64: str | None) -> list[float]:
        blocks: list[dict[str, Any]] = []
        text = (text or "").strip()
        if text:
            blocks.append({"type": "text", "text": text})
        if image_b64:
            blocks.append({"type": "image_url", "image_url": {"url": self._ensure_data_uri(image_b64)}})
        if not blocks:
            raise ValueError("Neither text nor image payload provided.")
        return self.embed_message(blocks)

    def batch_embed_elements(self, elements: Sequence[Mapping[str, Any]]) -> dict[int, list[float]]:
        embeddings: dict[int, list[float]] = {}
        for element in elements:
            element_id = element.get("id")
            if element_id is None:
                raise ValueError("Each element must include an 'id' field.")
            content_blocks = self._build_blocks_from_element(element)
            logger.debug("Embedding element id=%s elem_type=%s", element_id, element.get("elem_type"))
            vector = self.embed_message(content_blocks)
            embeddings[int(element_id)] = vector
        return embeddings

    def _build_payload(self, content_blocks: list[Mapping[str, Any]]) -> dict[str, Any]:
        return {
            "model": self._settings.model,
            "messages": [
                {
                    "role": "user",
                    "content": content_blocks,
                },
            ],
        }

    def _build_blocks_from_element(self, element: Mapping[str, Any]) -> list[dict[str, Any]]:
        elem_type = (element.get("elem_type") or "").lower()
        text_chunks: list[str] = []
        for field in ("text_content", "text_caption"):
            value = (element.get(field) or "").strip()
            if value:
                text_chunks.append(value)
        blocks: list[dict[str, Any]] = []
        if text_chunks:
            blocks.append({"type": "text", "text": " ".join(text_chunks)})
        image_payload = element.get("image_base64")
        if elem_type in {"image", "table", "equation"} and image_payload:
            blocks.append(
                {
                    "type": "image_url",
                    "image_url": {"url": self._ensure_data_uri(str(image_payload))},
                },
            )
        if not blocks:
            raise ValueError(f"Element {element.get('id')} has no content to embed.")
        return blocks

    def _send_request(self, payload: dict[str, Any]) -> EmbeddingResponse:
        headers = self._build_headers()
        max_attempts = max(1, self._settings.max_retries + 1)
        last_exc: Exception | None = None
        for attempt in range(max_attempts):
            try:
                response = self._session.post(
                    self._settings.endpoint,
                    json=payload,
                    timeout=self._settings.timeout_s,
                    headers=headers,
                )
                if response.status_code >= 400:
                    logger.warning(
                        "Embedding request failed (%s): %s",
                        response.status_code,
                        response.text[:256],
                    )
                response.raise_for_status()
                data = response.json()
                embedding = data["data"][0]["embedding"]
                model = data["data"][0].get("model") or data.get("model")
                usage = data.get("usage")
                return EmbeddingResponse(embedding=list(embedding), model=model, usage=usage)
            except Exception as exc:
                last_exc = exc
                if attempt < max_attempts - 1:
                    logger.info("Retrying embedding request (%s/%s)...", attempt + 1, max_attempts - 1)
                    continue
                break
        assert last_exc is not None
        raise EmbeddingServiceError("Embedding request failed.") from last_exc

    def _ensure_dimension(self, vector: Sequence[float]) -> None:
        if len(vector) != self._vector_dim:
            message = (
                f"Embedding dimension {len(vector)} does not match configured VECTOR_DIM={self._vector_dim}."
            )
            raise EmbeddingDimensionMismatchError(message)

    def _build_headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self._settings.api_key:
            headers[self._settings.api_key_header] = self._settings.api_key
        return headers

    @staticmethod
    def _ensure_data_uri(image_b64: str) -> str:
        data = image_b64.strip()
        if data.startswith("data:"):
            return data
        return f"data:image/png;base64,{data}"


__all__ = [
    "EmbeddingService",
    "EmbeddingServiceError",
    "EmbeddingDimensionMismatchError",
]
