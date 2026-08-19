"""Application settings, read from environment variables / `.env`
(matching `.env.example` exactly) via pydantic-settings -- never
hardcoded (constitution Principle II; MVP_CONTEXT.md Section 7).
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # --- Database ---
    database_url: str = "sqlite:///./payerguard.db"

    # --- LLM (Mistral) ---
    mistral_api_key: str | None = None
    mistral_model: str = "mistral-small-latest"

    # --- App ---
    environment: str = "development"
    log_level: str = "INFO"

    # --- CORS ---
    # Browser origins allowed to call this API. Defaults cover the Vite dev
    # server and the eventual Dockerized frontend port.
    cors_allowed_origins: list[str] = ["http://localhost:5173", "http://localhost:3000"]

    # --- Ingestion ---
    ingestion_watch_dir: str = "./data/raw"


@lru_cache
def get_settings() -> Settings:
    return Settings()
