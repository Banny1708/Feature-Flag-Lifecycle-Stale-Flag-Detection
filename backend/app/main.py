from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import get_settings
from .database import init_db
from .routers import analyze, flags, health, removals, reports, repositories, scans
from .services.seed_service import seed_if_empty
from .database import SessionLocal

settings = get_settings()

app = FastAPI(title="Feature Flag Lifecycle API",
              description="Backend for Feature-Flag-Lifecycle-Stale-Flag-Detection frontend. See /docs.",
              version="1.0.0")

origins = [o.strip() for o in settings.FRONTEND_ORIGIN.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins or ["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(repositories.router)
app.include_router(scans.router)
app.include_router(flags.router)
app.include_router(analyze.router)
app.include_router(removals.router)
app.include_router(reports.router)


from contextlib import asynccontextmanager


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    db = SessionLocal()
    try:
        seed_if_empty(db)
    finally:
        db.close()
    yield


app.router.lifespan_context = lifespan


@app.get("/", summary="Root")
def root():
    return {"name": "feature-flag-lifecycle-api", "docs": "/docs", "health": "/api/health"}
