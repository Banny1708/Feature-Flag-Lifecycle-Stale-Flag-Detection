"""Versioned Polyglot Piranha adapter (verified against the real distribution).

Distribution: PyPI `polyglot-piranha`, PINNED `0.4.9` (manylinux wheels,
requires-python >=3.8; backend runs 3.11). Upstream: github.com/uber/piranha
(Apache-2.0), primary language now Rust; `polyglot_piranha` Python API
(`execute_piranha`, `PiranhaArguments`) verified 2026-10-24/25.

Verified contract (see Phase 3 report; never guessed):
- Languages with FlagOps-shipped, verified rule configs: python, typescript,
  tsx (tsx reuses the typescript config — verified). Anything else ->
  cleanup_status UNSUPPORTED (no regex fallback, ever).
- Execution runs in an isolated subprocess
  (`sys.executable piranha_runner.py args.json out.json`) so Rust panics
  (invalid language, missing holes, missing config dir) can never take down
  the backend worker; timeouts kill the child via PIRANHA_TIMEOUT_SEC.
- `dry_run=True` never writes files (verified via git status).
- Unknown flags / no matches -> empty summaries -> NO_CHANGES (never success).
- Missing substitution holes, unsupported language, missing config dir all
  crash the library -> the adapter validates everything BEFORE invoking.
- Piranha validates its own rewrites and refuses to emit unparseable code
  ("Produced syntactically incorrect source code" -> nonzero exit).
- Outputs: per-file summaries {path, rewrites[{rule, replacement,
  matched}], matches}. Actual before/after comes from `git diff`.

Rule configs live in `backend/piranha_configs/<lang>/` (rules.toml +
edges.toml). Seed rules rewrite flag reads in `if` conditions to the
`@treated` literal; chained rules simplify `if True/False` blocks and
boolean expressions. KNOWN LIMITATION (verified): a consequence block
containing a nested `if` is rewritten with broken Python indentation
(IndentationError); verification catches it and the operation FAILS.
"""
from __future__ import annotations

import json
import sys
import tempfile
from dataclasses import dataclass, field
from datetime import datetime, timezone
from importlib import metadata as importlib_metadata
from pathlib import Path

from ..config import get_settings
from ..utils.subprocess_util import run_cmd, which

settings = get_settings()

#: Pinned real distribution (Dockerfile installs exactly this).
PIRANHA_VERSION_PIN = "0.4.9"
PIRANHA_PACKAGE = "polyglot-piranha"

#: Languages with verified, shipped rule configs. tsx reuses typescript/.
SUPPORTED_LANGUAGES = ("python", "typescript", "tsx")
_CONFIG_DIR_FOR = {"python": "python", "typescript": "typescript", "tsx": "typescript"}

#: permanent_value -> per-language boolean literal (verified: lowercase
#: `true` in Python produces an identifier, NOT a literal, and silently
#: disables all cleanup chaining).
_LANGUAGE_LITERAL = {
    "python": {"true": "True", "false": "False"},
    "typescript": {"true": "true", "false": "false"},
    "tsx": {"true": "true", "false": "false"},
}

_TRUE_TOKENS = {"true", "1", "yes", "y", "on"}
_FALSE_TOKENS = {"false", "0", "no", "n", "off"}

_RUNNER = str(Path(__file__).resolve().parent / "piranha_runner.py")


class PiranhaError(Exception):
    """Structured adapter failure. `code` is machine-readable and safe to
    expose; `message` never contains credentials (none are ever used)."""

    def __init__(self, code: str, message: str):
        super().__init__(f"[{code}] {message}")
        self.code = code
        self.message = message


@dataclass
class PiranhaConfig:
    """Validated cleanup request. Only verified fields — nothing invented."""
    language: str            # one of SUPPORTED_LANGUAGES
    flag_key: str
    treated_literal: str     # language-specific boolean literal
    config_dir: str          # verified directory with rules.toml + edges.toml
    dry_run: bool = False


@dataclass
class PiranhaFileResult:
    path: str
    rewrites: list[dict] = field(default_factory=list)
    matches: int = 0


