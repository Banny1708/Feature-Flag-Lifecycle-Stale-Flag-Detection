"""Verified FlagShark integration (official CLI: https://github.com/FlagShark/flagshark).

PINNED VERSION: 2.8.0 (npm `flagshark@2.8.0`, MIT). Verified 2026-10-24:

- Command:  `flagshark scan --format json`   (cwd = repository; NO positional path arg)
- `--version` -> `flagshark v2.8.0`, exit 0.  `--help` documents scan/assess.
- Exit codes: 0 = no stale flags, 1 = stale flags found, 2 = runtime/config error.
  Human progress logs go to stderr; `--format json` puts the schema on stdout.
- Top-level JSON keys: version, totalFlags, staleFlags, errorCount,
  parseErrorCount, excludedPermanent, permanentByPlatform, healthScore,
  detectedProviders, languages, flags[], scanDuration, links.
- `flags[]` contains STALE flags only (one entry per unique flag, first
  location). Non-stale detected flags are counted in totalFlags but not listed.
- Per-flag keys: name, file (ABSOLUTE path), line (int), language, provider,
  stale (bool), severity, confidence ("high"|"medium"|"low" STRING tier),
  signals[] ({type, severity, description}), age (human string like
  "1 year ago", or null when git blame is unavailable).
- FlagShark does NOT report AST node types. We persist ast_node_type="Unknown"
  rather than inventing one.

Stale semantics: FlagShark reports its own stale verdict + signals (age via
git blame vs --threshold, low-usage contributing-only, test-only-references,
platform-* with LaunchDarkly token). FlagOps' own detection engine
(services/detection_service.py) remains the lifecycle authority; scanner and
detection engine are recorded separately.

When the binary is missing or unusable, the labelled Regex-Fallback scan is
used and the engine is recorded as "Regex-Fallback" — never as FlagShark.
"""
from __future__ import annotations

import json
import re
import time
from pathlib import Path

from ..config import get_settings
from ..utils.subprocess_util import CmdResult, run_cmd, which

settings = get_settings()

#: Pinned official release this adapter was verified against. The Docker image
#: installs exactly this version; the adapter also records the version string
#: reported by the binary at runtime.
FLAGSHARK_VERSION_PIN = "2.8.0"

#: Verified CLI shape. `scan` takes NO positional path — the repo is supplied
#: via cwd. `--format json` is the documented stable machine schema
#: (`--json` is a deprecated shorthand for the same thing).
FLAGSHARK_SCAN_ARGV = ["scan", "--format", "json"]

#: Confidence tier (string, as reported) -> numeric score for DB/API compat.
CONFIDENCE_TIER_SCORE = {"high": 0.9, "medium": 0.6, "low": 0.3}

#: Extension -> language label when FlagShark omits `language`. This is a
#: filename heuristic, NOT an AST claim.
EXT_LANGUAGE = {
    ".ts": "typescript", ".tsx": "typescript",
    ".js": "javascript", ".jsx": "javascript", ".mjs": "javascript", ".cjs": "javascript",
    ".py": "python", ".go": "go", ".java": "java", ".cs": "csharp", ".php": "php",
    ".rs": "rust", ".kt": "kotlin", ".swift": "swift", ".rb": "ruby",
    ".c": "c", ".cpp": "cpp", ".h": "c", ".hpp": "cpp", ".m": "objective-c",
}

FLAG_PATTERN = re.compile(r"\b([A-Z][A-Z0-9_]{3,64})\b")
STRING_FLAG_PATTERN = re.compile(r"""['\"`]([A-Z][A-Z0-9_]{4,64})['\"`]""")
SKIP_DIRS = {".git", "node_modules", "dist", "build", ".venv", "venv", "__pycache__", "target"}
SKIP_EXT = {".png", ".jpg", ".jpeg", ".gif", ".ico", ".woff", ".woff2", ".ttf", ".pdf", ".zip"}

