import json
import secrets
from functools import lru_cache
from typing import Annotated, List, Union

from pydantic import AnyHttpUrl, Field
from pydantic.functional_validators import BeforeValidator
from pydantic_settings import BaseSettings, SettingsConfigDict


def _parse_cors_origins(value):
    if value is None:
        return value
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return []
        if stripped.startswith("["):
            try:
                loaded = json.loads(stripped)
                if isinstance(loaded, list):
                    return loaded
            except json.JSONDecodeError:
                pass
        return [origin.strip() for origin in stripped.split(",") if origin.strip()]
    return value


CorsOrigins = Annotated[List[Union[AnyHttpUrl, str]], BeforeValidator(_parse_cors_origins)]


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
    cors_origins: CorsOrigins = ["http://localhost:3000"]
    default_round_minutes: int = 3
    leaderboard_window_hours: int = 24
    max_room_capacity: int = 16


@lru_cache
def get_settings() -> Settings:
    return Settings()

