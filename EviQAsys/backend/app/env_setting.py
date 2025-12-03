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
PER_EVIDENCE_ELEM_CHAR_LIMIT: int = _get_int_env("PER_EVIDENCE_ELEM_CHAR_LIMIT", 3600)
OLLAMA_PROTOCOL: str = _get_env("OLLAMA_PROTOCOL", "http")
OLLAMA_HOST: str = _get_env("OLLAMA_HOST", "localhost")
OLLAMA_PORT: int = _get_int_env("OLLAMA_PORT", 11434)
OLLAMA_BASE_URL: str = f"{OLLAMA_PROTOCOL}://{OLLAMA_HOST}:{OLLAMA_PORT}"
OLLAMA_OPENAI_BASE_URL: str = f"{OLLAMA_BASE_URL}/v1"
OPENROUTER_API_BASE_URL: str = _get_env("OPENROUTER_API_BASE_URL", "https://openrouter.ai/api/v1")
DEFAULT_TEXT_LLM_MODEL: str = _get_env("DEFAULT_TEXT_LLM_MODEL", "x-ai/grok-4.1-fast:free")
DEFAULT_VISION_LLM_MODEL: str = _get_env("DEFAULT_VISION_LLM_MODEL", "x-ai/grok-4-fast")
OPENROUTER_API_KEY = _get_env("OPENROUTER_API_KEY")
LLM_API_BASE_DEFAULT: str = _get_env("LLM_API_BASE", OPENROUTER_API_BASE_URL)
LLM_API_KEY_DEFAULT: str = _get_env("LLM_API_KEY", OPENROUTER_API_KEY)
LLM_API_KEY_HEADER_DEFAULT: str = _get_env("LLM_API_KEY_HEADER", "Authorization")
LLM_TEMPERATURE_DEFAULT: float = _get_float_env("LLM_TEMPERATURE", 0.2)
LLM_MAX_OUTPUT_TOKENS_DEFAULT: int = _get_int_env("LLM_MAX_OUTPUT_TOKENS", 30000)
MIN_CHARACTOR_CHUNK_SIZE: int = _get_int_env("MIN_CHARACTOR_CHUNK_SIZE", 256)
MAX_CHARACTOR_CHUNK_SIZE: int = _get_int_env("MAX_CHARACTOR_CHUNK_SIZE", 3200)
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
    backend: str = _get_env("MINERU_BACKEND", "pipeline") # pdf解析后端，默认使用"vllm-async-engine"更快，支持高并发，后续可扩展 # 可选值："pipeline","vllm-async-engine"
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
    api_base: str = LLM_API_BASE_DEFAULT
    api_key: str = LLM_API_KEY_DEFAULT
    api_key_header: str = LLM_API_KEY_HEADER_DEFAULT
    temperature: float = LLM_TEMPERATURE_DEFAULT
    max_output_tokens: int = LLM_MAX_OUTPUT_TOKENS_DEFAULT


@dataclass(frozen=True)
class VisionLLMSettings:
    model: str = _get_env("VISION_LLM_MODEL", _get_env("VISION_VQA_MODEL", DEFAULT_VISION_LLM_MODEL))
    api_base: str = _get_env("VISION_LLM_API_BASE", LLM_API_BASE_DEFAULT)
    api_key: str = _get_env("VISION_LLM_API_KEY", LLM_API_KEY_DEFAULT)
    api_key_header: str = _get_env("VISION_LLM_API_KEY_HEADER", LLM_API_KEY_HEADER_DEFAULT)
    temperature: float = _get_float_env("VISION_LLM_TEMPERATURE", LLM_TEMPERATURE_DEFAULT)
    max_output_tokens: int = _get_int_env("VISION_LLM_MAX_OUTPUT_TOKENS", LLM_MAX_OUTPUT_TOKENS_DEFAULT)


@dataclass(frozen=True)
class QAFlowSettings:
    default_use_image: bool = _get_bool_env("QA_USE_IMAGE_DEFAULT", False)
    default_text_retrieve_topk: int = _get_int_env("QA_TEXT_RETRIEVE_TOPK_DEFAULT", 8)
    default_image_retrieve_topk: int = _get_int_env("QA_IMAGE_RETRIEVE_TOPK_DEFAULT", 2)
    default_text_memory_topk: int = _get_int_env("QA_TEXT_MEMORY_TOPK_DEFAULT", 4)
    default_image_memory_topk: int = _get_int_env("QA_IMAGE_MEMORY_TOPK_DEFAULT", 1)
    default_use_page_in_text_retrieve: bool = _get_bool_env("QA_USE_PAGE_IN_TEXT_RETRIEVE_DEFAULT", False)
    default_page_retrieve_topk: int = _get_int_env("QA_PAGE_RETRIEVE_TOPK_DEFAULT", 4)
    default_text_search_mode: str = _get_env("QA_TEXT_SEARCH_MODE_DEFAULT", "hybrid")
    memory_max_length: int = _get_int_env("QA_MEMORY_MAX_LENGTH", 4000)
    max_summary_memory_length: int = _get_int_env("QA_MAX_SUMMARY_MEMORY_LENGTH", 1000)


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
    """Return DSPy/OpenAI LLM configuration (text LLM)."""
    return LLMSettings()


@lru_cache(maxsize=1)
def get_vision_llm_settings() -> VisionLLMSettings:
    """Return OpenAI-compatible vision LLM configuration."""
    return VisionLLMSettings()


@lru_cache(maxsize=1)
def get_qa_flow_settings() -> QAFlowSettings:
    """Return QA flow defaults including retrieval/memory toggles."""
    return QAFlowSettings()


__all__ = [
    "DB_CHARSET",
    "VECTOR_DIM",
    "INGEST_BATCH_SIZE",
    "MIN_CHARACTOR_CHUNK_SIZE",
    "MAX_CHARACTOR_CHUNK_SIZE",
    "MAX_ELEM_CHUNK_SIZE",
    "CHUNK_SKIP_PATTERNS",
    "PER_EVIDENCE_ELEM_CHAR_LIMIT",
    "OLLAMA_PROTOCOL",
    "OLLAMA_HOST",
    "OLLAMA_PORT",
    "OLLAMA_BASE_URL",
    "OLLAMA_OPENAI_BASE_URL",
    "OPENROUTER_API_BASE_URL",
    "DEFAULT_TEXT_LLM_MODEL",
    "DEFAULT_VISION_LLM_MODEL",
    "RETRIEVAL_TOPK_CHUNK",
    "RETRIEVAL_TOPK_PAGE",
    "ENABLE_PAGE_CHUNK_RETRIEVAL",
    "ENABLE_PAGE_TEXT_CHUNKS",
    "OceanBaseSettings",
    "MinerUSettings",
    "UploadSettings",
    "EmbeddingSettings",
    "LLMSettings",
    "VisionLLMSettings",
    "QAFlowSettings",
    "get_oceanbase_settings",
    "get_mineru_settings",
    "get_upload_settings",
    "get_embedding_settings",
    "get_llm_settings",
    "get_vision_llm_settings",
    "get_qa_flow_settings",
]
