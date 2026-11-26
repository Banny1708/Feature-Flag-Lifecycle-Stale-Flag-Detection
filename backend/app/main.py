from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .config import get_settings
from .database import init_db, wait_for_db
from .routers import (
    analysis_runs,
    analyze,
    flags,
    health,
    projects,
    removals,
    reports,
    repositories,
    scans,
)
from .routers.settings import router as settings_router

settings = get_settings()

app = FastAPI(title="Feature Flag Lifecycle API",
              description="Backend for Feature-Flag-Lifecycle-Stale-Flag-Detection frontend. See /docs.",
              version="2.0.0")

origins = [o.strip() for o in settings.FRONTEND_ORIGIN.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins or ["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(projects.router)
app.include_router(repositories.router)
app.include_router(scans.router)
app.include_router(flags.router)
app.include_router(analyze.router)
app.include_router(analysis_runs.router)
app.include_router(removals.router)
app.include_router(reports.router)
app.include_router(settings_router)


@asynccontextmanager
async def lifespan(app: FastAPI):
    wait_for_db()  # backend waits until PostgreSQL/SQLite is reachable
    init_db()  # create_all is a no-op when Alembic already migrated; never destroys data
    # NOTE: no demo/seed records are inserted here. A fresh database stays empty
    # until real repositories are connected and scanned. Test fixtures live in
    # tests/fixtures.py and are never imported by production code.
    yield


app.router.lifespan_context = lifespan


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    # HTTPException keeps FastAPI's default handling; anything else becomes
    # structured JSON without leaking tracebacks to the frontend.
    if isinstance(exc, HTTPException):
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})
    return JSONResponse(status_code=500, content={"detail": f"internal server error: {type(exc).__name__}"})


@app.get("/", summary="Root")
def root():
    return {"name": "feature-flag-lifecycle-api", "docs": "/docs", "health": "/health"}
