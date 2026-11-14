from functools import lru_cache
from pathlib import Path
from typing import Annotated

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict
from sqlalchemy.engine import make_url

ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
        validate_assignment=True,
        hide_input_in_errors=True,
    )

    app_env: str = "development"
    database_url: str = Field(
        default="postgresql+psycopg://smartmall:CHANGE_ME@localhost:5432/smartmall", repr=False
    )
    cors_origins: Annotated[list[str], NoDecode] = ["http://localhost:5173"]
    ai_provider: str = "openai"
    ai_model: str = "gpt-5.4-mini"
    ai_simulation: bool = False
    openai_api_key: SecretStr | None = None
    ai_timeout_seconds: float = Field(default=20, gt=0, le=120)
    demo_access_token: SecretStr | None = Field(default=None, repr=False)
    demo_seed: bool = False

    @field_validator("demo_access_token", mode="before")
    @classmethod
    def validate_demo_token(cls, value):
        if value is None or value == "":
            return None
        token = value.get_secret_value() if isinstance(value, SecretStr) else value
        if len(token) < 32 or not token.isascii() or any(c.isspace() for c in token):
            raise ValueError("DEMO_ACCESS_TOKEN exige ao menos 32 caracteres ASCII sem espaços.")
        return value

    @model_validator(mode="after")
    def validate_deployment(self):
        if self.app_env != "development" and not self.demo_access_token:
            raise ValueError("Fora de development, configure DEMO_ACCESS_TOKEN.")
        if self.app_env == "demo" and not self.ai_simulation:
            raise ValueError("APP_ENV=demo exige AI_SIMULATION=true.")
        if self.demo_seed and self.app_env != "demo":
            raise ValueError("DEMO_SEED só é permitido em APP_ENV=demo.")
        return self

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
