from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import yaml


CONFIG_PATH = Path(__file__).resolve().parent / "config.yaml"


def _load_config() -> dict[str, object]:
    """Load YAML configuration, returning an empty dict if missing or invalid."""
    if not CONFIG_PATH.exists():
        return {}
    try:
        with CONFIG_PATH.open("r", encoding="utf-8") as config_file:
            loaded = yaml.safe_load(config_file) or {}
            return loaded if isinstance(loaded, dict) else {}
    except (OSError, yaml.YAMLError):
        return {}


CONFIG = _load_config()


def get_config(name: str, default: str | int | float | bool | None = None) -> str | int | float | bool | None:
    """Return a config value preferring YAML, then environment variables."""
    if name in CONFIG:
        value = CONFIG.get(name)
        if value not in {None, ""}:
            return value

    env_value = os.getenv(name)
    if env_value not in (None, ""):
        return env_value

    return default


def _get_env(name: str, default: str | None = None) -> str | None:
    value = get_config(name, default)
    if value is None or value == "":
        return default
    return str(value)

def _get_bool_env(name: str, default: bool) -> bool:
    raw_value = get_config(name, default)
    if raw_value is None or raw_value == "":
        return default
    if isinstance(raw_value, bool):
        return raw_value
    lowered = str(raw_value).strip().lower()
    return lowered in {"1", "true", "yes", "y", "on"}


def _get_elem_types_env(name: str, default: tuple[str, ...]) -> tuple[str, ...]:
    raw_value = get_config(name, ",".join(default))
    if isinstance(raw_value, (list, tuple)):
        raw_list = ",".join(str(entry) for entry in raw_value)
    else:
        raw_list = raw_value if raw_value is not None and raw_value != "" else ",".join(default)
    normalized: list[str] = []
    for entry in raw_list.split(","):
        trimmed = entry.strip().lower()
        if not trimmed or trimmed in normalized:
            continue
        normalized.append(trimmed)
    return tuple(normalized) if normalized else default



def _get_int_env(name: str, default: int) -> int:
    raw_value = get_config(name, default)
    if raw_value is None or raw_value == "":
        return default
    try:
        return int(raw_value)
    except (ValueError, TypeError) as exc:  # pragma: no cover - defensive guard rails
        raise ValueError(f"Invalid integer for {name}: {raw_value}") from exc


def _get_float_env(name: str, default: float) -> float:
    raw_value = get_config(name, default)
    if raw_value is None or raw_value == "":
        return default
    try:
        return float(raw_value)
    except (ValueError, TypeError) as exc:  # pragma: no cover - defensive guard rails
        raise ValueError(f"Invalid float for {name}: {raw_value}") from exc


def _get_str_tuple_env(name: str, default: tuple[str, ...]) -> tuple[str, ...]:
    raw_value = get_config(name, ",".join(default))
    if isinstance(raw_value, (list, tuple)):
        raw_list = [str(entry) for entry in raw_value]
    else:
        raw_list = str(raw_value or "").split(",")
    normalized: list[str] = []
    for entry in raw_list:
        trimmed = entry.strip()
        if not trimmed or trimmed in normalized:
            continue
        normalized.append(trimmed)
    return tuple(normalized) if normalized else default


@dataclass(frozen=True)
class OceanBaseSettings:
    host: str = _get_env("OB_HOST", "127.0.0.1")
    port: int = _get_int_env("OB_PORT", 2893)
    user: str = _get_env("OB_USER", "root")
    password: str = _get_env("OB_PASSWORD", "")
    default_database: str = _get_env("OB_DEFAULT_DATABASE", "test")
    connect_timeout: int = _get_int_env("DATABASE_CONNECT_TIMEOUT", 10)


DB_CHARSET: str = _get_env("DB_CHARSET", "utf8mb4")
VECTOR_DIM: int = _get_int_env("VECTOR_DIM", 2048)
INGEST_BATCH_SIZE: int = _get_int_env("BATCH_SIZE", 32)
EVIDENCE_PROMPT_CHAR_LIMIT: int = _get_int_env("EVIDENCE_PROMPT_CHAR_LIMIT", 2560)
OLLAMA_PROTOCOL: str = _get_env("OLLAMA_PROTOCOL", "http")
OLLAMA_HOST: str = _get_env("OLLAMA_HOST", "localhost")
OLLAMA_PORT: int = _get_int_env("OLLAMA_PORT", 11434)
OLLAMA_BASE_URL: str = f"{OLLAMA_PROTOCOL}://{OLLAMA_HOST}:{OLLAMA_PORT}"
OLLAMA_OPENAI_BASE_URL: str = f"{OLLAMA_BASE_URL}/v1"
OPENROUTER_API_BASE_URL: str = _get_env("OPENROUTER_API_BASE_URL", "https://openrouter.ai/api/v1")
DEFAULT_TEXT_LLM_MODEL: str = _get_env("DEFAULT_TEXT_LLM_MODEL", "x-ai/grok-4.1-fast")
OPENROUTER_API_KEY = _get_env("OPENROUTER_API_KEY")
DEFAULT_VLSION_MODEL = _get_env("DEFAULT_VLSION_MODEL", "x-ai/grok-4-fast")
MIN_CHARACTOR_CHUNK_SIZE: int = _get_int_env("MIN_CHARACTOR_CHUNK_SIZE", 480)
MAX_CHARACTOR_CHUNK_SIZE: int = _get_int_env("MAX_CHARACTOR_CHUNK_SIZE", 1200)
MAX_ELEM_CHUNK_SIZE: int = _get_int_env("MAX_ELEM_CHUNK_SIZE", 6)
CHUNK_SKIP_PATTERNS: tuple[str, ...] = _get_str_tuple_env(
    "CHUNK_SKIP_PATTERNS",
    (r"^\s*$", r"^[\u0000-\u001f\u007f]+$"),
)
RETRIEVAL_TOPK_CHUNK: int = _get_int_env("RETRIEVAL_TOPK_CHUNK", 6)
RETRIEVAL_TOPK_PAGE: int = _get_int_env("RETRIEVAL_TOPK_PAGE", 3)
ENABLE_PAGE_CHUNK_RETRIEVAL: bool = _get_bool_env("ENABLE_PAGE_CHUNK_RETRIEVAL", False)
ENABLE_PAGE_TEXT_CHUNKS: bool = _get_bool_env("ENABLE_PAGE_TEXT_CHUNKS", True)

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
    model: str = _get_env("LLM_MODEL_NAME", DEFAULT_TEXT_LLM_MODEL)
    api_base: str = _get_env("LLM_API_BASE", OPENROUTER_API_BASE_URL)
    api_key: str = _get_env("LLM_API_KEY", OPENROUTER_API_KEY)
    api_key_header: str = _get_env("LLM_API_KEY_HEADER", "Authorization")
    temperature: float = _get_float_env("LLM_TEMPERATURE", 0.2)
    max_output_tokens: int = _get_int_env("LLM_MAX_OUTPUT_TOKENS", 16000)


