import json
import secrets
from functools import lru_cache
from typing import List

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_CORS_ORIGINS = ["http://localhost:3000"]


def _parse_cors_origins(value: str | List[str] | None) -> List[str] | None:
    if value is None:
        return None

    if isinstance(value, (list, tuple, set)):
        return [str(origin).strip() for origin in value if str(origin).strip()]

    stripped = str(value).strip()
    if not stripped:
        return []

    if stripped.startswith("[") and stripped.endswith("]"):
        try:
            loaded = json.loads(stripped)
        except json.JSONDecodeError:
            inner = stripped[1:-1].strip()
            if not inner:
                return []
            stripped = inner
        else:
            if isinstance(loaded, list):
                return [str(origin).strip() for origin in loaded if str(origin).strip()]

    return [origin.strip() for origin in stripped.split(",") if origin.strip()]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Number Game Platform"
    api_prefix: str = "/api"
    secret_key: str = Field(default_factory=lambda: secrets.token_urlsafe(32))
    access_token_expire_minutes: int = 60 * 12
    refresh_token_expire_minutes: int = 60 * 24 * 30
    database_url: str = "sqlite+aiosqlite:///./number_game.db"
    redis_url: str | None = None
    cors_origins_raw: str | None = Field(default=None, alias="CORS_ORIGINS")
    default_round_minutes: int = 3
    leaderboard_window_hours: int = 24
    max_room_capacity: int = 16
    db_init_max_retries: int = 5
    db_init_retry_interval_seconds: float = 2.0

    @field_validator("database_url")
    @classmethod
    def ensure_async_driver(cls, value: str) -> str:
        """
        Cloud Run / GitHub Actions 환경 변수에서 흔히 사용하는
        postgresql:// 혹은 postgres:// 형태를 자동으로 asyncpg 드라이버로 보정한다.
        """
        if not value:
            return value

        if value.startswith("postgres://"):
            return "postgresql+asyncpg://" + value[len("postgres://") :]

        if value.startswith("postgresql://") and "+asyncpg" not in value.split("://", 1)[0]:
            return value.replace("postgresql://", "postgresql+asyncpg://", 1)

        return value

    @property
    def cors_origins(self) -> List[str]:
        parsed = _parse_cors_origins(self.cors_origins_raw)
        if not parsed:
            return DEFAULT_CORS_ORIGINS
        return parsed


@lru_cache
def get_settings() -> Settings:
    return Settings()

