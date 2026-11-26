from fastapi import APIRouter

from ..schemas.schemas import ToolStatus
from ..services import flagshark_service, piranha_service
from ..services.git_service import git_available
from ..services.test_service import maven_available

router = APIRouter(tags=["health"])


@router.get("/api/health", summary="Backend + tool availability")
def health() -> dict:
    fs = flagshark_service.flagshark_status()
    pir = piranha_service.piranha_status()
    git_ok, git_ver = git_available()
    return {
        "status": "ok",
        "tools": {
            "flagshark": fs,
            "piranha": pir,
            "git": {"available": git_ok, "version": git_ver or "UNAVAILABLE"},
            "maven": {"available": maven_available()},
        },
    }


@router.get("/health", summary="Liveness probe")
def liveness() -> dict:
    return {"status": "ok"}


@router.get("/health/db", summary="Readiness probe: verifies an actual database connection")
def db_health() -> dict:
    from sqlalchemy import text

    from ..config import effective_database_url
    from ..database import engine
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        url = effective_database_url()
        dialect = url.split(":")[0]
        return {"status": "ok", "dialect": dialect}
    except Exception as exc:
        from fastapi import HTTPException
        raise HTTPException(status_code=503, detail=f"database unreachable: {exc}")


@router.get("/api/tools/status", summary="Detailed tool status list")
def tools_status() -> list[ToolStatus]:
    fs = flagshark_service.flagshark_status()
    pir = piranha_service.piranha_status()
    git_ok, git_ver = git_available()
    return [
        ToolStatus(name="flagshark", available=fs["available"], version=fs.get("version", "")[:200],
                   path=fs.get("path", ""), hint=fs.get("hint", "")),
        ToolStatus(name="piranha", available=pir["available"], version=pir.get("version", "")[:200],
                   path=pir.get("path", ""), hint=pir.get("hint", "")),
        ToolStatus(name="git", available=git_ok, version=(git_ver or "")[:200]),
        ToolStatus(name="maven", available=maven_available()),
    ]
