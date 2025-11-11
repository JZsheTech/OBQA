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


@lru_cache(maxsize=1)
def get_oceanbase_settings() -> OceanBaseSettings:
    """Return cached OceanBase connection settings."""
    return OceanBaseSettings()


__all__ = [
    "DB_CHARSET",
    "VECTOR_DIM",
    "OceanBaseSettings",
    "get_oceanbase_settings",
]