_VERSION_RE = re.compile(r"flagshark\s+v?(\d+\.\d+\.\d+)", re.IGNORECASE)


class FlagSharkOutputError(ValueError):
    """Recorded FlagShark stdout is not the documented schema."""


def flagshark_status() -> dict:
    """Probe the real binary. Version comes from `flagshark --version`."""
    path = which(settings.FLAGS_HARK_BIN)
    if not path:
        return {"available": False, "path": "", "version": "UNAVAILABLE",
                "hint": f"'{settings.FLAGS_HARK_BIN}' not found on PATH. "
                        f"Install the official CLI (npm i -g flagshark@{FLAGSHARK_VERSION_PIN}) "
                        "and set FLAGS_HARK_BIN if needed."}
    r = run_cmd([settings.FLAGS_HARK_BIN, "--version"], timeout=30)
    probe = ((r.stdout or "") + "\n" + (r.stderr or "")).strip()
    m = _VERSION_RE.search(probe)
    version = m.group(1) if m else (probe[:120] or "UNKNOWN")
    return {"available": r.returncode == 0, "path": path, "version": version,
            "hint": "" if r.returncode == 0 else f"--version failed: {probe[:200]}"}


def run_flagshark_scan(repo: Path) -> tuple[CmdResult, float]:
    """Execute the verified scan shape. Returns (result, duration_ms).

    Exit 0 (no stale) and 1 (stale found) are both successful scans; exit 2
    signals a runtime/config error. Raises FileNotFoundError-equivalent via
    returncode 127 when the binary is missing.
    """
    started = time.time()
    result = run_cmd([settings.FLAGS_HARK_BIN, *FLAGSHARK_SCAN_ARGV],
                     cwd=str(repo), timeout=settings.SCAN_TIMEOUT_SEC)
    return result, (time.time() - started) * 1000


def parse_flagshark_output(stdout: str) -> dict:
    """Parse stdout into the documented schema subset. Raises on mismatch."""
    try:
        payload = json.loads((stdout or "").strip())
    except Exception as exc:
        raise FlagSharkOutputError(f"stdout is not JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise FlagSharkOutputError(
            f"top-level JSON must be an object, got {type(payload).__name__}")
    flags = payload.get("flags")
    if not isinstance(flags, list):
        raise FlagSharkOutputError("missing required key 'flags' (expected a list)")
    for key in ("totalFlags", "staleFlags"):
        if key in payload and not isinstance(payload[key], int):
            raise FlagSharkOutputError(f"key '{key}' must be an int")
    return payload


def relativize_path(repo: Path, file_path: str) -> str:
    """Return file_path relative to repo. Rejects escapes.

    Raises FlagSharkOutputError for empty paths, absolute paths outside the
    repo, or relative paths escaping it (../). Callers count these as invalid
    tool output — they are never persisted.
    """
    raw = (file_path or "").strip()
    if not raw:
        raise FlagSharkOutputError("finding has an empty file path")
    p = Path(raw)
    if p.is_absolute():
        try:
            return str(p.resolve().relative_to(repo.resolve()))
        except ValueError:
            raise FlagSharkOutputError(f"finding path escapes repository: {raw[:200]}")
    # relative: normalise lexically, then verify containment
    joined = (repo.resolve() / p)
    try:
        return str(joined.resolve().relative_to(repo.resolve()))
    except ValueError:
        raise FlagSharkOutputError(f"finding path escapes repository: {raw[:200]}")


def language_for(rel_path: str, reported: object) -> str:
    """Prefer FlagShark's own language label; else extension heuristic; else 'unknown'."""
    if isinstance(reported, str) and reported.strip():
        return reported.strip().lower()
    return EXT_LANGUAGE.get(Path(rel_path).suffix.lower(), "unknown")


