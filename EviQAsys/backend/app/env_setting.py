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


@dataclass(frozen=True)
class OceanBaseSettings:
    host: str = _get_env("OB_HOST", "127.0.0.1")
    port: int = _get_int_env("OB_PORT", 2881)
    user: str = _get_env("OB_USER", "paperQA@test")
    password: str = _get_env("OB_PASSWORD", "12345678")
    default_database: str = _get_env("OB_DEFAULT_DATABASE", "obqa_dev")
    connect_timeout: int = _get_int_env("DATABASE_CONNECT_TIMEOUT", 10)


DB_CHARSET: str = _get_env("DB_CHARSET", "utf8mb4")
VECTOR_DIM: int = _get_int_env("VECTOR_DIM", 64)
INGEST_BATCH_SIZE: int = _get_int_env("BATCH_SIZE", 32)
OLLAMA_PROTOCOL: str = _get_env("OLLAMA_PROTOCOL", "http")
OLLAMA_HOST: str = _get_env("OLLAMA_HOST", "localhost")
OLLAMA_PORT: int = _get_int_env("OLLAMA_PORT", 11434)
OLLAMA_BASE_URL: str = f"{OLLAMA_PROTOCOL}://{OLLAMA_HOST}:{OLLAMA_PORT}"
OLLAMA_OPENAI_BASE_URL: str = f"{OLLAMA_BASE_URL}/v1"


@dataclass(frozen=True)
class MinerUSettings:
    mode: str = _get_env("MINERU_MODE", "http")
    endpoint: str = _get_env("MINERU_ENDPOINT", "http://127.0.0.1:18543/file_parse")
    backend: str = _get_env("MINERU_BACKEND", "pipeline")
    timeout_s: int = _get_int_env("MINERU_TIMEOUT_S", 600)
    lang_list: tuple[str, ...] = tuple(
        entry.strip() for entry in _get_env("MINERU_LANG_LIST", "en").split(",") if entry.strip()
    )


@dataclass(frozen=True)
class UploadSettings:
    root_dir: str = _get_env("UPLOAD_DIR", "/tmp/obqa_uploads")
    max_upload_mb: int = _get_int_env("MAX_UPLOAD_MB", 200)


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


__all__ = [
    "DB_CHARSET",
    "VECTOR_DIM",
    "INGEST_BATCH_SIZE",
    "OLLAMA_PROTOCOL",
    "OLLAMA_HOST",
    "OLLAMA_PORT",
    "OLLAMA_BASE_URL",
    "OLLAMA_OPENAI_BASE_URL",
    "OceanBaseSettings",
    "MinerUSettings",
    "UploadSettings",
    "get_oceanbase_settings",
    "get_mineru_settings",
    "get_upload_settings",
]
