"""Backend tests: real DB (temp sqlite), no faked tool successes."""
import os
import tempfile

import pytest
from fastapi.testclient import TestClient

tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
tmp.close()
os.environ["DATABASE_URL"] = f"sqlite:///{tmp.name}"

from app.database import SessionLocal, init_db  # noqa: E402
from app.main import app  # noqa: E402
from app.services import flagshark_service, piranha_service  # noqa: E402
from app.services.seed_service import seed_if_empty  # noqa: E402

init_db()
db = SessionLocal()
seed_if_empty(db)
db.close()

client = TestClient(app)


def test_health():
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"
    assert "flagshark" in r.json()["tools"]


def test_repositories_seeded():
    r = client.get("/api/repositories")
    assert r.status_code == 200
    assert len(r.json()) >= 5


def test_register_repository_validation():
    r = client.post("/api/repositories", json={"name": "bad", "local_path": "/nonexistent-xyz-123"})
    assert r.status_code == 400


def test_flags_and_stale():
    r = client.get("/api/flags")
    assert r.status_code == 200
    assert len(r.json()) >= 4
    r2 = client.get("/api/flags/stale")
    assert r2.status_code == 200
    assert all(f["status"] in ("stale", "potentially-stale") for f in r2.json())


def test_evidence_risk_flow():
    flags = client.get("/api/flags").json()
    fid = flags[0]["id"]
    assert client.get(f"/api/flags/{fid}/evidence").status_code == 200
    assert client.get(f"/api/flags/{fid}/code-paths").status_code == 200
    # risk may 404 until analyze; analyze must work without repo checkout too
    client.post(f"/api/flags/{fid}/analyze")


def test_tool_missing_handling():
    fs = flagshark_service.flagshark_status()
    assert "available" in fs and "hint" in fs
    ps = piranha_service.piranha_status()
    assert "available" in ps and "hint" in ps
    # removal without local checkout must error, never fake success
    flags = client.get("/api/flags").json()
    fid = flags[0]["id"]
    r = client.post(f"/api/flags/{fid}/remove",
                    json={"flag_id": fid, "target_branch": "main", "tool_target": "Piranha"})
    assert r.status_code in (400, 404, 500)


def test_scan_persistence_and_reports():
    assert client.get("/api/scans").status_code == 200
    assert client.get("/api/removals").status_code == 200
    assert client.get("/api/verifications").status_code == 200
    assert client.get("/api/reports").status_code == 200
    r = client.post("/api/reports", json={"title": "t", "type": "stale-summary"})
    assert r.status_code == 201