@dataclass(frozen=True)
class VisionVQASettings:
    endpoint: str = _get_env("VISION_VQA_ENDPOINT", OPENROUTER_API_BASE_URL)
    model: str = _get_env("VISION_VQA_MODEL",DEFAULT_VLSION_MODEL ) #  "x-ai/grok-4-fast"
    api_key: str = _get_env("VISION_VQA_API_KEY", OPENROUTER_API_KEY)
    api_key_header: str = _get_env("VISION_VQA_API_KEY_HEADER", "Authorization")
    timeout_s: int = _get_int_env("VISION_VQA_TIMEOUT_S", 120)
    max_tokens: int = _get_int_env("VISION_VQA_MAX_TOKENS", 400)



DEFAULT_QA_ELEM_TYPES: tuple[str, ...] = ("text", "header", "table", "image")


@dataclass(frozen=True)
class QAFlowSettings:
    max_history_turns: int = _get_int_env("QA_MAX_HISTORY_TURNS", 8)
    text_evidence_limit: int = _get_int_env("QA_TEXT_EVIDENCE_LIMIT", 8)
    image_evidence_limit: int = _get_int_env("QA_IMAGE_EVIDENCE_LIMIT", 4)
    enable_memory_summarizer: bool = _get_bool_env("QA_ENABLE_MEMORY_SUMMARIZER", False)
    enable_image_vqa: bool = _get_bool_env("QA_ENABLE_IMAGE_VQA", False)
    default_retrieval_mode: str = _get_env("QA_DEFAULT_RETRIEVAL_MODE", "auto")
    default_search_mode: str = _get_env("QA_DEFAULT_SEARCH_MODE", "hybrid")
    default_elem_types: tuple[str, ...] = _get_elem_types_env("QA_DEFAULT_ELEM_TYPES", DEFAULT_QA_ELEM_TYPES)
    retrieval_topk_chunk: int = RETRIEVAL_TOPK_CHUNK
    retrieval_topk_page: int = RETRIEVAL_TOPK_PAGE
    enable_page_chunk_retrieval: bool = ENABLE_PAGE_CHUNK_RETRIEVAL
    enable_page_text_chunks: bool = ENABLE_PAGE_TEXT_CHUNKS


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
    """Return DSPy/OpenAI LLM configuration (OpenRouter grok-4.1-fast by default)."""
    return LLMSettings()


@lru_cache(maxsize=1)
def get_vision_vqa_settings() -> VisionVQASettings:
    """Return settings for the optional visual question answering client."""
    return VisionVQASettings()


@lru_cache(maxsize=1)
def get_qa_flow_settings() -> QAFlowSettings:
    """Return QA flow defaults including retrieval/memory/VQA toggles."""
    return QAFlowSettings()


__all__ = [
    "DB_CHARSET",
    "VECTOR_DIM",
    "INGEST_BATCH_SIZE",
    "MIN_CHARACTOR_CHUNK_SIZE",
    "MAX_CHARACTOR_CHUNK_SIZE",
    "MAX_ELEM_CHUNK_SIZE",
    "CHUNK_SKIP_PATTERNS",
    "EVIDENCE_PROMPT_CHAR_LIMIT",
    "OLLAMA_PROTOCOL",
    "OLLAMA_HOST",
    "OLLAMA_PORT",
    "OLLAMA_BASE_URL",
    "OLLAMA_OPENAI_BASE_URL",
    "OPENROUTER_API_BASE_URL",
    "DEFAULT_TEXT_LLM_MODEL",
    "RETRIEVAL_TOPK_CHUNK",
    "RETRIEVAL_TOPK_PAGE",
    "ENABLE_PAGE_CHUNK_RETRIEVAL",
    "ENABLE_PAGE_TEXT_CHUNKS",
    "OceanBaseSettings",
    "MinerUSettings",
    "UploadSettings",
    "EmbeddingSettings",
    "LLMSettings",
    "VisionVQASettings",
    "QAFlowSettings",
    "get_oceanbase_settings",
    "get_mineru_settings",
    "get_upload_settings",
    "get_embedding_settings",
    "get_llm_settings",
    "get_vision_vqa_settings",
    "get_qa_flow_settings",
]