@dataclass
class PiranhaResult:
    """Outcome of one adapter invocation."""
    ok: bool
    cleanup_status: str      # APPLIED | NO_CHANGES | DRY_RUN_OK | (errors raise)
    files_changed: list[str] = field(default_factory=list)
    rewrites: list[dict] = field(default_factory=list)
    # Raw per-file match details (used by provider detection).
    raw_summaries: list[dict] = field(default_factory=list)
    stdout: str = ""
    stderr: str = ""
    timed_out: bool = False
    exit_code: int | None = None


def piranha_version() -> str:
    try:
        return importlib_metadata.version(PIRANHA_PACKAGE)
    except Exception:
        return "UNAVAILABLE"


def piranha_status() -> dict:
    """Probe the real library (import + version), never a guessed binary."""
    ver = piranha_version()
    if ver == "UNAVAILABLE" or ver != PIRANHA_VERSION_PIN:
        note = (f"expected {PIRANHA_PACKAGE}=={PIRANHA_VERSION_PIN}"
                if ver == "UNAVAILABLE" else
                f"installed {ver} != pinned {PIRANHA_VERSION_PIN}")
        return {"available": False, "path": "", "version": ver,
                "hint": f"{note}. Install the pinned version: "
                        f"pip install {PIRANHA_PACKAGE}=={PIRANHA_VERSION_PIN}",
                "languages": []}
    import polyglot_piranha  # noqa: F401 (importability proof)
    return {"available": True, "path": __file__,
            "version": ver,
            "hint": "",
            "languages": list(SUPPORTED_LANGUAGES)}


def repo_language_to_piranha(repo_language: str | None) -> str | None:
    """Map a repository language label to a verified Piranha language.

    Returns None for anything unverified (JavaScript/JSX/Java/Go/...):
    those become cleanup_status UNSUPPORTED, never a guessed cleanup.
    """
    lang = (repo_language or "").strip().lower()
    mapping = {"python": "python", "py": "python",
               "typescript": "typescript", "ts": "typescript",
               "tsx": "tsx"}
    return mapping.get(lang)


def parse_permanent_value(value: str | None, language: str) -> str:
    """Map a user permanent value to the language boolean literal."""
    v = (value or "").strip().lower()
    if v in _TRUE_TOKENS:
        key = "true"
    elif v in _FALSE_TOKENS:
        key = "false"
    else:
        raise PiranhaError("INVALID_VALUE",
                           f"permanent_value must be a boolean (got {str(value)[:40]!r})")
    return _LANGUAGE_LITERAL[language][key]


def packaged_config_dir(language: str) -> Path:
    """Verified shipped configs. Raises CONFIG_MISSING if incomplete."""
    if language not in _CONFIG_DIR_FOR:
        raise PiranhaError("UNSUPPORTED_LANGUAGE",
                           f"language '{language}' has no verified Piranha rule configuration")
    d = (Path(__file__).resolve().parent.parent.parent
         / "piranha_configs" / _CONFIG_DIR_FOR[language])
    rules, edges = d / "rules.toml", d / "edges.toml"
    if not rules.is_file() or not edges.is_file():
        raise PiranhaError("CONFIG_MISSING",
                           f"rule configuration incomplete for '{language}' "
                           f"(expected rules.toml + edges.toml in {d})")
    return d


def build_config(language: str, flag_key: str, permanent_value: str | None,
                 dry_run: bool = False) -> PiranhaConfig:
    """Validate everything Piranha would crash on, before invoking it."""
    if language not in SUPPORTED_LANGUAGES:
        raise PiranhaError("UNSUPPORTED_LANGUAGE",
                           f"language '{language}' has no verified Piranha rule "
                           f"configuration (supported: {', '.join(SUPPORTED_LANGUAGES)})")
    key = (flag_key or "").strip()
    if not key:
        raise PiranhaError("INVALID_FLAG", "flag key is empty")
    treated = parse_permanent_value(permanent_value, language)
    config_dir = packaged_config_dir(language)
    return PiranhaConfig(language=language, flag_key=key,
                         treated_literal=treated,
                         config_dir=str(config_dir), dry_run=dry_run)


