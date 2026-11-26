"""LaunchDarkly provider-aware detection (source-labelled ProviderAST).

Supplement to FlagShark, never a replacement: FlagShark remains the primary
scanner. This layer finds SDK-mediated flag references with literal keys
that FlagShark's import-gated detection can miss in non-standard layouts,
using verified tree-sitter match queries executed by the pinned
polyglot-piranha engine in dry-run mode (no writes, ever).

Verified 2026-10-26 (lab fixture `piranha-lab/prov/`):
- Python (`ldclient`, surface verified from launchdarkly-server-sdk 9.18.3):
  `X.variation("FLAG", ...)` incl. chained `ldclient.get().variation(...)`.
  `variation_detail` (object return), computed keys (`"prefix_" + name`) and
  env-derived keys (`os.getenv(...)`) do NOT match.
- TypeScript (`launchdarkly-node-server-sdk` and `@launchdarkly/*`) and TSX:
  variation/boolVariation/stringVariation/numberVariation/jsonVariation with
  literal keys. *Detail variants, computed and env-derived keys excluded.
  Piranha scans only `.py` for language=python and `.ts` for
  language=typescript, so candidacy is restricted to exactly those
  extensions (plus `.tsx` via the dedicated tsx entry); anything else would
  be silently skipped and is therefore excluded up front.

Every finding carries source "ProviderAST" plus provider/method/language.
is_stale is ALWAYS False here: provider references are inventory, never
staleness verdicts — lifecycle stays with the FlagOps detection engine.
"""
from __future__ import annotations

from pathlib import Path

from . import piranha_service
from ..utils.subprocess_util import which

# language -> (file extensions, import markers proving SDK usage, method label)
PROVIDERS: dict[str, dict[str, dict[str, list[str]]]] = {
    "launchdarkly": {
        "python": {
            "extensions": [".py"],
            "imports": ["ldclient", "launchdarkly"],
            "methods": ["variation"],
        },
        "typescript": {
            "extensions": [".ts"],
            "imports": ["launchdarkly-node-server-sdk", "@launchdarkly/",
                        "launchdarkly-js-client-sdk"],
            "methods": ["variation", "boolVariation", "stringVariation",
                        "numberVariation", "jsonVariation"],
        },
        "tsx": {
            "extensions": [".tsx"],
            "imports": ["launchdarkly-node-server-sdk", "@launchdarkly/",
                        "launchdarkly-js-client-sdk"],
            "methods": ["variation", "boolVariation", "stringVariation",
                        "numberVariation", "jsonVariation"],
        },
    },
}

SKIP_DIRS = {".git", "node_modules", "dist", "build", ".venv", "venv",
             "__pycache__", "target", ".tox", "eggs"}
SKIP_EXT = {".png", ".jpg", ".jpeg", ".gif", ".ico", ".woff", ".woff2",
            ".ttf", ".pdf", ".zip", ".min.js"}
MAX_FILE_BYTES = 1_000_000
MAX_FILES = 20000
MAX_FINDINGS = 2000

CONFIDENCE = 0.8  # structural match + import gate, below FlagShark high (0.9)


def provider_config_dir(provider: str, language: str) -> Path | None:
    base = (Path(__file__).resolve().parent.parent.parent
            / "piranha_configs" / "providers" / provider / language)
    if (base / "rules.toml").is_file():
        return base
    return None


def _candidate_files(repo: Path, extensions: list[str],
                     markers: list[str]) -> list[Path]:
    """Files with a matching extension that mention an SDK import marker.

    Import gating keeps precision: files without the SDK import are never
    scanned, so unrelated `variation(` calls cannot match.
    """
    out: list[Path] = []
    count = 0
    for p in repo.rglob("*"):
        if count > MAX_FILES:
            break
        try:
            if not p.is_file() or p.suffix.lower() not in extensions:
                continue
            if any(part in SKIP_DIRS for part in p.parts):
                continue
            if p.suffix.lower() in SKIP_EXT or p.stat().st_size > MAX_FILE_BYTES:
                continue
            text = p.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        count += 1
        if any(m in text for m in markers):
            out.append(p)
    return out


def _strip_quotes(token: str) -> str | None:
    t = (token or "").strip()
    if len(t) >= 2 and t[0] == t[-1] and t[0] in ("'", '"', "`"):
        inner = t[1:-1]
        # literal keys only: reject escapes/computed fragments
        if inner and "\\" not in inner and inner.strip() == inner:
            return inner
    return None


def detect_provider_references(repo: Path) -> tuple[list[dict], dict]:
    """Run verified provider match scans. Returns (findings, stats).

    Never raises: tool/config problems yield ([], {"unavailable": ...}).
    Findings are inventory (is_stale False), source-labelled ProviderAST.
    """
    findings: list[dict] = []
    stats: dict[str, object] = {"providers": {}, "unavailable": ""}
    st = piranha_service.piranha_status()
    if not st.get("available"):
        stats["unavailable"] = "polyglot-piranha unavailable"
        return findings, stats
    for provider, langs in PROVIDERS.items():
        for language, spec in langs.items():
            cfg = provider_config_dir(provider, language)
            if cfg is None:
                continue
            files = _candidate_files(repo, spec["extensions"], spec["imports"])
            if not files:
                continue
            try:
                summaries = piranha_service.run_match_scan(
                    repo, language, cfg, [str(p) for p in files])
            except piranha_service.PiranhaError as exc:
                stats.setdefault("errors", []).append(f"{provider}/{language}: {exc.code}")
                continue
            n = 0
            for s in summaries:
                rel = s.get("file", "")
                for m in s.get("matches", []):
                    if not isinstance(m, dict):
                        continue
                    caps = m.get("captures", {}) or {}
                    key = _strip_quotes(str(caps.get("key", "")))
                    if not key:
                        continue
                    method = str(caps.get("method", "") or "")
                    row = m.get("row")
                    try:
                        line = int(row) + 1 if row is not None else 0
                    except (TypeError, ValueError):
                        line = 0
                    findings.append({
                        "flag_key": key,
                        "file_path": rel,
                        "line_number": line,
                        "ast_node_type": "Unknown",
                        "is_stale": False,
                        "confidence": CONFIDENCE,
                        "reason": (f"ProviderAST({provider}): {method}() call "
                                   f"with literal key in {rel or '?'}:{line or '?'}"),
                        "language": language,
                        "provider": provider,
                        "detection_source": "ProviderAST",
                        "method": method,
                        "severity": "",
                        "confidence_tier": "high",
                        "signals": [],
                        "signal_details": "",
                        "age": None,
                    })
                    n += 1
                    if len(findings) >= MAX_FINDINGS:
                        break
                if len(findings) >= MAX_FINDINGS:
                    break
            stats["providers"][f"{provider}/{language}"] = {
                "files_scanned": len(files), "references": n}
    return findings, stats
