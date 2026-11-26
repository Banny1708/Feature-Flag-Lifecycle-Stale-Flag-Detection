import time

from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from .config import effective_database_url, get_settings


class Base(DeclarativeBase):
    pass


def _connect_args(url: str) -> dict:
    if url.startswith("sqlite"):
        return {"check_same_thread": False}
    return {}


def build_engine(url: str | None = None):
    url = url or effective_database_url()
    return create_engine(url, connect_args=_connect_args(url), pool_pre_ping=True)


settings = get_settings()
engine = build_engine()
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def wait_for_db(retries: int = 30, delay: float = 2.0) -> None:
    """Block until the database accepts connections (backend waits for PostgreSQL)."""
    last: Exception | None = None
    for _ in range(retries):
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return
        except Exception as exc:  # noqa: BLE001 - startup resilience
            last = exc
            time.sleep(delay)
    raise RuntimeError(f"database not reachable: {last}")


def init_db() -> None:
    from .models import models  # noqa: F401  (register models)
    Base.metadata.create_all(bind=engine)