def run_cleanup(repo: Path, config: PiranhaConfig) -> PiranhaResult:
    """Execute Piranha in an isolated subprocess against the workspace.

    dry_run=True never modifies files. Real runs modify the worktree in
    place (caller must be on a safety branch); the actual diff is captured
    separately via capture_diff().
    """
    return _run_paths(
        repo, config.language, config.config_dir,
        {"flag_name": config.flag_key, "treated": config.treated_literal},
        dry_run=config.dry_run)


def run_match_scan(repo: Path, language: str, config_dir: Path,
                   paths: list[str]) -> list[dict]:
    """Match-only scan (no holes, no rewrites): returns raw file summaries.

    Used by provider detection. Never modifies files (always dry-run).
    Raises PiranhaError on tool failure; callers treat failure as no data.
    """
    result = _run_paths(repo, language, str(config_dir), {},
                        dry_run=True, paths=paths)
    return result.raw_summaries


def _run_paths(repo: Path, language: str, config_dir: str,
               substitutions: dict, dry_run: bool,
               paths: list[str] | None = None) -> PiranhaResult:
    """Shared subprocess invocation. `paths` overrides the default [repo]."""
    targets = paths if paths else [str(repo)]
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as af:
        json.dump({"language": language,
                   "paths_to_codebase": targets,
                   "path_to_configurations": config_dir,
                   "substitutions": substitutions,
                   "dry_run": dry_run}, af)
        args_path = af.name
    out_path = args_path + ".out.json"
    try:
        r = run_cmd([sys.executable, _RUNNER, args_path, out_path],
                    cwd=str(repo), timeout=settings.PIRANHA_TIMEOUT_SEC)
    finally:
        Path(args_path).unlink(missing_ok=True)
    if r.timed_out:
        Path(out_path).unlink(missing_ok=True)
        raise PiranhaError("TIMEOUT",
                           f"Piranha exceeded {settings.PIRANHA_TIMEOUT_SEC}s and was "
                           f"terminated; workspace may be partially modified — "
                           f"restore the safety branch before retrying")
    if r.returncode != 0:
        Path(out_path).unlink(missing_ok=True)
        tail = ((r.stderr or "") + "\n" + (r.stdout or "")).strip().splitlines()
        detail = tail[-1][-500:] if tail and tail[-1].strip() else ""
        raise PiranhaError("EXECUTION_FAILED",
                           f"Piranha exited with code {r.returncode} ({detail or 'no output'})")
    try:
        payload = json.loads(Path(out_path).read_text(encoding="utf-8"))
        summaries = payload.get("summaries", [])
        if not isinstance(summaries, list):
            raise ValueError("summaries is not a list")
    except Exception as exc:
        raise PiranhaError("BAD_OUTPUT",
                           f"Piranha produced unparseable output: {exc}") from exc
    finally:
        Path(out_path).unlink(missing_ok=True)
    files: list[PiranhaFileResult] = []
    for s in (summaries or []):
        if not isinstance(s, dict):
            continue
        raw_path = str(s.get("path", ""))
        try:
            rel = str(Path(raw_path).resolve().relative_to(repo.resolve()))
        except ValueError:
            rel = raw_path  # outside the repo: keep verbatim for auditability
        files.append(PiranhaFileResult(path=rel,
                                       rewrites=list(s.get("rewrites", []) or []),
                                       matches=len(s.get("matches", []) or [])
                                       if isinstance(s.get("matches"), list)
                                       else int(s.get("matches", 0) or 0)))
    changed = [f.path for f in files if f.rewrites]
    rewrites = [{"file": f.path, **rw} for f in files for rw in f.rewrites]
    dicts = [s for s in (summaries or []) if isinstance(s, dict)]
    raw_matches = [{"file": f.path,
                    "matches": list(s.get("matches", []) or [])}
                   for f, s in zip(files, dicts)]
    if dry_run:
        status = "DRY_RUN_OK"
    else:
        status = "APPLIED" if changed else "NO_CHANGES"
    return PiranhaResult(ok=True, cleanup_status=status,
                         files_changed=changed, rewrites=rewrites,
                         raw_summaries=raw_matches,
                         stdout=(r.stdout or "")[-4000:],
                         stderr=(r.stderr or "")[-4000:],
                         exit_code=r.returncode)


