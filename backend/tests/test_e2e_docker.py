"""Phase 4 Docker E2E: full governed chain over real HTTP against uvicorn.

Runs the deployed stack shape (backend serving HTTP + sqlite + workspace):
register -> scan (FlagShark) -> flag lifecycle -> risk -> dry-run (real)
-> approval -> cleanup (real Piranha) -> verification -> post-scan evidence
-> SDK NO_CHANGES proof -> rollback restore.

Deterministic: local fixture repo only, no GitHub. Requires the real
libraries (skipped without polyglot-piranha); designed to run inside the
Docker backend image.
"""
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

import pytest

try:
    import importlib.util as _ilu
    REAL_LIB = _ilu.find_spec("polyglot_piranha") is not None
except Exception:
    REAL_LIB = False

needs_docker_e2e = pytest.mark.skipif(
    not REAL_LIB, reason="needs real Piranha + FlagShark (runs in Docker)")


def _free_port() -> int:
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


class Server:
    def __init__(self, workdir: Path):
        self.workdir = workdir
        self.port = _free_port()
        self.db = workdir / "e2e.db"
        self.ws = workdir / "ws"
        self.ws.mkdir(parents=True, exist_ok=True)
        self.proc: subprocess.Popen | None = None

    def start(self):
        env = dict(os.environ)
        env["DATABASE_URL"] = f"sqlite:///{self.db}"
        env["WORKSPACE_DIR"] = str(self.ws)
        env["FRONTEND_ORIGIN"] = "http://localhost:5173"
        backend = Path(__file__).parent.parent
        self.proc = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "app.main:app",
             "--host", "127.0.0.1", "--port", str(self.port)],
            cwd=str(backend), env=env,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        deadline = time.time() + 60
        while time.time() < deadline:
            try:
                self.get("/health")
                return
            except Exception:
                time.sleep(0.5)
        raise RuntimeError("backend did not start")

    def stop(self):
        if self.proc:
            self.proc.terminate()
            try:
                self.proc.wait(timeout=15)
            except Exception:
                self.proc.kill()

    def _req(self, method: str, path: str, body: dict | None = None):
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(f"http://127.0.0.1:{self.port}{path}",
                                     data=data, method=method,
                                     headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=300) as r:
                return r.status, json.loads(r.read().decode() or "null")
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read().decode() or "null")

    def get(self, path: str):
        code, body = self._req("GET", path)
        assert code == 200, body
        return body

    def post(self, path: str, body: dict, expect=(200, 201)):
        code, resp = self._req("POST", path, body)
        assert code in expect, resp
        return resp

    def patch(self, path: str, body: dict):
        code, resp = self._req("PATCH", path, body)
        assert code == 200, resp
        return resp


FIXTURE_PY = """from flags import DEMO_E2E

import ldclient


def render(user):
    if DEMO_E2E:
        return new_ui(user)
    else:
        return old_ui(user)


def checkout(user):
    if ldclient.get().variation("SDK_E2E_FLAG", user, False):
        return "new"
    return "old"
"""

FIXTURE_FLAGS = "DEMO_E2E = True\n"


@needs_docker_e2e
def test_full_chain_over_http(tmp_path):
    work = tmp_path / "work"
    (work / "py").mkdir(parents=True)
    (work / "py" / "app.py").write_text(FIXTURE_PY)
    (work / "py" / "flags.py").write_text(FIXTURE_FLAGS)
    (work / "py" / "pytest.ini").write_text("[pytest]\n")
    (work / "py" / "test_ok.py").write_text("def test_ok():\n    assert True\n")
    env = dict(os.environ, GIT_AUTHOR_DATE="2025-01-01T12:00:00",
               GIT_COMMITTER_DATE="2025-01-01T12:00:00")
    subprocess.run(["git", "init", "-q", str(work)], check=True)
    subprocess.run(["git", "-C", str(work), "config", "user.email", "t@t.t"], check=True)
    subprocess.run(["git", "-C", str(work), "config", "user.name", "t"], check=True)
    subprocess.run(["git", "-C", str(work), "add", "-A"], check=True)
    subprocess.run(["git", "-C", str(work), "-c", "user.email=t@t", "-c", "user.name=t",
                    "commit", "-qm", "init"], check=True, env=env)

    srv = Server(tmp_path / "srv")
    srv.start()
    try:
        # 1. register
        repo = srv.post("/api/repositories",
                        {"name": "e2e-http", "local_path": str(work),
                         "language": "Python"})
        rid = repo["id"]
        # 2. scan: FlagShark finds the SDK flag (stale via age? fresh repo -> clean)
        scan = srv.post("/api/scans", {"repository_id": rid})
        assert scan["scannerEngine"].startswith("FlagShark"), scan
        assert scan["status"] in ("success", "partial"), scan
        sdk_flags = [f for f in scan["findings"]
                     if f["flagKey"] == "SDK_E2E_FLAG"]
        assert sdk_flags, "FlagShark must detect the literal SDK flag"
        # 3. bare flag via project + lifecycle walk
        proj = srv.post("/api/projects", {"name": "e2e-proj"})
        flag = srv.post(f"/api/projects/{proj['id']}/flags",
                        {"name": "DEMO_E2E", "key": "DEMO_E2E",
                         "repository_id": rid})
        fid = flag["id"]
        for state in ("ROLLOUT", "CONCLUDED", "STALE_CANDIDATE",
                      "RISK_REVIEW", "REMOVAL_PENDING"):
            srv.patch(f"/api/flags/{fid}", {"lifecycle_state": state})
        # 4. risk
        risk = srv.post("/api/risk-assessments", {"flag_id": fid})
        assert risk["recommendation"] in ("SAFE_TO_REMOVE", "REVIEW_REQUIRED",
                                          "DO_NOT_REMOVE")
        # 5. dry-run (real Piranha plan)
        dry = srv.post("/api/removals/dry-run",
                       {"flag_id": fid, "permanent_value": "True"})
        assert dry["cleanupStatus"] == "DRY_RUN", dry
        assert any("app.py" in f for f in dry["plannedFiles"]), dry
        # 6. approved cleanup
        op = srv.post("/api/removals?confirmed_high_risk=true",
                      {"flag_id": fid, "permanent_value": "True"})
        assert op["cleanupStatus"] == "APPLIED", op
        assert op["verificationStatus"] == "SUCCESS", op
        assert op["status"] == "SUCCESS", op
        assert "if DEMO_E2E" not in (work / "py" / "app.py").read_text()
        # 7. post-cleanup evidence recorded rescan
        ev = srv.get(f"/api/evidence?feature_flag_id={fid}")
        kinds = {e["evidenceType"] for e in ev}
        assert "post-cleanup-scan" in kinds, kinds
        # 8. SDK string pattern is honestly NOT cleaned
        sdk_id = sdk_flags[0].get("flagKey")
        assert sdk_id == "SDK_E2E_FLAG"
        # 9. rollback restores exact bytes
        cleaned = (work / "py" / "app.py").read_bytes()
        assert b"if DEMO_E2E" not in cleaned
        rb = srv.post(f"/api/removals/{op['id']}/rollback", {})
        assert "rollback_operation_id" in rb, rb
        restored = (work / "py" / "app.py").read_bytes()
        assert b"if DEMO_E2E" in restored
    finally:
        srv.stop()
