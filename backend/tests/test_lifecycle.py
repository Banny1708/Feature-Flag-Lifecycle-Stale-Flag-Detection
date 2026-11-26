"""Lifecycle, detection, risk, dry-run, rollback tests (real DB, no faked tool results)."""
import os
import subprocess
import tempfile
from pathlib import Path

_tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
_tmp.close()
os.environ.setdefault("DATABASE_URL", f"sqlite:///{_tmp.name}")

from app.database import SessionLocal, init_db  # noqa: E402
from app.main import app  # noqa: E402
from tests.fixtures import seed_if_empty  # noqa: E402  (test-only fixtures)

init_db()
_db = SessionLocal()
seed_if_empty(_db)
_db.close()

from fastapi.testclient import TestClient  # noqa: E402

client = TestClient(app)

PROJ = {}


def test_health_probes():
    assert client.get("/health").status_code == 200
    r = client.get("/health/db")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_project_crud():
    r = client.post("/api/projects", json={"name": "capstone-test", "description": "t"})
    assert r.status_code == 201
    PROJ["id"] = r.json()["id"]
    assert client.get(f"/api/projects/{PROJ['id']}").status_code == 200
    assert any(p["id"] == PROJ["id"] for p in client.get("/api/projects").json())


def test_flag_lifecycle_valid_and_invalid():
    pid = PROJ["id"]
    r = client.post(f"/api/projects/{pid}/flags",
                    json={"name": "F1", "key": "LC_FLAG_1", "owner": "tester"})
    assert r.status_code == 201
    assert r.json()["repositoryId"] == ""  # project-scoped flag: no repo link, still valid
    fid = r.json()["id"]
    # unknown repository is rejected, not a 500
    assert client.post(f"/api/projects/{pid}/flags",
                       json={"name": "F1c", "key": "LC_FLAG_1C",
                             "repository_id": "repo-does-not-exist"}).status_code == 422
    # duplicate key in project -> 409
    assert client.post(f"/api/projects/{pid}/flags",
                       json={"name": "F1b", "key": "LC_FLAG_1"}).status_code == 409
    # invalid jump ACTIVE -> REMOVED rejected
    bad = client.patch(f"/api/flags/{fid}", json={"lifecycle_state": "REMOVED"})
    assert bad.status_code == 422
    # valid step ACTIVE -> ROLLOUT
    ok = client.patch(f"/api/flags/{fid}", json={"lifecycle_state": "ROLLOUT"})
    assert ok.status_code == 200
    assert ok.json()["status"] == "active"  # UI status stays compatible
    # unknown state rejected
    assert client.patch(f"/api/flags/{fid}", json={"lifecycle_state": "NOPE"}).status_code == 422
    PROJ["flag"] = fid


def test_evaluations_recorded():
    fid = PROJ["flag"]
    r = client.post(f"/api/flags/{fid}/evaluations",
                    json={"environment": "production", "evaluation_count": 10,
                          "enabled_count": 10, "disabled_count": 0,
                          "last_evaluated_at": "2026-09-01T00:00:00Z",
                          "evaluation_frequency": "low"})
    assert r.status_code == 201
    assert len(client.get(f"/api/flags/{fid}/evaluations").json()) >= 1


def test_detection_rejected_without_evidence():
    pid = PROJ["id"]
    r = client.post(f"/api/projects/{pid}/flags", json={"name": "Ghost", "key": "GHOST_FLAG_X"})
    ghost = r.json()["id"]
    run = client.post("/api/analysis/run",
                      json={"project_id": pid, "analysis_type": "STALE_DETECTION"}).json()
    assert run["status"] == "COMPLETED"
    dets = {d["featureFlagId"]: d for d in
            client.get("/api/detection-results", params={"analysis_run_id": run["id"]}).json()}
    assert dets[ghost]["detectionStatus"] == "REJECTED"  # no evidence -> never STALE
    PROJ["run"] = run["id"]


def test_detection_stale_candidate_and_untested():
    # seeded DEPRECATED_STRIPE_WEBHOOK: 180d inactive, 100% rollout, 0 evals
    flags = client.get("/api/flags", params={"searchQuery": "DEPRECATED_STRIPE_WEBHOOK"}).json()
    assert flags, "seed flag missing"
    run = client.post("/api/analysis/run",
                      json={"analysis_type": "FULL_ANALYSIS"}).json()
    assert run["status"] == "COMPLETED"
    assert run["untestedPaths"] >= 1
    dets = client.get("/api/detection-results", params={"analysis_run_id": run["id"]}).json()
    by_flag = {d["featureFlagId"]: d for d in dets}
    hit = by_flag.get(flags[0]["id"])
    assert hit and hit["detectionStatus"] in ("STALE", "CANDIDATE")
    assert hit["staleScore"] >= 35 and hit["reason"]
    unp = client.get("/api/untested-paths", params={"analysis_run_id": run["id"]}).json()
    assert any(u["featureFlagId"] == flags[0]["id"] for u in unp)


