from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    telegram_bot_token: str = Field(alias="TELEGRAM_BOT_TOKEN")
    gemini_api_key: str = Field(alias="GEMINI_API_KEY")
    database_url: str = Field(alias="DATABASE_URL", default="sqlite+aiosqlite:///./tarot_bot.db")
    gemini_model: str = Field(alias="GEMINI_MODEL", default="gemini-2.0-flash")
    voice_model_size: str = Field(alias="VOICE_MODEL_SIZE", default="tiny")
    allow_reversed_cards: bool = Field(alias="ALLOW_REVERSED_CARDS", default=False)
    bot_timezone: str = Field(alias="BOT_TIMEZONE", default="Europe/Chisinau")
    data_dir: Path = Field(default=Path("."))


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    load_dotenv()
    return Settings()
