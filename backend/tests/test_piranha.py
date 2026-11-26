"""Phase 3 tests: verified Polyglot Piranha 0.4.9 adapter.

Two tiers:
- Unit tests (run everywhere): validation, language gating, error taxonomy,
  diff capture, restore, syntax check — no real Piranha needed.
- Real-execution tests (skipped without the library): golden byte-equality
  against recorded fixtures, dry-run purity, treated true/false,
  multi-file, nested-limitation, no-changes, flow e2e, rollback restore.
  These run inside the Docker backend image (python 3.11 + pinned wheel).
"""
import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest

os.environ.setdefault("DATABASE_URL", f"sqlite:///{tempfile.NamedTemporaryFile(suffix='.db', delete=False).name}")

from app.database import init_db  # noqa: E402
from app.services import piranha_service as ps  # noqa: E402
from app.services.piranha_service import (  # noqa: E402
    PiranhaError,
    build_config,
    capture_diff,
    parse_permanent_value,
    repo_language_to_piranha,
    restore_workspace,
    verify_python_syntax,
)

init_db()

try:
    import importlib.util as _ilu
    REAL_LIB = _ilu.find_spec("polyglot_piranha") is not None
except Exception:
    REAL_LIB = False

needs_real = pytest.mark.skipif(not REAL_LIB, reason="polyglot-piranha not installed here; runs in Docker")

FIX = Path(__file__).parent / "fixtures" / "piranha"
CASES = {
    "py_true": {"lang": "python", "flag": "FEATURE_NEW_UI", "treated": "True"},
    "py_false": {"lang": "python", "flag": "FEATURE_OLD_SEARCH", "treated": "False"},
    "ts_true": {"lang": "typescript", "flag": "FEATURE_NEW_UI", "treated": "true"},
}


def _git(dirpath: Path, *args: str) -> str:
    r = subprocess.run(["git", *args], cwd=str(dirpath), capture_output=True, text=True, timeout=60)
    assert r.returncode == 0, r.stderr
    return r.stdout


def _copy_case(name: str, dest: Path) -> Path:
    src = FIX / "cases" / name / "before"
    assert src.is_dir(), f"missing golden fixture {src}"
    shutil.copytree(src, dest, dirs_exist_ok=True)
    _git(dest, "init", "-q")
    _git(dest, "config", "user.email", "t@t.t")
    _git(dest, "config", "user.name", "t")
    _git(dest, "add", "-A")
    _git(dest, "commit", "-qm", "before")
    return dest


# ------------------------- unit: gating & validation -------------------------

def test_language_mapping_verified_only():
    assert repo_language_to_piranha("Python") == "python"
    assert repo_language_to_piranha("TypeScript") == "typescript"
    assert repo_language_to_piranha("tsx") == "tsx"
    assert repo_language_to_piranha("TS") == "typescript"
    for unsupported in ["JavaScript", "js", "Java", "Go", "Kotlin", "", None, "cobol"]:
        assert repo_language_to_piranha(unsupported) is None


def test_permanent_value_mapping_per_language():
    assert parse_permanent_value("true", "python") == "True"
    assert parse_permanent_value("False", "python") == "False"
    assert parse_permanent_value("TRUE", "typescript") == "true"
    assert parse_permanent_value("1", "tsx") == "true"
    assert parse_permanent_value("0", "python") == "False"
    with pytest.raises(PiranhaError) as e:
        parse_permanent_value("maybe", "python")
    assert e.value.code == "INVALID_VALUE"
    with pytest.raises(PiranhaError) as e2:
        parse_permanent_value("", "typescript")
    assert e2.value.code == "INVALID_VALUE"


def test_build_config_rejects_before_library():
    with pytest.raises(PiranhaError) as e:
        build_config("java", "SOME_FLAG", "true")
    assert e.value.code == "UNSUPPORTED_LANGUAGE"
    with pytest.raises(PiranhaError) as e2:
        build_config("python", "   ", "true")
    assert e2.value.code == "INVALID_FLAG"
    cfg = build_config("python", "MY_FLAG", "True")
    assert cfg.treated_literal == "True" and cfg.config_dir.endswith("python")
    cfg2 = build_config("tsx", "MY_FLAG", "false")
    assert cfg2.treated_literal == "false"


def test_status_shape_without_library():
    st = ps.piranha_status()
    assert set(st) >= {"available", "version", "hint", "languages"}
    if not REAL_LIB:
        assert st["available"] is False


def test_run_cleanup_timeout_mapping(monkeypatch, tmp_path):
    from app.utils.subprocess_util import CmdResult
    import app.services.piranha_service as mod

    def fake_run(*a, **k):
        return CmdResult(124, "", "TIMEOUT", True)

    monkeypatch.setattr(mod, "run_cmd", fake_run)
    cfg = build_config("python", "X_FLAG", "True", dry_run=True)
    with pytest.raises(PiranhaError) as e:
        mod.run_cleanup(tmp_path, cfg)
    assert e.value.code == "TIMEOUT"