def capture_diff(repo: Path, max_chars: int = 60000) -> dict:
    """Capture the ACTUAL git diff (unified) plus stat/numstat counts."""
    diff = run_cmd([settings.GIT_BIN, "diff", "--no-ext-diff"], cwd=str(repo), timeout=60)
    stat = run_cmd([settings.GIT_BIN, "diff", "--stat"], cwd=str(repo), timeout=30)
    numstat = run_cmd([settings.GIT_BIN, "diff", "--numstat"], cwd=str(repo), timeout=30)
    files = run_cmd([settings.GIT_BIN, "diff", "--name-only"], cwd=str(repo), timeout=30)
    added = removed = 0
    for line in (numstat.stdout or "").splitlines():
        parts = line.split()
        if len(parts) >= 2:
            try:
                added += int(parts[0]); removed += int(parts[1])
            except ValueError:
                pass
    return {"unified": (diff.stdout or "")[:max_chars],
            "stat": (stat.stdout or "")[:4000],
            "files": [f for f in (files.stdout or "").splitlines() if f.strip()],
            "lines_added": added, "lines_removed": removed}


def create_safety_branch(repo: Path, flag_key: str) -> dict:
    """Unchanged safety mechanism: timestamped branch + recorded base commit."""
    ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    branch = f"flagops-safety-{flag_key.lower()[:32]}-{ts}"
    base = run_cmd([settings.GIT_BIN, "rev-parse", "HEAD"], cwd=str(repo), timeout=15)
    base_commit = base.stdout.strip() if base.returncode == 0 else "UNAVAILABLE"
    r = run_cmd([settings.GIT_BIN, "checkout", "-b", branch], cwd=str(repo), timeout=30)
    if r.returncode != 0:
        return {"ok": False, "branch": "", "base_commit": base_commit,
                "error": (r.stderr or r.stdout)[-2000:]}
    return {"ok": True, "branch": branch, "base_commit": base_commit, "error": ""}


def restore_workspace(repo: Path, base_commit: str) -> dict:
    """Restore tracked files to the recorded safety base (`git reset --hard`).

    Used by rollback when base_commit is a valid SHA. Returns ok/error.
    Untracked files are left alone (Piranha never creates them with the
    shipped configuration: delete_file_if_empty is off).
    """
    if not base_commit or base_commit == "UNAVAILABLE":
        return {"ok": False, "error": "no valid base commit recorded; cannot restore"}
    verify = run_cmd([settings.GIT_BIN, "rev-parse", "--verify", base_commit],
                     cwd=str(repo), timeout=15)
    if verify.returncode != 0:
        return {"ok": False,
                "error": f"recorded base commit is not a valid revision: {base_commit[:40]}"}
    r = run_cmd([settings.GIT_BIN, "reset", "--hard", base_commit],
                cwd=str(repo), timeout=60)
    if r.returncode != 0:
        return {"ok": False, "error": (r.stderr or r.stdout)[-2000:]}
    status = run_cmd([settings.GIT_BIN, "status", "--porcelain"],
                     cwd=str(repo), timeout=30)
    dirty = [l for l in (status.stdout or "").splitlines()
             if l.strip() and not l.startswith("??")]
    if dirty:
        return {"ok": False,
                "error": f"worktree still dirty after reset: {dirty[:5]}"}
    return {"ok": True, "error": ""}


def verify_python_syntax(paths: list[str], repo: Path) -> list[str]:
    """Compile-check changed Python files. Returns list of failure messages."""
    import py_compile
    failures = []
    for rel in paths:
        if not rel.endswith(".py"):
            continue
        p = (repo / rel)
        # stay inside the repo (defense against weird diff paths)
        try:
            p.resolve().relative_to(repo.resolve())
        except ValueError:
            failures.append(f"{rel}: path escapes repository")
            continue
        if not p.is_file():
            continue
        try:
            py_compile.compile(str(p), doraise=True)
        except Exception as exc:
            failures.append(f"{rel}: {exc}")
    return failures