def test_risk_recommendation_and_history():
    flags = client.get("/api/flags", params={"searchQuery": "LEGACY_OAUTH"}).json()
    fid = flags[0]["id"]
    r = client.post("/api/risk-assessments", json={"flag_id": fid})
    assert r.status_code == 201
    body = r.json()
    assert body["riskLevel"] in ("LOW", "MEDIUM", "HIGH", "CRITICAL")
    assert body["recommendation"] in ("SAFE_TO_REMOVE", "REVIEW_REQUIRED", "DO_NOT_REMOVE")
    hist = client.get(f"/api/flags/{fid}/history").json()
    assert any(h["action"] == "RISK_ASSESSED" for h in hist)
    assert client.get("/api/audit-logs", params={"feature_flag_id": fid}).status_code == 200
    assert client.get("/api/evidence", params={"feature_flag_id": fid}).status_code == 200


def test_dry_run_changes_nothing():
    fid = PROJ["flag"]
    r = client.post("/api/removals/dry-run", json={"flag_id": fid, "permanent_value": "false"})
    assert r.status_code == 200
    body = r.json()
    assert "plannedFiles" in body
    assert body["operationType"] == "DRY_RUN"
    assert body["status"] == "SUCCESS"


def test_approved_removal_refused_without_piranha():
    # HIGH/CRITICAL or missing tooling must never silently succeed
    fid = PROJ["flag"]
    r = client.post("/api/removals", json={"flag_id": fid})
    assert r.status_code == 422  # no risk assessment yet for this flag
    flags = client.get("/api/flags", params={"searchQuery": "LEGACY_OAUTH"}).json()
    r2 = client.post("/api/removals", json={"flag_id": flags[0]["id"]})
    # 400 (no local checkout) / 422 (risk or lifecycle guard) / 500 (tool failure):
    # all prove the API never silently succeeds.
    assert r2.status_code in (400, 422, 500)
    ops = client.get("/api/removals").json()
    assert not [o for o in ops
                if o["flagId"] in (fid, flags[0]["id"]) and o["status"] == "SUCCESS"
                and o.get("operationType") == "REMOVE"]


def test_rollback_restores_safety_branch():
    tmp = Path(tempfile.mkdtemp(prefix="ffsd-rb-"))
    (tmp / "f.txt").write_text("v1")
    subprocess.run(["git", "init", "-q", str(tmp)], check=True)
    subprocess.run(["git", "-C", str(tmp), "add", "-A"], check=True)
    subprocess.run(["git", "-C", str(tmp), "-c", "user.email=t@t", "-c", "user.name=t",
                    "commit", "-qm", "init"], check=True)
    subprocess.run(["git", "-C", str(tmp), "checkout", "-qb", "ffsd-safety-demo"], check=True)
    subprocess.run(["git", "-C", str(tmp), "checkout", "-q", "master"], check=True)
    (tmp / "f.txt").write_text("v2-removed")
    subprocess.run(["git", "-C", str(tmp), "-c", "user.email=t@t", "-c", "user.name=t",
                    "commit", "-qam", "removal"], check=True)

    repo = client.post("/api/repositories",
                       json={"name": "rb-repo", "local_path": str(tmp)}).json()
    flag = client.post(f"/api/projects/{PROJ['id']}/flags",
                       json={"name": "RB", "key": "RB_FLAG",
                             "repository_id": repo["id"]}).json()
    # fabricate a completed REMOVE op with a real safety branch (simulates post-removal state)
    from app.database import SessionLocal
    from app.models.models import RemovalOperation
    db = SessionLocal()
    db.add(RemovalOperation(id="op-rb-test", flag_id=flag["id"], flag_name="RB_FLAG",
                            repository_id=repo["id"], repository_name="rb-repo",
                            status="SUCCESS", tool_target="Piranha",
                            safety_branch="ffsd-safety-demo", base_commit="init"))
    db.commit()
    db.close()
    r = client.post("/api/removals/op-rb-test/rollback")
    assert r.status_code == 200
    assert (tmp / "f.txt").read_text() == "v1"  # genuinely restored
    assert r.json()["restored_branch"] == "ffsd-safety-demo"