def normalize_findings(payload: dict, repo: Path) -> tuple[list[dict], dict]:
    """Normalize verified FlagShark `flags[]` into FlagOps findings.

    Returns (findings, stats) where stats counts skipped/invalid entries.
    Fields that FlagShark does not provide are null/unknown — never invented.
    `stale` defaults to False when absent (a missing verdict is not a stale
    verdict); confidence tiers map to numeric scores with the raw tier kept.
    """
    findings: list[dict] = []
    skipped = 0
    invalid_paths = 0
    for item in payload.get("flags", []):
        if not isinstance(item, dict):
            skipped += 1
            continue
        key = item.get("name")
        if not isinstance(key, str) or not key.strip():
            skipped += 1
            continue
        try:
            rel = relativize_path(repo, str(item.get("file", "")))
        except FlagSharkOutputError:
            invalid_paths += 1
            continue
        try:
            line = int(item.get("line") or 0)
        except (TypeError, ValueError):
            line = 0
        tier = str(item.get("confidence", "") or "").lower()
        stale = item.get("stale", False)
        signals = item.get("signals") if isinstance(item.get("signals"), list) else []
        sig_types = [str(s.get("type", "")) for s in signals
                     if isinstance(s, dict) and s.get("type")]
        sig_text = "; ".join(
            str(s.get("description", s.get("type", ""))) for s in signals
            if isinstance(s, dict))[:1000]
        findings.append({
            "flag_key": key.strip(),
            "file_path": rel,
            "line_number": line,
            # FlagShark reports no AST node types; "Unknown" is the honest value.
            "ast_node_type": "Unknown",
            "is_stale": bool(stale),
            "confidence": CONFIDENCE_TIER_SCORE.get(tier, 0.5),
            "reason": (f"FlagShark: {'; '.join(sig_types) or 'detected'}"
                       + (f" — {sig_text}" if sig_text and sig_types else ""))[:1500],
            # Verified-schema extras (persisted into evidence payloads):
            "language": language_for(rel, item.get("language")),
            "provider": str(item.get("provider", "") or "")[:120],
            "severity": str(item.get("severity", "") or "")[:32],
            "confidence_tier": tier or "unknown",
            "signals": sig_types,
            "signal_details": sig_text,
            "age": (str(item.get("age")) if item.get("age") is not None else None),
        })
    return findings, {"skipped": skipped, "invalid_paths": invalid_paths}


def regex_reference_scan(repo: Path) -> list[dict]:
    """Honest local fallback: grep UPPER_SNAKE tokens in string literals. Engine labelled Regex-Fallback."""
    findings: list[dict] = []
    files = 0
    for p in repo.rglob("*"):
        if files > 20000:
            break
        try:
            if not p.is_file():
                continue
            if any(part in SKIP_DIRS for part in p.parts):
                continue
            if p.suffix.lower() in SKIP_EXT:
                continue
            if p.stat().st_size > 1_000_000:
                continue
            text = p.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        files += 1
        rel = str(p.relative_to(repo))
        for i, line in enumerate(text.splitlines(), start=1):
            for m in STRING_FLAG_PATTERN.finditer(line):
                token = m.group(1)
                if any(w in token for w in ("FLAG", "ENABLE", "DISABLE", "ROLLOUT", "EXPERIMENT", "LEGACY", "DEPRECATED", "TEMP", "HOTFIX")):
                    findings.append({
                        "flag_key": token,
                        "file_path": rel,
                        "line_number": i,
                        "ast_node_type": "StringLiteral",
                        "is_stale": False,
                        "confidence": 0.4,
                        "reason": "Local reference scan (Regex-Fallback): string literal looks like a flag key",
                        "language": language_for(rel, None),
                        "provider": "",
                        "severity": "",
                        "confidence_tier": "regex",
                        "signals": [],
                        "signal_details": "",
                        "age": None,
                    })
                    if len(findings) > 2000:
                        return findings
    return findings


