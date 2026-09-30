"""Application settings, loaded from environment variables or a .env file."""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=(".env", "../.env"), extra="ignore")

    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.5-flash"
    database_url: str = "sqlite:///./data/app.db"
    max_upload_mb: int = 5
    max_text_chars: int = 30000
    cors_origins: str = "*"


@lru_cache
def get_settings() -> Settings:
    return Settings()
