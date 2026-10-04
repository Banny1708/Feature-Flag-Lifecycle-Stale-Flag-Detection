from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    DATABASE_URL: str = "sqlite:///./feature_flags.db"
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


@lru_cache
def get_settings() -> Settings:
    return Settings()
