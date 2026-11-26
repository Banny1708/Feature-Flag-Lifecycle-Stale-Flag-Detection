"""Phase 2 tests: verified FlagShark v2.8.0 adapter.

Schema assertions use the RECORDED golden fixture
(tests/fixtures/flagshark/actual_scan_output.json) from a real
`flagshark scan --format json` run — never an invented schema.
Subprocess mocking replays ACTUAL observed stdout/exit codes.
"""
import json
from pathlib import Path

import pytest

import os
import tempfile

os.environ.setdefault("DATABASE_URL", f"sqlite:///{tempfile.NamedTemporaryFile(suffix='.db', delete=False).name}")

from app.database import init_db  # noqa: E402
from app.services import flagshark_service as fs  # noqa: E402
from app.services.flagshark_service import (  # noqa: E402
    FlagSharkOutputError,
    normalize_findings,
    parse_flagshark_output,
    relativize_path,
)

init_db()

FIXTURE = Path(__file__).parent / "fixtures" / "flagshark" / "actual_scan_output.json"
GOLDEN = json.loads(FIXTURE.read_text())
REPO = Path("/repo")


# ---------- 1-2. executable + version detection ----------

def test_status_missing_binary(monkeypatch):
    import app.services.flagshark_service as mod
    monkeypatch.setattr(mod.settings, "FLAGS_HARK_BIN", "definitely-not-a-real-binary-xyz")
    s = mod.flagshark_status()
    assert s["available"] is False and s["version"] == "UNAVAILABLE"
    assert "flagshark" in s["hint"].lower()


def test_version_parsing_unit():
    import re
    from app.services.flagshark_service import _VERSION_RE
    assert _VERSION_RE.search("flagshark v2.8.0").group(1) == "2.8.0"


# ---------- 3-5. recorded output parses + normalizes ----------

def test_golden_fixture_parses():
    payload = parse_flagshark_output(json.dumps(GOLDEN))
    assert payload["version"] == "2.8.0"
    assert payload["totalFlags"] == 4 and payload["staleFlags"] == 3
    assert isinstance(payload["flags"], list) and len(payload["flags"]) == 3


def test_golden_normalization_preserves_real_fields():
    findings, stats = normalize_findings(GOLDEN, REPO)
    assert stats == {"skipped": 0, "invalid_paths": 0}
    by_key = {f["flag_key"]: f for f in findings}
    t = by_key["TEST_ONLY_FLAG"]
    assert t["file_path"] == "tests/test_flags.py" and t["line_number"] == 4
    assert t["is_stale"] is True
    assert t["language"] == "python" and t["provider"] == "ldclient"
    assert t["confidence_tier"] == "high" and t["confidence"] == 0.9
    assert set(t["signals"]) == {"age", "low-usage", "test-only-references"}
    assert t["age"] == "1 year ago"
    # No AST node types are reported by FlagShark: honest "Unknown", never invented.
    assert all(f["ast_node_type"] == "Unknown" for f in findings)


def test_stale_only_property_documented():
    # totalFlags counts a fresh flag that has NO entry: the adapter must not
    # invent findings for it.
    findings, _ = normalize_findings(GOLDEN, REPO)
    assert "FRESH_ROLLOUT_2026" not in {f["flag_key"] for f in findings}


# ---------- 6-8. path normalization ----------

def test_relative_path_kept():
    assert relativize_path(REPO, "src/a.ts") == "src/a.ts"


def test_absolute_inside_repo():
    assert relativize_path(REPO, "/repo/src/a.ts") == "src/a.ts"


def test_absolute_outside_repo_rejected():
    with pytest.raises(FlagSharkOutputError):
        relativize_path(REPO, "/etc/passwd")


def test_traversal_rejected():
    with pytest.raises(FlagSharkOutputError):
        relativize_path(REPO, "../../etc/passwd")
    with pytest.raises(FlagSharkOutputError):
        relativize_path(REPO, "")


def test_invalid_paths_counted_not_persisted():
    payload = {"flags": [
        {"name": "GOOD_FLAG", "file": "/repo/a.py", "line": 1},
        {"name": "EVIL_FLAG", "file": "/etc/passwd", "line": 1},
        {"name": "", "file": "/repo/b.py", "line": 2},
        "not-a-dict",
    ]}
    findings, stats = normalize_findings(payload, REPO)
    assert [f["flag_key"] for f in findings] == ["GOOD_FLAG"]
    assert stats == {"skipped": 2, "invalid_paths": 1}


# ---------- 9-12. malformed / edge outputs ----------

def test_empty_flags_is_valid_clean_scan():
    payload = parse_flagshark_output(json.dumps({"version": "2.8.0", "totalFlags": 0,
                                                 "staleFlags": 0, "flags": []}))
    findings, _ = normalize_findings(payload, REPO)
    assert findings == []


def test_malformed_outputs_rejected():
    for bad in ["not json at all", "[1,2,3]",
                json.dumps({"totalFlags": 1}),
                json.dumps({"flags": {}}),
                json.dumps({"flags": [], "totalFlags": "many"})]:
        with pytest.raises(FlagSharkOutputError):
            parse_flagshark_output(bad)


