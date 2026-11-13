from functools import lru_cache
from pathlib import Path
from typing import Annotated

from pydantic import field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict
from sqlalchemy.engine import make_url

ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ROOT / ".env", env_file_encoding="utf-8", extra="ignore"
    )

    app_env: str = "development"
    database_url: str = "postgresql+psycopg://smartmall:CHANGE_ME@localhost:5432/smartmall"
    cors_origins: Annotated[list[str], NoDecode] = ["http://localhost:5173"]

    @field_validator("database_url")
    @classmethod
    def use_psycopg(cls, value: str) -> str:
        url = make_url(value)
        if url.drivername not in {"postgresql", "postgresql+psycopg"}:
            raise ValueError("DATABASE_URL deve usar PostgreSQL com psycopg.")
        return url.set(drivername="postgresql+psycopg").render_as_string(hide_password=False)

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_origins(cls, value: str | list[str]) -> list[str]:
        origins = value.split(",") if isinstance(value, str) else value
        result = [origin.strip().rstrip("/") for origin in origins if origin.strip()]
        if any(not origin.startswith(("http://", "https://")) for origin in result):
            raise ValueError("CORS_ORIGINS deve conter origens HTTP/HTTPS separadas por vírgula.")
        return result


@lru_cache
def get_settings() -> Settings:
    return Settings()