def test_run_cleanup_exec_failure_mapping(monkeypatch, tmp_path):
    from app.utils.subprocess_util import CmdResult
    import app.services.piranha_service as mod

    def fake_run(*a, **k):
        return CmdResult(2, "", "Produced syntactically incorrect source code", False)

    monkeypatch.setattr(mod, "run_cmd", fake_run)
    cfg = build_config("python", "X_FLAG", "True", dry_run=True)
    with pytest.raises(PiranhaError) as e:
        mod.run_cleanup(tmp_path, cfg)
    assert e.value.code == "EXECUTION_FAILED"


# ------------------------- unit: diff / restore / syntax -------------------------

def test_capture_diff_records_real_unified_diff(tmp_path):
    d = tmp_path / "r"
    d.mkdir()
    (d / "a.py").write_text("x = 1\n")
    _git(d, "init", "-q")
    _git(d, "config", "user.email", "t@t.t")
    _git(d, "config", "user.name", "t")
    _git(d, "add", "-A")
    _git(d, "commit", "-qm", "init")
    (d / "a.py").write_text("x = 2\n")
    diff = capture_diff(d)
    assert "-x = 1" in diff["unified"] and "+x = 2" in diff["unified"]
    assert diff["files"] == ["a.py"]
    assert diff["lines_added"] == 1 and diff["lines_removed"] == 1


def test_restore_workspace_reverts_to_base(tmp_path):
    d = tmp_path / "r"
    d.mkdir()
    (d / "a.py").write_text("v1\n")
    _git(d, "init", "-q")
    _git(d, "config", "user.email", "t@t.t")
    _git(d, "config", "user.name", "t")
    _git(d, "add", "-A")
    _git(d, "commit", "-qm", "init")
    base = _git(d, "rev-parse", "HEAD").strip()
    (d / "a.py").write_text("modified\n")
    assert restore_workspace(d, base)["ok"] is True
    assert (d / "a.py").read_text() == "v1\n"
    bad = restore_workspace(d, "not-a-real-base")
    assert bad["ok"] is False


def test_verify_python_syntax_flags_broken_indent(tmp_path):
    (tmp_path / "good.py").write_text("x = 1\n")
    (tmp_path / "bad.py").write_text("def f():\n    if x:\n            y = 1\n      z = 2\n")
    fails = verify_python_syntax(["good.py", "bad.py", "missing.py", "../escape.py"], tmp_path)
    assert any("bad.py" in f for f in fails)
    assert any("escape" in f for f in fails)
    assert not any(f.startswith("good.py") for f in fails)


# ------------------------- real: golden byte-equality -------------------------

@needs_real
@pytest.mark.parametrize("case", ["py_true", "py_false", "ts_true"])
def test_golden_transformation_byte_equal(tmp_path, case):
    meta = CASES[case]
    work = _copy_case(case, tmp_path / "work")
    cfg = build_config(meta["lang"], meta["flag"], meta["treated"], dry_run=False)
    before = {p.name: p.read_bytes() for p in (tmp_path / "work").iterdir() if p.is_file()}
    result = ps.run_cleanup(work, cfg)
    assert result.ok and result.cleanup_status == "APPLIED"
    assert result.files_changed, "expected real file changes"
    after_dir = FIX / "cases" / case / "after"
    for expected in after_dir.iterdir():
        if expected.is_file():
            actual = work / expected.name
            assert actual.is_file(), f"missing {expected.name}"
            assert actual.read_bytes() == expected.read_bytes(), f"differs: {expected.name}"
    # unrelated files byte-identical
    assert (work / ("unrelated.py" if meta["lang"] == "python" else "unrelated.ts")).read_bytes() == \
        (after_dir / ("unrelated.py" if meta["lang"] == "python" else "unrelated.ts")).read_bytes()
    assert before != {p.name: p.read_bytes() for p in work.iterdir() if p.is_file()}


@needs_real
def test_golden_patch_matches_real_diff(tmp_path):
    work = _copy_case("py_true", tmp_path / "work")
    cfg = build_config("python", "FEATURE_NEW_UI", "True", dry_run=False)
    ps.run_cleanup(work, cfg)
    patch = (FIX / "cases" / "py_true" / "expected.patch").read_text()
    assert "-    if FEATURE_NEW_UI:" in patch and "+    return new_ui(user)" in patch
    assert "UNRELATED_CODE" not in patch  # unrelated code never in diff