def run_detection(repo: Path) -> dict:
    """Run the verified FlagShark scan, else the labelled Regex-Fallback.

    Return contract (unchanged for callers): engine, findings, raw, error,
    duration_ms, tool_available — plus version, exit_code, total_flags,
    invalid_paths, signal stats for transparency.
    """
    started = time.time()
    status = flagshark_status()
    raw = ""
    engine = "FlagShark-engine"
    findings: list[dict] = []
    error = ""
    version = status.get("version", "UNAVAILABLE")
    exit_code: int | None = None
    total_flags = 0
    invalid_paths = 0

    if status["available"]:
        result, _scan_ms = run_flagshark_scan(repo)
        exit_code = result.returncode
        raw = (result.stdout or "")[:20000]
        if result.timed_out:
            error = (f"FlagShark scan timed out after {settings.SCAN_TIMEOUT_SEC}s; "
                     "supplemented with local reference scan.")
            findings = regex_reference_scan(repo)
            engine = "Regex-Fallback"
        elif exit_code in (0, 1):
            # Both are successful scans (1 == stale flags found).
            try:
                payload = parse_flagshark_output(result.stdout or "")
                total_flags = int(payload.get("totalFlags", 0) or 0)
                findings, stats = normalize_findings(payload, repo)
                invalid_paths = stats["invalid_paths"]
                if stats["skipped"] or invalid_paths:
                    error = (f"FlagShark output contained {stats['skipped']} skipped "
                             f"and {invalid_paths} out-of-workspace entries (ignored).")
                reported_version = str(payload.get("version", "") or "").strip()
                if reported_version:
                    version = reported_version
                engine = f"FlagShark {version}" if version not in ("", "UNAVAILABLE", "UNKNOWN") else "FlagShark"
            except FlagSharkOutputError as exc:
                error = (f"FlagShark output did not match the v{FLAGSHARK_VERSION_PIN} schema "
                         f"({exc}); supplemented with local reference scan.")
                findings = regex_reference_scan(repo)
                engine = "Regex-Fallback"
        else:
            # Exit 2 (or other): runtime/config error. Parse attempt first so a
            # partial JSON is never silently discarded; otherwise honest fallback.
            parsed_ok = False
            try:
                payload = parse_flagshark_output(result.stdout or "")
                total_flags = int(payload.get("totalFlags", 0) or 0)
                findings, stats = normalize_findings(payload, repo)
                invalid_paths = stats["invalid_paths"]
                parsed_ok = bool(findings) or total_flags == 0
                engine = f"FlagShark {version}" if version not in ("", "UNAVAILABLE", "UNKNOWN") else "FlagShark"
            except FlagSharkOutputError:
                parsed_ok = False
            if not parsed_ok:
                findings = regex_reference_scan(repo)
                engine = "Regex-Fallback"
            tail = ((result.stderr or "") + "\n" + (result.stdout or "")).strip().splitlines()
            detail = tail[-1][-300:] if tail and tail[-1].strip() else ""
            error = (f"FlagShark exited with code {exit_code} "
                     f"({detail or 'no output'}); "
                     + ("partial FlagShark findings kept." if parsed_ok and engine.startswith("FlagShark")
                        else "results come from local Regex-Fallback scan, not FlagShark."))
    else:
        # No binary: do NOT fake FlagShark results. Honest local scan, clearly labelled.
        findings = regex_reference_scan(repo)
        engine = "Regex-Fallback"
        if not findings:
            error = ("FlagShark is not installed/configured "
                     f"('{settings.FLAGS_HARK_BIN}' not found on PATH) and the local reference scan "
                     "found no flag-like references. Install FlagShark for full AST detection.")
        else:
            error = (f"FlagShark is not installed ('{settings.FLAGS_HARK_BIN}' not found); "
                     f"results come from local Regex-Fallback scan, not FlagShark.")
    duration_ms = int((time.time() - started) * 1000)
    return {"engine": engine, "findings": findings, "raw": raw, "error": error,
            "duration_ms": duration_ms, "tool_available": status["available"],
            "version": version, "exit_code": exit_code, "total_flags": total_flags,
            "invalid_paths": invalid_paths}
