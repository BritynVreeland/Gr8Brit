"""Runtime settings, read from environment variables (or a local .env file)."""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=REPO_ROOT / ".env", extra="ignore")

    database_url: str | None = None
    supabase_url: str | None = None
    supabase_service_role_key: str | None = None
    anthropic_api_key: str | None = None
    voyage_api_key: str | None = None
    meta_access_token: str | None = None
    meta_app_id: str | None = None
    meta_app_secret: str | None = None
    meta_graph_version: str = "v24.0"
    youtube_api_key: str | None = None
    author_hash_salt: str | None = None

    config_dir: Path = REPO_ROOT / "config"
    migrations_dir: Path = REPO_ROOT / "db" / "migrations"


@lru_cache
def get_settings() -> Settings:
    return Settings()
