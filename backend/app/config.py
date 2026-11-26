from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    DATABASE_URL: str = "sqlite:///./feature_flags.db"
    # PostgreSQL (primary in Docker Compose; unset password locally -> SQLite fallback stays default)
    POSTGRES_HOST: str = "postgres"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "ffsd"
    POSTGRES_USER: str = "ffsd"
    POSTGRES_PASSWORD: str = ""
    BACKEND_HOST: str = "127.0.0.1"
    BACKEND_PORT: int = 8000
    FRONTEND_ORIGIN: str = "http://localhost:5173"
    WORKSPACE_DIR: str = "./workspaces"
    FLAGS_HARK_BIN: str = "flagshark"
    PIRANHA_BIN: str = "piranha"
    GIT_BIN: str = "git"
    MVN_BIN: str = "mvn"
    SCAN_TIMEOUT_SEC: int = 300
    PIRANHA_TIMEOUT_SEC: int = 300
    TEST_TIMEOUT_SEC: int = 900
    CLONE_TIMEOUT_SEC: int = 300


@lru_cache
def get_settings() -> Settings:
    return Settings()


def effective_database_url(s: Settings | None = None) -> str:
    """PostgreSQL is primary when explicitly configured; otherwise honor DATABASE_URL (SQLite dev default).

    Docker Compose sets DATABASE_URL to the postgres DSN directly. A bare
    POSTGRES_PASSWORD without DATABASE_URL also builds the DSN — but never with
    a hardcoded password; empty password means 'not configured'.
    """
    s = s or get_settings()
    if s.DATABASE_URL and not s.DATABASE_URL.startswith("sqlite"):
        return s.DATABASE_URL
    if s.POSTGRES_PASSWORD:
        return (
            f"postgresql+psycopg://{s.POSTGRES_USER}:{s.POSTGRES_PASSWORD}"
            f"@{s.POSTGRES_HOST}:{s.POSTGRES_PORT}/{s.POSTGRES_DB}"
        )
    return s.DATABASE_URL
