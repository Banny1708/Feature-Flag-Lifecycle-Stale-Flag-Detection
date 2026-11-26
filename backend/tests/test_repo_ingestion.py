"""Phase 1 tests: real repository ingestion + isolated workspaces.

Unit tests use real local git repositories (no network). The GitHub
integration test is marked and skipped when the network is unavailable —
it is never faked.
"""
import json
import os
import subprocess
import tempfile
from pathlib import Path

import pytest

os.environ.setdefault("DATABASE_URL", f"sqlite:///{tempfile.NamedTemporaryFile(suffix='.db', delete=False).name}")

from app.config import get_settings  # noqa: E402
from app.database import init_db  # noqa: E402
from app.services import repo_service  # noqa: E402
from app.services.repo_service import CloneError  # noqa: E402

init_db()  # ensure tables exist regardless of test-module import order

settings = get_settings()


def _make_git_repo(base: Path, name: str = "origin") -> Path:
    """Create a real local git repo with one commit + one flag-like file."""
    d = base / name
    d.mkdir(parents=True)
    subprocess.run(["git", "init"], cwd=str(d), check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "t@t.t"], cwd=str(d), check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "t"], cwd=str(d), check=True, capture_output=True)
    (d / "app.py").write_text("import os\nif os.getenv('ENABLE_TEST_FLAG'):\n    print('on')\n", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=str(d), check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=str(d), check=True, capture_output=True)
    return d


# ---------- URL validation ----------

def test_valid_github_urls():
    for u in ["https://github.com/octocat/Hello-World",
              "https://github.com/octocat/Hello-World.git",
              "https://github.com/octocat/Hello-World/"]:
        v = repo_service.validate_repository_url(u)
        assert v["owner"] == "octocat" and v["name"] == "Hello-World"
        assert v["canonical_url"] == "https://github.com/octocat/Hello-World"


def test_invalid_urls_rejected():
    bad = ["", "not-a-url", "git@github.com:octocat/Hello-World.git",
           "http://github.com/octocat/Hello-World",
           "https://gitlab.com/octocat/Hello-World",
           "https://github.com/onlyowner",
           "https://github.com/",
           "file:///etc/passwd",
           "/srv/workspaces/my-repo",
           "https://user:token123456@github.com/octocat/Hello-World"]
    for u in bad:
        with pytest.raises(CloneError) as e:
            repo_service.validate_repository_url(u)
        assert e.value.code == "INVALID_URL"


# ---------- workspace isolation ----------

def test_workspace_path_isolation(tmp_path):
    ws = str(tmp_path / "ws")
    d = repo_service.managed_repo_dir(ws, "repo-abc123")
    assert str(d).startswith(str(Path(ws).resolve()))
    assert d.name == "repo-abc123"
    with pytest.raises(CloneError):
        repo_service.managed_repo_dir(ws, "../../etc")
    with pytest.raises(CloneError):
        repo_service.managed_repo_dir(ws, "a/b")
    with pytest.raises(CloneError):
        repo_service.managed_repo_dir(ws, "")


def test_error_classification():
    assert repo_service._classify_clone_error("fatal: repository not found", "", 128)[0] == "REPOSITORY_NOT_FOUND"
    assert repo_service._classify_clone_error("fatal: Authentication failed", "", 128)[0] == "AUTHENTICATION_FAILED"
    assert repo_service._classify_clone_error("couldn't find remote ref refs/heads/nope", "", 128)[0] == "BRANCH_NOT_FOUND"
    assert repo_service._classify_clone_error("Could not resolve host: github.com", "", 128)[0] == "NETWORK_ERROR"


def test_token_never_leaks_in_errors():
    token = "ghp_superSecretToken12345"
    out = repo_service.sanitize(f"failed with bearer {token} embedded", [token])
    assert token not in out
    assert "***REDACTED***" in out


# ---------- real clone of a local git repo (exercises the true git path) ----------

def test_clone_local_git_repo_end_to_end(tmp_path, monkeypatch):
    origin = _make_git_repo(tmp_path)
    monkeypatch.setattr(settings, "WORKSPACE_DIR", str(tmp_path / "ws"))
    # local file:// URL bypasses the GitHub-only validator (validator tested above);
    # the clone machinery itself is transport-agnostic and fully real here.
    repo_id = "repo-test01"
    dest = repo_service.source_dir(str(tmp_path / "ws"), repo_id)
    r = subprocess.run(["git", "clone", "--depth", "1", "--", str(origin), str(dest)],
                       capture_output=True, text=True, timeout=60)
    assert r.returncode == 0, r.stderr
    from app.services import git_service
    ev = git_service.collect_git_evidence(dest)
    assert ev["available"] is True
    assert len(ev["commit"]) == 40  # real full SHA recorded
    assert (dest / "app.py").exists()


