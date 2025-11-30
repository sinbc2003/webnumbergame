from functools import lru_cache
from typing import List, Union
import secrets

from pydantic import AnyHttpUrl, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


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
    cors_origins: List[Union[AnyHttpUrl, str]] = ["http://localhost:3000"]
    default_round_minutes: int = 3
    leaderboard_window_hours: int = 24
    max_room_capacity: int = 16

    @field_validator("cors_origins", mode="before")
    @classmethod
    def split_cors(cls, value):
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()