def test_missing_verdict_is_not_stale():
    findings, _ = normalize_findings(
        {"flags": [{"name": "X_FLAG", "file": "a.py", "line": 1}]}, REPO)
    assert findings[0]["is_stale"] is False


def test_missing_language_derived_from_extension():
    findings, _ = normalize_findings(
        {"flags": [{"name": "X_FLAG", "file": "a.py", "line": 1}]}, REPO)
    assert findings[0]["language"] == "python"
    findings2, _ = normalize_findings(
        {"flags": [{"name": "Y_FLAG", "file": "a.weird", "line": 1}]}, REPO)
    assert findings2[0]["language"] == "unknown"


# ---------- 13-15. exit codes / timeout / fallback, replaying REAL outputs ----------

def _payload_under(payload: dict, root: Path) -> dict:
    """Relocate a recorded payload's absolute /repo paths under a test dir."""
    import copy
    out = copy.deepcopy(payload)
    for item in out.get("flags", []):
        if isinstance(item, dict) and str(item.get("file", "")).startswith("/repo/"):
            item["file"] = str(root / str(item["file"])[len("/repo/"):])
    return out


def _replay(monkeypatch, stdout, returncode=1, timed_out=False):
    from app.utils.subprocess_util import CmdResult
    import app.services.flagshark_service as mod

    def fake_which(_bin):
        return "/usr/local/bin/flagshark"

    def fake_run(args, cwd=None, timeout=120):
        if "--version" in args:
            return CmdResult(0, "flagshark v2.8.0", "")
        return CmdResult(returncode, stdout, "", timed_out)

    monkeypatch.setattr(mod, "which", fake_which)
    monkeypatch.setattr(mod, "run_cmd", fake_run)


def test_exit_1_with_stale_is_success_engine_flagshark(monkeypatch, tmp_path):
    _replay(monkeypatch, json.dumps(_payload_under(GOLDEN, tmp_path)), returncode=1)
    out = fs.run_detection(tmp_path)
    assert out["tool_available"] is True
    assert out["engine"].startswith("FlagShark")
    assert out["engine"] == "FlagShark 2.8.0"
    assert len(out["findings"]) == 3
    assert out["error"] == ""


def test_exit_0_empty_is_clean_success(monkeypatch, tmp_path):
    _replay(monkeypatch, json.dumps({"version": "2.8.0", "totalFlags": 0,
                                     "staleFlags": 0, "flags": []}), returncode=0)
    out = fs.run_detection(tmp_path)
    assert out["engine"].startswith("FlagShark") and out["findings"] == []


def test_exit_2_falls_back_with_honest_engine(monkeypatch, tmp_path):
    _replay(monkeypatch, "", returncode=2)
    (tmp_path / "a.py").write_text("x = 'NOT_A_FLAG_VALUE'\n")
    out = fs.run_detection(tmp_path)
    assert out["engine"] == "Regex-Fallback"
    assert "code 2" in out["error"]


def test_timeout_falls_back_and_reports(monkeypatch, tmp_path):
    _replay(monkeypatch, "", returncode=124, timed_out=True)
    (tmp_path / "a.py").write_text("x = 'LEGACY_TIMEOUT_FLAG'\n")
    out = fs.run_detection(tmp_path)
    assert out["engine"] == "Regex-Fallback"
    assert "timed out" in out["error"]
    assert any(f["flag_key"] == "LEGACY_TIMEOUT_FLAG" for f in out["findings"])


def test_non_json_stdout_falls_back_and_records(monkeypatch, tmp_path):
    _replay(monkeypatch, "some human text, not json", returncode=1)
    (tmp_path / "a.py").write_text("x = 'LEGACY_NONJSON_FLAG'\n")
    out = fs.run_detection(tmp_path)
    assert out["engine"] == "Regex-Fallback"
    assert "not JSON" in out["error"] or "schema" in out["error"]


# ---------- 16-18. persistence + engine correctness + no fake AST ----------

def test_scan_persistence_with_flagshark_findings(monkeypatch, tmp_path):
    from fastapi.testclient import TestClient
    from app.main import app

    _replay(monkeypatch, json.dumps(_payload_under(GOLDEN, tmp_path)), returncode=1)

    c = TestClient(app)
    r = c.post("/api/repositories", json={"name": "fs-persist", "local_path": str(tmp_path)})
    assert r.status_code == 201, r.text
    repo_id = r.json()["id"]
    s = c.post("/api/scans", json={"repository_id": repo_id})
    assert s.status_code == 201, s.text
    body = s.json()
    assert body["scannerEngine"].startswith("FlagShark")
    assert body["staleFlagsDetected"] == 3
    # findings persisted with honest node type + real provider/language in reason
    det = [f for f in body["findings"] if f["flagKey"] == "TEST_ONLY_FLAG"]
    assert det and det[0]["astNodeType"] == "Unknown"
    assert "ldclient" in det[0]["reason"] or "test-only" in det[0]["reason"]
    # structured stale-signal evidence row exists
    ev = c.get("/api/evidence", params={"feature_flag_id": det[0]["flagKey"]})
    assert ev.status_code == 200
    sig_rows = [e for e in ev.json() if e["evidenceType"] == "stale-signal"]
    assert sig_rows and sig_rows[0]["payload"]["provider"] == "ldclient"
