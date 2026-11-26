"""Phase 4 tests: LaunchDarkly provider-aware detection + cleanup.

Ground truth (verified by real polyglot-piranha 0.4.9 runs, see Phase 4 report):
- Python (launchdarkly-server-sdk 9.18.3 surface verified from the wheel):
  client.variation("LD_PY_CHECKOUT", ...) detected+cleanable;
  variation_detail (object return), computed keys, env-derived keys excluded.
- TypeScript: variation/boolVariation/stringVariation/numberVariation/
  jsonVariation detected+cleanable; *Detail/computed/env-derived excluded.
Real-execution tests skip without the library (they run in Docker).
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
from app.services import provider_service as pv  # noqa: E402
from app.services import piranha_service as ps  # noqa: E402

init_db()

try:
    import importlib.util as _ilu
    REAL_LIB = _ilu.find_spec("polyglot_piranha") is not None
except Exception:
    REAL_LIB = False

needs_real = pytest.mark.skipif(not REAL_LIB, reason="polyglot-piranha not installed here; runs in Docker")

PROV = Path(__file__).parent / "fixtures" / "piranha" / "prov"


def _repo_with(tmp_path, files: dict[str, str]) -> Path:
    d = tmp_path / "repo"
    d.mkdir()
    for rel, content in files.items():
        p = d / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content)
    subprocess.run(["git", "init", "-q", str(d)], check=True)
    subprocess.run(["git", "-C", str(d), "config", "user.email", "t@t.t"], check=True)
    subprocess.run(["git", "-C", str(d), "config", "user.name", "t"], check=True)
    subprocess.run(["git", "-C", str(d), "add", "-A"], check=True)
    subprocess.run(["git", "-C", str(d), "-c", "user.email=t@t", "-c", "user.name=t",
                    "commit", "-qm", "init"], check=True)
    return d


# ------------------------- unit: gating & parsing -------------------------

def test_strip_quotes():
    assert pv._strip_quotes('"FLAG_X"') == "FLAG_X"
    assert pv._strip_quotes("'FLAG_X'") == "FLAG_X"
    assert pv._strip_quotes("FLAG_X") is None
    assert pv._strip_quotes('"a" + b') is None
    assert pv._strip_quotes('""') is None


def test_import_gate_skips_unrelated_files(tmp_path):
    repo = _repo_with(tmp_path, {
        "a.py": "import ldclient\nx = client.variation(\"GATED_FLAG\", u, False)\n",
        "b.py": "x = something.variation(\"UNGATED_FLAG\", u, False)\n",
    })
    files = pv._candidate_files(repo, [".py"], ["ldclient"])
    assert [p.name for p in files] == ["a.py"]


def test_no_provider_config_means_no_findings(tmp_path):
    repo = _repo_with(tmp_path, {"a.go": 'x := 1\n'})
    findings, stats = pv.detect_provider_references(repo)
    # Go has no verified provider config: nothing detected, never an error.
    assert findings == []


def test_missing_library_reports_unavailable(monkeypatch, tmp_path):
    import app.services.provider_service as mod
    monkeypatch.setattr(mod.piranha_service, "piranha_status",
                        lambda: {"available": False})
    repo = _repo_with(tmp_path, {"a.py": "import ldclient\n"})
    findings, stats = mod.detect_provider_references(repo)
    assert findings == [] and stats.get("unavailable")


# ------------------------- real: match detection -------------------------

@needs_real
def test_provider_match_python(tmp_path):
    repo = _repo_with(tmp_path, {"ld.py": (PROV / "py" / "ld_usage.py").read_text()})
    findings, stats = pv.detect_provider_references(repo)
    keys = {f["flag_key"] for f in findings}
    assert keys == {"LD_PY_CHECKOUT"}, keys
    f = findings[0]
    assert f["file_path"] == "ld.py" and f["line_number"] == 6
    assert f["provider"] == "launchdarkly" and f["method"] == "variation"
    assert f["is_stale"] is False and "ProviderAST" in f["reason"]


@needs_real
def test_provider_match_typescript(tmp_path):
    repo = _repo_with(tmp_path, {"ld.ts": (PROV / "ts" / "ld_usage.ts").read_text()})
    findings, stats = pv.detect_provider_references(repo)
    keys = {f["flag_key"] for f in findings}
    assert keys == {"LD_TS_CHECKOUT", "LD_TS_BOOL", "LD_TS_STR",
                    "LD_TS_NUM", "LD_TS_JSON"}, keys
    methods = {f["flag_key"]: f["method"] for f in findings}
    assert methods["LD_TS_BOOL"] == "boolVariation"
    assert all("ProviderAST" in f["reason"] and f["is_stale"] is False
               for f in findings)


@needs_real
def test_provider_scan_integration_labels_sources(tmp_path):
    from fastapi.testclient import TestClient
    from app.main import app
    c = TestClient(app)
    repo = _repo_with(tmp_path, {"ld.py": (PROV / "py" / "ld_usage.py").read_text()})
    r = c.post("/api/repositories", json={"name": "prov-scan", "local_path": str(repo),
                                          "language": "Python"})
    assert r.status_code == 201, r.text
    s = c.post("/api/scans", json={"repository_id": r.json()["id"]})
    assert s.status_code == 201, s.text
    names = {f["flagKey"] for f in s.json()["findings"]}
    assert "LD_PY_CHECKOUT" in names
    # provider findings are never marked stale and never labelled FlagShark
    for f in s.json()["findings"]:
        if f["flagKey"] == "LD_PY_CHECKOUT":
            assert f["reason"].startswith("ProviderAST(")
    ev = c.get("/api/evidence")
    assert ev.status_code == 200
    prov_rows = [e for e in ev.json() if e["evidenceType"] == "provider-inventory"]
    assert prov_rows and all(e["source"].startswith("ProviderAST(") for e in prov_rows)


# ------------------------- real: provider cleanup -------------------------

def _run_cleanup(lang, workdir, flag, treated):
    cfg = ps.build_config(lang, flag, treated, dry_run=False)
    return ps.run_cleanup(workdir, cfg)


@needs_real
def test_provider_cleanup_python_true(tmp_path):
    work = tmp_path / "w"
    shutil.copytree(PROV / "py", work)
    res = _run_cleanup("python", work, "LD_PY_CHECKOUT", "True")
    assert res.cleanup_status == "APPLIED"
    text = (work / "ld_usage.py").read_text()
    assert "LD_PY_CHECKOUT" not in text and "return new_ui(user)" in text
    # excluded patterns untouched: detail call, computed and env keys remain
    assert "LD_PY_DETAIL" in text and "prefix_" in text and "os.getenv" in text


@needs_real
def test_provider_cleanup_typescript_bool(tmp_path):
    work = tmp_path / "w"
    shutil.copytree(PROV / "ts", work)
    res = _run_cleanup("typescript", work, "LD_TS_BOOL", "true")
    assert res.cleanup_status == "APPLIED"
    text = (work / "ld_usage.ts").read_text()
    assert "LD_TS_BOOL" not in text
    # Detail variant untouched (object return would break if replaced)
    assert "LD_TS_DETAIL" in text and "variationDetail" in text


@needs_real
def test_provider_match_tsx(tmp_path):
    repo = _repo_with(tmp_path, {"ld.tsx": (PROV / "tsx" / "ld_usage.tsx").read_text()})
    findings, stats = pv.detect_provider_references(repo)
    keys = {f["flag_key"] for f in findings}
    assert keys == {"TSX_CHECKOUT"}, keys
    assert findings[0]["language"] == "tsx"


@needs_real
def test_provider_no_changes_for_unsupported_pattern(tmp_path):
    work = tmp_path / "w"
    shutil.copytree(PROV / "py", work)
    # detail-variant flags have no cleanup rule: honest NO_CHANGES, never SUCCESS
    res = _run_cleanup("python", work, "LD_PY_DETAIL", "True")
    assert res.cleanup_status == "NO_CHANGES" and not res.files_changed


@needs_real
def test_provider_unknown_flag_no_changes(tmp_path):
    work = tmp_path / "w"
    shutil.copytree(PROV / "ts", work)
    res = _run_cleanup("typescript", work, "NO_SUCH_FLAG_XYZ", "true")
    assert res.cleanup_status == "NO_CHANGES" and not res.files_changed
