"""Phase 4 evaluation: corpus metrics from REAL executions.

Corpus: tests/fixtures/eval/{manifest.json, repos/*}. Metrics are computed,
never estimated; ground truth lives in the manifest. Real tool runs are
required (skipped without polyglot-piranha/FlagShark; they run in Docker).
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
from app.services import flagshark_service as fs  # noqa: E402
from app.services import piranha_service as ps  # noqa: E402
from app.services import provider_service as pv  # noqa: E402

init_db()

try:
    import importlib.util as _ilu
    REAL_LIB = _ilu.find_spec("polyglot_piranha") is not None
except Exception:
    REAL_LIB = False

REAL_FS = bool(__import__("shutil").which("flagshark"))
needs_real = pytest.mark.skipif(not (REAL_LIB and REAL_FS),
                                reason="needs FlagShark + Piranha (runs in Docker)")

EVAL = Path(__file__).parent / "fixtures" / "eval"
MANIFEST = json.loads((EVAL / "manifest.json").read_text())


def _materialize(case: dict, dest: Path) -> Path:
    src = EVAL / case["repo"]
    assert src.is_dir(), f"missing eval repo {src}"
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(src, dest)
    date = case.get("commit_date", "")
    env = dict(os.environ)
    if date and date != "now":
        env["GIT_AUTHOR_DATE"] = date
        env["GIT_COMMITTER_DATE"] = date
    subprocess.run(["git", "init", "-q", str(dest)], check=True)
    subprocess.run(["git", "-C", str(dest), "config", "user.email", "t@t.t"], check=True)
    subprocess.run(["git", "-C", str(dest), "config", "user.name", "t"], check=True)
    subprocess.run(["git", "-C", str(dest), "add", "-A"], check=True)
    subprocess.run(["git", "-C", str(dest), "-c", "user.email=t@t", "-c", "user.name=t",
                    "commit", "-qm", "eval"], check=True, env=env)
    return dest


def _detect(repo: Path):
    det = fs.run_detection(repo)
    prov, _ = pv.detect_provider_references(repo)
    found = {}
    for f in list(det.get("findings", [])) + prov:
        found.setdefault(f["flag_key"], {"stale": False, "engines": set()})
        found[f["flag_key"]]["stale"] = found[f["flag_key"]]["stale"] or bool(f.get("is_stale"))
        found[f["flag_key"]]["engines"].add(
            "flagshark" if "FlagShark" in str(det.get("engine", "")) and not f.get("detection_source")
            else ("provider" if f.get("detection_source") == "ProviderAST" else "fallback"))
    return found, det, prov


def test_manifest_integrity():
    assert MANIFEST["version"] == 1
    for c in MANIFEST["detection_cases"] + MANIFEST["cleanup_cases"]:
        assert c["id"] and (EVAL / c.get("repo", "")).is_dir() or "fixture_case" in c
    assert set(MANIFEST["metrics"]) >= {"detection_precision", "cleanup_success_rate"}


@needs_real
def test_detection_metrics_on_corpus(tmp_path):
    tp = fp = fn = 0
    stale_ok = stale_total = 0
    per_case = {}
    for case in MANIFEST["detection_cases"]:
        repo = _materialize(case, tmp_path / case["id"])
        found, det, prov = _detect(repo)
        expected = set(case["expected_keys"])
        got = set(found)
        tp += len(expected & got)
        fp += len(got - expected)
        fn += len(expected - got)
        for key in case.get("expected_stale", []):
            stale_total += 1
            stale_ok += 1 if found.get(key, {}).get("stale") else 0
        # must-not-detect list is absolute
        for bad in case.get("must_not_detect", []):
            assert not any(bad in k for k in got), f"{case['id']}: false positive containing {bad!r} in {sorted(got)}"
        per_case[case["id"]] = {"expected": sorted(expected), "got": sorted(got)}
    precision = tp / (tp + fp) if (tp + fp) else 1.0
    recall = tp / (tp + fn) if (tp + fn) else 1.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    print(f"\nEVAL detection: TP={tp} FP={fp} FN={fn} P={precision:.3f} R={recall:.3f} F1={f1:.3f} stale={stale_ok}/{stale_total} {per_case}")
    assert precision == 1.0, per_case
    assert recall == 1.0, per_case
    assert stale_ok == stale_total


@needs_real
def test_cleanup_metrics_on_corpus(tmp_path):
    from app.services.cleanup_flow import record_post_cleanup_scan  # noqa
    results: dict[str, str] = {}
    false_cleanups = 0
    for case in MANIFEST["cleanup_cases"]:
        if "fixture_case" in case:
            src = Path(__file__).parent / "fixtures" / "piranha" / "cases" / case["fixture_case"] / "before"
            work = tmp_path / case["id"]
            shutil.copytree(src, work)
            before = {p.name: p.read_bytes() for p in work.iterdir() if p.is_file()}
            unrelated_before = {(work / "unrelated.py").read_bytes() if (work / "unrelated.py").exists() else None,
                                (work / "unrelated.ts").read_bytes() if (work / "unrelated.ts").exists() else None}
        else:
            work = _materialize({"repo": case["repo"], "commit_date": "now"},
                                tmp_path / case["id"])
            before = {p.name: p.read_bytes() for p in work.rglob("*") if p.is_file() and ".git" not in p.parts}
            unrelated_before = set()
        lang = ps.repo_language_to_piranha(case["language"] if case["language"] != "go" else "Go")
        if lang is None:
            results[case["id"]] = "UNSUPPORTED"
            assert case["expect_status"] == "UNSUPPORTED"
            continue
        cfg = ps.build_config(lang, case["flag"], case["treated"], dry_run=False)
        try:
            res = ps.run_cleanup(work, cfg)
            status = res.cleanup_status
        except ps.PiranhaError as exc:
            status = exc.code
        results[case["id"]] = status
        assert status == case["expect_status"], f"{case['id']}: {status}"
        # false-cleanup: unrelated fixtures must be byte-identical
        for blob in unrelated_before:
            if blob is not None:
                assert blob in {p.read_bytes() for p in work.rglob("*") if p.is_file()}, case["id"]
    total = len(results)
    success = sum(1 for s in results.values() if s == "APPLIED")
    no_changes = sum(1 for s in results.values() if s == "NO_CHANGES")
    unsupported = sum(1 for s in results.values() if s == "UNSUPPORTED")
    print(f"\nEVAL cleanup: n={total} success={success/total:.2f} "
          f"no_changes={no_changes/total:.2f} unsupported={unsupported/total:.2f} "
          f"false_cleanup={false_cleanups} {results}")
    assert false_cleanups == 0
    assert unsupported >= 1  # corpus must exercise the honest refusal path


@needs_real
def test_rollback_success_rate(tmp_path):
    attempts = ok = 0
    for flag, treated in [("FEATURE_NEW_UI", "True"), ("FEATURE_OLD_SEARCH", "False")]:
        src = Path(__file__).parent / "fixtures" / "piranha" / "cases" / (
            "py_true" if treated == "True" else "py_false") / "before"
        work = tmp_path / f"rb_{flag}"
        shutil.copytree(src, work)
        subprocess.run(["git", "init", "-q", str(work)], check=True)
        subprocess.run(["git", "-C", str(work), "config", "user.email", "t@t.t"], check=True)
        subprocess.run(["git", "-C", str(work), "config", "user.name", "t"], check=True)
        subprocess.run(["git", "-C", str(work), "add", "-A"], check=True)
        subprocess.run(["git", "-C", str(work), "-c", "user.email=t@t", "-c", "user.name=t",
                        "commit", "-qm", "init"], check=True)
        base = subprocess.run(["git", "-C", str(work), "rev-parse", "HEAD"],
                              capture_output=True, text=True, check=True).stdout.strip()
        before = {p.name: p.read_bytes() for p in work.iterdir() if p.is_file()}
        cfg = ps.build_config("python", flag, treated, dry_run=False)
        res = ps.run_cleanup(work, cfg)
        assert res.cleanup_status == "APPLIED"
        attempts += 1
        assert ps.restore_workspace(work, base)["ok"] is True
        after = {p.name: p.read_bytes() for p in work.iterdir() if p.is_file()}
        if after == before:
            ok += 1
    print(f"\nEVAL rollback: {ok}/{attempts}")
    assert ok == attempts
