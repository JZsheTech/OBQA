from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache


def _get_env(name: str, default: str) -> str:
    value = os.getenv(name)
    if value is None or value == "":
        return default
    return value


def _get_int_env(name: str, default: int) -> int:
    raw_value = os.getenv(name)
    if raw_value is None or raw_value == "":
        return default
    try:
        return int(raw_value)
    except ValueError as exc:  # pragma: no cover - defensive guard rails
        raise ValueError(f"Invalid integer for {name}: {raw_value}") from exc


def _get_float_env(name: str, default: float) -> float:
    raw_value = os.getenv(name)
    if raw_value is None or raw_value == "":
        return default
    try:
        return float(raw_value)
    except ValueError as exc:  # pragma: no cover - defensive guard rails
        raise ValueError(f"Invalid float for {name}: {raw_value}") from exc


@dataclass(frozen=True)
class OceanBaseSettings:
    host: str = _get_env("OB_HOST", "127.0.0.1")
    port: int = _get_int_env("OB_PORT", 2881)
    user: str = _get_env("OB_USER", "paperQA@test")
    password: str = _get_env("OB_PASSWORD", "12345678")
    default_database: str = _get_env("OB_DEFAULT_DATABASE", "obqa_dev")
    connect_timeout: int = _get_int_env("DATABASE_CONNECT_TIMEOUT", 10)


DB_CHARSET: str = _get_env("DB_CHARSET", "utf8mb4")
VECTOR_DIM: int = _get_int_env("VECTOR_DIM", 2048)
INGEST_BATCH_SIZE: int = _get_int_env("BATCH_SIZE", 32)
ELEMENT_CONTEXT_OVERLAP: int = _get_int_env("ELEMENT_CONTEXT_OVERLAP", 1)
OLLAMA_PROTOCOL: str = _get_env("OLLAMA_PROTOCOL", "http")
OLLAMA_HOST: str = _get_env("OLLAMA_HOST", "localhost")
OLLAMA_PORT: int = _get_int_env("OLLAMA_PORT", 11434)
OLLAMA_BASE_URL: str = f"{OLLAMA_PROTOCOL}://{OLLAMA_HOST}:{OLLAMA_PORT}"
OLLAMA_OPENAI_BASE_URL: str = f"{OLLAMA_BASE_URL}/v1"


@dataclass(frozen=True)
class MinerUSettings:
    mode: str = _get_env("MINERU_MODE", "http")
    endpoint: str = _get_env("MINERU_ENDPOINT", "http://127.0.0.1:18543/file_parse")
    backend: str = _get_env("MINERU_BACKEND", "vllm-async-engine") # pdf解析后端，默认使用"vllm-async-engine"更快 # 可选值：""pipeline"",""vllm-async-engine""
    timeout_s: int = _get_int_env("MINERU_TIMEOUT_S", 600)
    lang_list: tuple[str, ...] = tuple(
        entry.strip() for entry in _get_env("MINERU_LANG_LIST", "en").split(",") if entry.strip()
    )


@dataclass(frozen=True)
class UploadSettings:
    root_dir: str = _get_env("UPLOAD_DIR", "/tmp/obqa_uploads")
    max_upload_mb: int = _get_int_env("MAX_UPLOAD_MB", 200)


@dataclass(frozen=True)
class EmbeddingSettings:
    endpoint: str = _get_env("EMBEDDING_ENDPOINT", "http://localhost:7701/v1/embeddings")
    model: str = _get_env("EMBEDDING_MODEL", "jinaembeddingv4")
    timeout_s: int = _get_int_env("EMBEDDING_TIMEOUT_S", 60)
    max_retries: int = _get_int_env("EMBEDDING_MAX_RETRIES", 1)
    api_key: str = _get_env("EMBEDDING_API_KEY", "")
    api_key_header: str = _get_env("EMBEDDING_API_KEY_HEADER", "Authorization")


@dataclass(frozen=True)
class LLMSettings:
    model: str = _get_env("LLM_MODEL_NAME", "llama3:70b")
    api_base: str = _get_env("LLM_API_BASE", OLLAMA_OPENAI_BASE_URL)
    api_key: str = _get_env("LLM_API_KEY", "EMPTY")
    api_key_header: str = _get_env("LLM_API_KEY_HEADER", "Authorization")
    temperature: float = _get_float_env("LLM_TEMPERATURE", 0.2)
    max_output_tokens: int = _get_int_env("LLM_MAX_OUTPUT_TOKENS", 800)


@dataclass(frozen=True)
class VisionVQASettings:
    endpoint: str = _get_env("VISION_VQA_ENDPOINT", OLLAMA_OPENAI_BASE_URL)
    model: str = _get_env("VISION_VQA_MODEL", "qwen2.5-vl-72b")
    api_key: str = _get_env("VISION_VQA_API_KEY", "EMPTY")
    api_key_header: str = _get_env("VISION_VQA_API_KEY_HEADER", "Authorization")
    timeout_s: int = _get_int_env("VISION_VQA_TIMEOUT_S", 120)
    max_tokens: int = _get_int_env("VISION_VQA_MAX_TOKENS", 400)


@lru_cache(maxsize=1)
def get_oceanbase_settings() -> OceanBaseSettings:
    """Return cached OceanBase connection settings."""
    return OceanBaseSettings()


@lru_cache(maxsize=1)
def get_mineru_settings() -> MinerUSettings:
    """Return MinerU HTTP integration preferences."""
    return MinerUSettings()


@lru_cache(maxsize=1)
def get_upload_settings() -> UploadSettings:
    """Return upload directory preferences."""
    return UploadSettings()


@lru_cache(maxsize=1)
def get_embedding_settings() -> EmbeddingSettings:
    """Return embedding service configuration."""
    return EmbeddingSettings()


@lru_cache(maxsize=1)
def get_llm_settings() -> LLMSettings:
    """Return DSPy/OpenAI LLM configuration."""
    return LLMSettings()


@lru_cache(maxsize=1)
def get_vision_vqa_settings() -> VisionVQASettings:
    """Return settings for the optional visual question answering client."""
    return VisionVQASettings()


__all__ = [
    "DB_CHARSET",
    "VECTOR_DIM",
    "INGEST_BATCH_SIZE",
    "ELEMENT_CONTEXT_OVERLAP",
    "OLLAMA_PROTOCOL",
    "OLLAMA_HOST",
    "OLLAMA_PORT",
    "OLLAMA_BASE_URL",
    "OLLAMA_OPENAI_BASE_URL",
    "OceanBaseSettings",
    "MinerUSettings",
    "UploadSettings",
    "EmbeddingSettings",
    "LLMSettings",
    "VisionVQASettings",
    "get_oceanbase_settings",
    "get_mineru_settings",
    "get_upload_settings",
    "get_embedding_settings",
    "get_llm_settings",
    "get_vision_vqa_settings",
]