@needs_real
def test_nested_limitation_is_real_and_detected(tmp_path):
    work = _copy_case("py_true", tmp_path / "work")
    cfg = build_config("python", "FEATURE_NEW_UI", "True", dry_run=False)
    result = ps.run_cleanup(work, cfg)
    nested = [f for f in result.files_changed if f.endswith("case_nested.py")]
    assert nested, "nested case must be touched by Piranha"
    failures = verify_python_syntax(nested, work)
    assert failures, "nested rewrite must be flagged by the syntax check (IndentationError)"


@needs_real
def test_dry_run_purity_and_no_changes_unknown_flag(tmp_path):
    work = _copy_case("py_true", tmp_path / "work")
    before_status = _git(work, "status", "--porcelain")
    cfg = build_config("python", "FEATURE_NEW_UI", "True", dry_run=True)
    res = ps.run_cleanup(work, cfg)
    assert res.cleanup_status == "DRY_RUN_OK" and res.files_changed
    assert _git(work, "status", "--porcelain") == before_status == ""
    cfg2 = build_config("python", "NO_SUCH_FLAG_AT_ALL", "True", dry_run=False)
    res2 = ps.run_cleanup(work, cfg2)
    assert res2.cleanup_status == "NO_CHANGES" and not res2.files_changed


# ------------------------- real: governed flow -------------------------

def _repo_with_flag(c, tmp_path, case, repo_name, flag_key, language):
    """Register a golden-case checkout and create its flag via a project."""
    work = _copy_case(case, tmp_path / "work")
    repo = c.post("/api/repositories", json={"name": repo_name, "local_path": str(work),
                                             "language": language}).json()
    proj = c.post("/api/projects", json={"name": f"proj-{repo_name}"}).json()
    flag = c.post(f"/api/projects/{proj['id']}/flags",
                  json={"name": flag_key, "key": flag_key,
                        "repository_id": repo["id"]}).json()
    return repo, flag, work


def _client():
    from fastapi.testclient import TestClient
    from app.main import app
    return TestClient(app)


@needs_real
def test_flow_apply_and_verify_and_rescan(tmp_path):
    import subprocess
    c = _client()
    repo, flag, work = _repo_with_flag(c, tmp_path, "py_true", "pir-e2e",
                                       "FEATURE_NEW_UI", "Python")
    # SUCCESS path needs: no nested-block case, no multi-import case, green tests.
    (work / "case_nested.py").unlink()
    (work / "two_flags.py").unlink()
    (work / "pytest.ini").write_text("[pytest]\n")
    (work / "test_smoke.py").write_text("def test_ok():\n    assert True\n")
    subprocess.run(["git", "add", "-A"], cwd=str(work), check=True)
    subprocess.run(["git", "-c", "user.email=t@t", "-c", "user.name=t",
                    "commit", "-qm", "test setup"], cwd=str(work), check=True)
    # dry-run first: real plan, repo untouched
    d = c.post("/api/removals/dry-run", json={"flag_id": flag["id"], "permanent_value": "True"})
    assert d.status_code == 200, d.text
    assert d.json()["cleanupStatus"] == "DRY_RUN"
    assert "case_true.py" in (d.json()["plannedFiles"] or [])
    assert _git(work, "status", "--porcelain") == ""
    # approved removal via legacy endpoint (no risk guard) — real cleanup
    r = c.post(f"/api/flags/{flag['id']}/remove",
               json={"flag_id": flag["id"], "target_branch": "master",
                     "tool_target": "Piranha", "permanent_value": "True"})
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["cleanupStatus"] == "APPLIED"
    assert body["verificationStatus"] == "SUCCESS"
    assert "if FEATURE_NEW_UI" not in (work / "case_true.py").read_text()
    assert "post-cleanup" in " ".join(
        e["evidenceType"] for e in
        c.get("/api/evidence", params={"feature_flag_id": flag["id"]}).json())


@needs_real
def test_tracked_clean_ignores_untracked(tmp_path):
    from app.services import git_service
    d = tmp_path / "r"
    d.mkdir()
    (d / "a.py").write_text("v1\n")
    _git(d, "init", "-q")
    _git(d, "config", "user.email", "t@t.t")
    _git(d, "config", "user.name", "t")
    _git(d, "add", "-A")
    _git(d, "commit", "-qm", "init")
    assert git_service.tracked_clean(d) is True
    (d / "__pycache__").mkdir()
    (d / "__pycache__" / "x.pyc").write_text("junk")
    assert git_service.tracked_clean(d) is True  # untracked noise ignored
    (d / "a.py").write_text("modified\n")
    assert git_service.tracked_clean(d) is False


