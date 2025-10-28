"""Application configuration powered by environment variables."""

from functools import lru_cache
from typing import Optional
from urllib.parse import quote_plus

from pydantic import BaseSettings, Field


class Settings(BaseSettings):
    """Centralised application settings."""

    app_name: str = Field(default="EviQAsys", alias="APP_NAME")

    ob_host: str = Field(default="127.0.0.1", alias="OB_HOST")
    ob_port: int = Field(default=2881, alias="OB_PORT")
    ob_user: str = Field(default="paperQA@test", alias="OB_USER")
    ob_password: str = Field(default="12345678", alias="OB_PASSWORD")
    ob_database: str = Field(default="eviqasys", alias="OB_DATABASE")
    ob_charset: str = Field(default="utf8mb4", alias="OB_CHARSET")

    sql_echo: bool = Field(default=False, alias="SQL_ECHO")
    vector_dimension: int = Field(default=1536, alias="VECTOR_DIMENSION", ge=1)

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False

    @property
    def sqlalchemy_database_uri(self) -> str:
        """Return DSN for the main OceanBase schema."""
        user = quote_plus(self.ob_user)
        password = quote_plus(self.ob_password)
        return (
            f"mysql+pymysql://{user}:{password}"
            f"@{self.ob_host}:{self.ob_port}/{self.ob_database}"
            f"?charset={self.ob_charset}"
        )

    @property
    def sqlalchemy_server_uri(self) -> str:
        """Return DSN pointing to server without schema, for bootstrap tasks."""
        user = quote_plus(self.ob_user)
        password = quote_plus(self.ob_password)
        return (
            f"mysql+pymysql://{user}:{password}"
            f"@{self.ob_host}:{self.ob_port}/?charset={self.ob_charset}"
        )


@lru_cache()
def get_settings() -> Settings:
    """Cached settings accessor."""
    return Settings()  # type: ignore[call-arg]


settings: Settings = get_settings()
