"""Real FlagShark invocation. Never fakes results.

Strategy: try `flagshark` binary with a few common CLI shapes:
  flagshark --path <repo> [--format json]
  flagshark scan <repo> --format json
  flagshark --help (to detect availability)
If stdout parses as JSON we normalize it; otherwise we store raw output and
fall back to a local regex-based reference scan (clearly labelled engine
'Regex-Fallback', NOT FlagShark) so scans still produce honest local data.
If no binary exists and fallback finds nothing, scan is marked failed with a
clear 'FlagShark is not installed' error instead of fake flags.
"""
from __future__ import annotations

import json
import re
import time
from pathlib import Path

from ..config import get_settings
from ..utils.subprocess_util import CmdResult, run_cmd, which

settings = get_settings()

FLAG_PATTERN = re.compile(r"\b([A-Z][A-Z0-9_]{3,64})\b")
STRING_FLAG_PATTERN = re.compile(r"""['\"`]([A-Z][A-Z0-9_]{4,64})['\"`]""")
SKIP_DIRS = {".git", "node_modules", "dist", "build", ".venv", "venv", "__pycache__", "target"}
SKIP_EXT = {".png", ".jpg", ".jpeg", ".gif", ".ico", ".woff", ".woff2", ".ttf", ".pdf", ".zip"}


def flagshark_status() -> dict:
    path = which(settings.FLAGS_HARK_BIN)
    if not path:
        return {"available": False, "path": "", "version": "UNAVAILABLE",
                "hint": f"'{settings.FLAGS_HARK_BIN}' not found on PATH. Install FlagShark and set FLAGS_HARK_BIN if needed."}
    r = run_cmd([settings.FLAGS_HARK_BIN, "--help"], timeout=20)
    probe = (r.stdout or "") + (r.stderr or "")
    return {"available": True, "path": path, "version": probe[:500],
            "hint": ""}


def _try_flagshark_json(repo: Path) -> tuple[CmdResult | None, str]:
    """Try common CLI shapes, return (result, shape_used)."""
    shapes = [
        [settings.FLAGS_HARK_BIN, "--path", str(repo), "--format", "json"],
        [settings.FLAGS_HARK_BIN, "scan", str(repo), "--format", "json"],
        [settings.FLAGS_HARK_BIN, "--path", str(repo)],
        [settings.FLAGS_HARK_BIN, "scan", str(repo)],
    ]
    for shape in shapes:
        r = run_cmd(shape, cwd=str(repo), timeout=settings.SCAN_TIMEOUT_SEC)
        combined = (r.stdout or "") + (r.stderr or "")
        if "not found" in combined.lower() or r.returncode == 127:
            return None, ""
        # accept any run that produced output; parse later
        if (r.stdout or "").strip():
            return r, " ".join(shape[:2])
    return r, " ".join(shapes[0][:2])


def _normalize_flagshark_json(payload: object) -> list[dict]:
    """Best-effort normalization of unknown FlagShark JSON shapes into findings."""
    findings: list[dict] = []
    if isinstance(payload, dict):
        candidates: object = payload.get("flags", payload.get("findings", payload.get("results", [])))
    else:
        candidates = payload
    if isinstance(candidates, dict):
        candidates = [candidates]
    if not isinstance(candidates, list):
        return findings
    for item in candidates:
        if not isinstance(item, dict):
            continue
        key = str(item.get("flag_key") or item.get("key") or item.get("name") or item.get("flag") or "")
        if not key:
            continue
        findings.append({
            "flag_key": key,
            "file_path": str(item.get("file_path") or item.get("file") or item.get("path") or ""),
            "line_number": int(item.get("line_number") or item.get("line") or 0),
            "ast_node_type": str(item.get("ast_node_type") or item.get("node_type") or "Unknown"),
            "is_stale": bool(item.get("is_stale", False)),
            "confidence": float(item.get("confidence", 0.5)),
            "reason": str(item.get("reason") or "Detected by FlagShark"),
        })
    return findings


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
                    })
                    if len(findings) > 2000:
                        return findings
    return findings


def run_detection(repo: Path) -> dict:
    started = time.time()
    status = flagshark_status()
    raw = ""
    engine = "FlagShark-engine"
    findings: list[dict] = []
    error = ""
    if status["available"]:
        result, shape = _try_flagshark_json(repo)
        if result is None:
            error = f"FlagShark binary '{settings.FLAGS_HARK_BIN}' could not be executed."
            engine = "FlagShark-engine"
        else:
            raw = (result.stdout or "")[:20000]
            try:
                payload = json.loads(result.stdout)
                findings = _normalize_flagshark_json(payload)
                if not findings and (result.stdout or "").strip():
                    # produced output but not parseable -> keep raw, mark partial
                    error = f"FlagShark output was not parseable JSON (shape: {shape}); raw output stored."
                    engine = "FlagShark-engine"
            except Exception as exc:
                # Non-JSON output: store raw, supplement with honest local scan
                error = f"FlagShark output not JSON ({exc}); supplemented with local reference scan."
                extra = regex_reference_scan(repo)
                findings = extra
                engine = "Regex-Fallback"
                raw = (result.stdout or "")[:20000]
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
            "duration_ms": duration_ms, "tool_available": status["available"]}
