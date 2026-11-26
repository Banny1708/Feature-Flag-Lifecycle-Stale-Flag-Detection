"""Phase 4 security regression: credentials, traversal, injection, safety.

No test here performs destructive actions outside tmp dirs. All subprocess
use goes through argument arrays (asserted structurally, not just by trust).
"""
import os
import subprocess
import tempfile
from pathlib import Path

import pytest

os.environ.setdefault("DATABASE_URL", f"sqlite:///{tempfile.NamedTemporaryFile(suffix='.db', delete=False).name}")

from app.database import init_db  # noqa: E402
from app.services import piranha_service as ps  # noqa: E402
from app.services import repo_service  # noqa: E402
from app.services.repo_service import CloneError  # noqa: E402

init_db()


def _git_repo(base: Path, name: str = "r") -> Path:
    d = base / name
    d.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "-q", str(d)], check=True)
    subprocess.run(["git", "-C", str(d), "config", "user.email", "t@t.t"], check=True)
    subprocess.run(["git", "-C", str(d), "config", "user.name", "t"], check=True)
    (d / "a.py").write_text("x = 1\n")
    subprocess.run(["git", "-C", str(d), "add", "-A"], check=True)
    subprocess.run(["git", "-C", str(d), "-c", "user.email=t@t", "-c", "user.name=t",
                    "commit", "-qm", "init"], check=True)
    return d


# ---------- credentials ----------

def test_sanitize_redacts_tokens():
    token = "ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZ123456"
    dirty = f"fatal: Authentication failed for {token} and bearer {token}"
    clean = repo_service.sanitize(dirty, [token])
    assert token not in clean
    assert clean.count("***REDACTED***") >= 1


def test_clone_error_never_contains_token(tmp_path, monkeypatch):
    from app import config as config_mod
    monkeypatch.setattr(config_mod.get_settings(), "WORKSPACE_DIR", str(tmp_path / "ws"))
    token = "ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZ123456"
    with pytest.raises(CloneError) as e:
        repo_service.clone_repository(
            "https://github.com/this-org-definitely-not-here-xyz/nope-nope",
            "repo-sec01", access_token=token, timeout=60)
    assert token not in str(e.value) and token not in e.value.message


def test_no_shell_true_anywhere():
    import ast
    root = Path(__file__).parent.parent / "app"
    offenders = []
    for p in root.rglob("*.py"):
        tree = ast.parse(p.read_text(encoding="utf-8", errors="ignore"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                for kw in node.keywords:
                    if kw.arg == "shell" and isinstance(kw.value, ast.Constant) and kw.value.value:
                        offenders.append(f"{p.name}:{node.lineno}")
            if isinstance(node, ast.Attribute) and node.attr == "system":
                if isinstance(node.value, ast.Name) and node.value.id == "os":
                    offenders.append(f"{p.name}:{node.lineno}")
    assert not offenders, offenders


# ---------- workspace traversal / path escape ----------

def test_managed_workspace_traversal_rejected(tmp_path):
    ws = str(tmp_path / "ws")
    with pytest.raises(CloneError):
        repo_service.managed_repo_dir(ws, "../../etc")
    with pytest.raises(CloneError):
        repo_service.managed_repo_dir(ws, "a/b")
    with pytest.raises(CloneError):
        repo_service.managed_repo_dir(ws, "")
    ok = repo_service.managed_repo_dir(ws, "repo-abc123")
    assert str(ok).startswith(str(Path(ws).resolve()))


def test_flagshark_paths_cannot_escape_repo(tmp_path):
    from app.services import flagshark_service as fs
    repo = tmp_path / "r"
    repo.mkdir()
    with pytest.raises(fs.FlagSharkOutputError):
        fs.relativize_path(repo, "/etc/passwd")
    with pytest.raises(fs.FlagSharkOutputError):
        fs.relativize_path(repo, "../../etc/passwd")
    assert fs.relativize_path(repo, "a/b.py") == "a/b.py"


def test_verify_python_syntax_rejects_escape(tmp_path):
    fails = ps.verify_python_syntax(["../../etc/x.py"], tmp_path)
    assert fails and any("escapes" in f for f in fails)


# ---------- dirty repository ----------

# Dirty-worktree refusal is covered by test_piranha.py::test_flow_refuses_dirty_worktree.
def test_tracked_clean_ignores_untracked_files(tmp_path):
    from app.services import git_service
    d = _git_repo(tmp_path)
    assert git_service.tracked_clean(d) is True
    (d / "__pycache__").mkdir()
    (d / "__pycache__" / "x.pyc").write_text("junk")
    assert git_service.tracked_clean(d) is True
    (d / "a.py").write_text("modified\n")
    assert git_service.tracked_clean(d) is False


# ---------- command injection ----------

def test_malicious_flag_key_never_reaches_shell(tmp_path, monkeypatch):
    from app.utils.subprocess_util import CmdResult
    import app.services.piranha_service as mod
    seen: list = []

    def fake_run(args, cwd=None, timeout=120):
        seen.append(args)
        return CmdResult(2, "", "boom", False)

    monkeypatch.setattr(mod, "run_cmd", fake_run)
    cfg = mod.build_config("python", 'X"; rm -rf /tmp/pwned; echo "', "True", dry_run=True)
    with pytest.raises(mod.PiranhaError):
        mod.run_cleanup(tmp_path, cfg)
    # argv arrays only: attacker string travels as one inert list element
    assert seen and all(isinstance(call, list) for call in seen)
    flat = " ".join(str(a) for call in seen for a in call)
    assert "rm -rf" not in flat.replace('X"; rm -rf /tmp/pwned; echo "', "")


def test_malicious_repo_filenames_handled(tmp_path):
    pytest.importorskip("polyglot_piranha")
    d = _git_repo(tmp_path)
    evil = d / "we;ird $(name).py"
    evil.write_text("if EVIL_INJECT_FLAG:\n    x = 1\n")
    subprocess.run(["git", "-C", str(d), "add", "-A"], check=True)
    subprocess.run(["git", "-C", str(d), "-c", "user.email=t@t", "-c", "user.name=t",
                    "commit", "-qm", "evil"], check=True)
    results, _stats = __import__("app.services.provider_service",
                                 fromlist=["detect_provider_references"]).detect_provider_references(d)
    assert isinstance(results, list)  # completes without shell interpretation


# ---------- tool output with credentials ----------

def test_runner_never_echoes_arguments():
    # The runner's only stdout is the summaries JSON; the args file (which
    # carries substitutions) is read, never printed.
    import app.services.piranha_runner as runner
    import inspect
    src = inspect.getsource(runner)
    prints = [ln.strip() for ln in src.splitlines() if ln.strip().startswith("print(")]
    assert prints, "runner must report errors, but only to stderr"
    assert all("stderr" in ln for ln in prints), prints
    assert src.count("json.dump(payload") == 1
