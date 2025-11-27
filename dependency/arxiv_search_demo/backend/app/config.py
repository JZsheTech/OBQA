from functools import lru_cache
from typing import List

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    Centralized application configuration pulled from environment variables.
    Default values keep local development easy (SQLite, local CORS).
    """

    database_url: str = Field(
        default="mysql+pymysql://root:@127.0.0.1:2893/test?charset=utf8mb4",
        description="SQLAlchemy-compatible DB URL, e.g. mysql+pymysql://user:pass@host:3306/db",
    )
    arxiv_delay_seconds: float = Field(default=3.0, ge=0)
    arxiv_num_retries: int = Field(default=3, ge=0)
    arxiv_page_size: int = Field(default=50, ge=1, le=50)

    cors_allow_origins: List[str] = Field(
        default_factory=lambda: [
            "http://localhost:5373",
            "http://127.0.0.1:5373",
            "http://localhost:3000",
        ]
    )

    @field_validator("cors_allow_origins", mode="before")
    @classmethod
    def split_origins(cls, value):
        if isinstance(value, str):
            return [v.strip() for v in value.split(",") if v.strip()]
        return value

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