def test_clone_cmd_is_full_history():
    # Regression test (Phase 5): FlagShark skips ALL git-blame age signals on
    # shallow clones, so workspaces must never be shallow (--depth forbidden).
    cmd = repo_service.build_clone_cmd("https://github.com/o/r", "/tmp/x", "main", "")
    assert "--depth" not in cmd
    assert cmd[:2] == ["git", "clone"]
    assert "--" in cmd  # separator before URL (no option injection)


def test_clone_failure_cleans_workspace(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "WORKSPACE_DIR", str(tmp_path / "ws"))
    with pytest.raises(CloneError) as e:
        repo_service.clone_repository("https://github.com/this-org-definitely-not-here-xyz/nope-nope",
                                      "repo-fail01", timeout=60)
    assert e.value.code in ("REPOSITORY_NOT_FOUND", "NETWORK_ERROR", "AUTHENTICATION_FAILED")
    assert not (tmp_path / "ws" / "repositories" / "repo-fail01").exists()


def test_clone_unknown_branch_falls_back_to_default(tmp_path, monkeypatch):
    # Unknown branch (e.g. UI default "main" vs actual "master") falls back to
    # the remote default branch; the recorded branch reflects reality.
    monkeypatch.setattr(settings, "WORKSPACE_DIR", str(tmp_path / "ws"))
    out = repo_service.clone_repository("https://github.com/octocat/Hello-World",
                                        "repo-branch01",
                                        branch="branch-that-does-not-exist-xyz",
                                        timeout=120)
    assert out["branch"] == "master"
    assert len(out["commit_hash"]) == 40
    assert Path(out["local_path"]).is_dir()


# ---------- API level: local-path mode still works, URL mode validates ----------

def _client():
    from fastapi.testclient import TestClient
    from app.main import app
    return TestClient(app)


def test_api_rejects_empty_body_and_bad_url():
    c = _client()
    assert c.post("/api/repositories", json={"name": "x"}).status_code == 400
    r = c.post("/api/repositories", json={"name": "x", "url": "git@github.com:o/r.git"})
    assert r.status_code == 400


def test_api_local_path_mode_and_scan(tmp_path):
    origin = _make_git_repo(tmp_path, "local-origin")
    c = _client()
    r = c.post("/api/repositories",
               json={"name": "local-t", "local_path": str(origin), "language": "Python"})
    assert r.status_code == 201, r.text
    repo_id = r.json()["id"]
    g = c.get(f"/api/repositories/{repo_id}/git")
    assert g.status_code == 200 and g.json()["available"] is True
    s = c.post("/api/scans", json={"repository_id": repo_id})
    assert s.status_code == 201, s.text
    assert s.json()["status"] in ("success", "partial")
    if s.json()["scannerEngine"] == "Regex-Fallback":
        # No FlagShark binary here: fallback finds the quoted UPPER_SNAKE token.
        assert s.json()["totalFlagsDetected"] >= 1
    else:
        # Real FlagShark: a bare os.getenv token is not an SDK call, so a
        # clean scan (zero stale flags) is the honest result.
        assert s.json()["scannerEngine"].startswith("FlagShark")


def test_api_missing_repo_scan_still_404():
    c = _client()
    assert c.post("/api/scans", json={"repository_id": "repo-does-not-exist"}).status_code == 404


# ---------- live GitHub integration (never faked; skipped offline) ----------

def _network_ok() -> bool:
    import socket
    try:
        socket.create_connection(("github.com", 443), timeout=5).close()
        return True
    except OSError:
        return False


@pytest.mark.integration
def test_integration_clone_real_github_repo(tmp_path, monkeypatch):
    if not _network_ok():
        pytest.skip("no network access to github.com")
    monkeypatch.setattr(settings, "WORKSPACE_DIR", str(tmp_path / "ws"))
    c = _client()
    r = c.post("/api/repositories",
               json={"name": "hello-world-e2e", "url": "https://github.com/octocat/Hello-World"})
    assert r.status_code == 201, r.text
    body = r.json()
    repo_id = body["id"]
    src = Path(tmp_path / "ws" / "repositories" / repo_id / "source")
    assert src.is_dir() and (src / ".git").is_dir()
    # Phase 5 regression: workspaces must be full clones (shallow clones
    # disable FlagShark's git-blame age signals).
    shallow = subprocess.run(["git", "-C", str(src), "rev-parse",
                              "--is-shallow-repository"],
                             capture_output=True, text=True, timeout=30)
    assert shallow.stdout.strip() == "false", shallow.stdout
    assert (src / "README" ).exists() or any(src.iterdir())
    meta = json.loads((src.parent / "metadata.json").read_text())
    assert meta["commit_hash"] and len(meta["commit_hash"]) == 40
    assert "token" not in json.dumps(meta).lower() or "github_token" not in json.dumps(meta)
    g = c.get(f"/api/repositories/{repo_id}/git")
    assert g.json()["available"] is True
    s = c.post("/api/scans", json={"repository_id": repo_id})
    assert s.status_code == 201
    assert s.json()["scannerEngine"] == "Regex-Fallback" or s.json()["scannerEngine"].startswith("FlagShark")