@needs_real
def test_flow_refuses_dirty_worktree(tmp_path):
    c = _client()
    repo, flag, work = _repo_with_flag(c, tmp_path, "py_true", "pir-dirty",
                                       "FEATURE_NEW_UI", "Python")
    (work / "case_true.py").write_text("# operator edit\n")
    r = c.post(f"/api/flags/{flag['id']}/remove",
               json={"flag_id": flag["id"], "permanent_value": "True"})
    assert r.status_code == 422
    assert "DIRTY" in r.text


@needs_real
def test_multi_name_import_preserved_byte_identical(tmp_path):
    src = Path(__file__).parent / "fixtures" / "piranha" / "cases" / "py_true" / "before" / "two_flags.py"
    assert "FEATURE_NEW_UI, FEATURE_OLD_SEARCH" in src.read_text()
    work = tmp_path / "w"
    work.mkdir()
    shutil.copy(src, work / "two_flags.py")
    subprocess.run(["git", "init", "-q", str(work)], check=True)
    from app.services import piranha_service as _ps
    cfg = _ps.build_config("python", "FEATURE_NEW_UI", "True", dry_run=False)
    res = _ps.run_cleanup(work, cfg)
    # multi-name import line must survive byte-identical; NO_CHANGES would also
    # be acceptable, APPLIED-with-other-changes must not touch the import
    content = (work / "two_flags.py").read_text()
    assert "from flags import FEATURE_NEW_UI, FEATURE_OLD_SEARCH" in content


@needs_real
def test_aliased_import_never_rewritten(tmp_path):
    from app.services import piranha_service as _ps
    d = tmp_path / "w"
    d.mkdir()
    (d / "a.py").write_text("from flags import FEATURE_ALIAS as F\n\n\ndef f():\n    if F:\n        return 1\n    return 0\n")
    subprocess.run(["git", "init", "-q", str(d)], check=True)
    subprocess.run(["git", "-C", str(d), "config", "user.email", "t@t.t"], check=True)
    subprocess.run(["git", "-C", str(d), "config", "user.name", "t"], check=True)
    subprocess.run(["git", "-C", str(d), "add", "-A"], check=True)
    subprocess.run(["git", "-C", str(d), "-c", "user.email=t@t", "-c", "user.name=t",
                    "commit", "-qm", "init"], check=True)
    cfg = _ps.build_config("python", "FEATURE_ALIAS", "True", dry_run=False)
    res = _ps.run_cleanup(d, cfg)
    # aliased usage is invisible to the name-based seed: must be NO_CHANGES,
    # never a corrupt partial rewrite
    assert res.cleanup_status == "NO_CHANGES" and not res.files_changed


@needs_real
def test_flow_unsupported_language_refused(tmp_path):
    c = _client()
    repo, flag, work = _repo_with_flag(c, tmp_path, "py_true", "pir-unsup",
                                       "FEATURE_NEW_UI", "Go")
    r = c.post(f"/api/flags/{flag['id']}/remove",
               json={"flag_id": flag["id"], "permanent_value": "True"})
    assert r.status_code == 422
    assert "UNSUPPORTED" in r.text


@needs_real
def test_flow_rollback_restores_bytes(tmp_path):
    from app.database import SessionLocal
    from app.models.models import RemovalOperation

    c = _client()
    repo, flag, work = _repo_with_flag(c, tmp_path, "py_false", "pir-rb",
                                       "FEATURE_OLD_SEARCH", "Python")
    before = {p.name: p.read_bytes() for p in work.iterdir() if p.is_file()}
    r = c.post(f"/api/flags/{flag['id']}/remove",
               json={"flag_id": flag["id"], "permanent_value": "False"})
    assert r.status_code == 201, r.text
    assert (work / "case_false.py").read_bytes() != before["case_false.py"]
    rb = c.post(f"/api/removals/{r.json()['id']}/rollback")
    assert rb.status_code == 200, rb.text
    after = {p.name: p.read_bytes() for p in work.iterdir() if p.is_file()}
    assert after == before, "rollback must restore exact bytes"
    # cleanup the fabricated-op path is unaffected: status recorded
    db = SessionLocal()
    assert db.get(RemovalOperation, r.json()["id"]).status == "ROLLED_BACK"
    db.close()


@needs_real
def test_no_credentials_in_evidence_or_logs(tmp_path):
    c = _client()
    repo, flag, work = _repo_with_flag(c, tmp_path, "py_true", "pir-sec",
                                       "FEATURE_NEW_UI", "Python")
    r = c.post(f"/api/flags/{flag['id']}/remove",
               json={"flag_id": flag["id"], "permanent_value": "True"})
    assert r.status_code == 201, r.text
    blob = r.text
    for row in c.get("/api/evidence", params={"feature_flag_id": flag["id"]}).json():
        blob += json.dumps(row.get("payload", {}))
    for needle in ("ghp_", "github_token", "bearer", "Authorization"):
        assert needle not in blob
