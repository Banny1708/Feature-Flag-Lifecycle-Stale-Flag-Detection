"""Real repository ingestion: validate URL -> clone with git -> isolated workspace.

Phase 1 scope only: public GitHub HTTPS cloning (plus optional token auth via the
existing `github_token` system setting). No FlagShark, no Piranha, no fake data.

Security rules enforced here:
- subprocess arg arrays only, never shell=True (via utils.subprocess_util).
- access tokens are never written to the DB, metadata.json, logs, errors, or audit.
- all captured git output is sanitized (token redacted) before it leaves this module.
- managed workspaces are confined to WORKSPACE_DIR/repositories/<repo-id>/.

Error categories (CloneError.code): INVALID_URL, REPOSITORY_NOT_FOUND,
AUTHENTICATION_FAILED, BRANCH_NOT_FOUND, NETWORK_ERROR, GIT_UNAVAILABLE,
CLONE_TIMEOUT, WORKSPACE_ERROR, UNKNOWN_GIT_ERROR.
"""
from __future__ import annotations

import json
import os
import re
import shutil
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

from ..config import get_settings
from ..utils.subprocess_util import run_cmd, which
from . import git_service

settings = get_settings()

REDACTED = "***REDACTED***"

# Strictly: https://github.com/<owner>/<repo>[.git][/...]
_GITHUB_PATH_RE = re.compile(r"^/([^/]+)/([^/]+?)(?:\.git)?/?$")

# repo ids come from utils.helpers.new_id -> "<prefix>-<hex>"; allow only that shape
# for workspace path derivation so traversal is impossible.
_REPO_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$")


class CloneError(Exception):
    """Structured clone failure. `code` is machine-readable, `message` is safe
    for API responses (never contains credentials)."""

    def __init__(self, code: str, message: str):
        super().__init__(f"[{code}] {message}")
        self.code = code
        self.message = message


def sanitize(text: str, secrets: list[str] | None = None) -> str:
    """Redact any credential material from text before logging/returning."""
    out = text or ""
    for s in secrets or []:
        if s and len(s) >= 4 and s in out:
            out = out.replace(s, REDACTED)
    # generic bearer-token shaped leftovers are redacted defensively
    out = re.sub(r"(?i)(bearer\s+)[A-Za-z0-9_.\-~+/=]{8,}", r"\1" + REDACTED, out)
    return out


def validate_repository_url(url: str) -> dict:
    """Validate a GitHub HTTPS repository URL. Returns owner/repo/name.

    Raises CloneError(INVALID_URL) for anything that is not clearly a
    https://github.com/<owner>/<repo> URL. SSH, file://, bare paths and
    non-GitHub hosts are rejected here (local checkouts use MODE B instead).
    """
    raw = (url or "").strip()
    if not raw:
        raise CloneError("INVALID_URL", "repository URL is empty")
    try:
        parsed = urlparse(raw)
    except Exception:
        raise CloneError("INVALID_URL", f"not a valid URL: {raw[:120]}")
    if parsed.scheme != "https":
        raise CloneError("INVALID_URL", "only HTTPS repository URLs are supported (got "
                         f"scheme '{parsed.scheme or '?'}')")
    host = (parsed.hostname or "").lower()
    if host != "github.com":
        raise CloneError("INVALID_URL", f"only github.com URLs are supported (got '{host or '?'}')")
    if parsed.username or parsed.password:
        raise CloneError("INVALID_URL", "credentials must not be embedded in the repository URL; "
                         "configure github_token in Settings for private repositories")
    m = _GITHUB_PATH_RE.match(parsed.path or "")
    if not m:
        raise CloneError("INVALID_URL", "URL must look like https://github.com/<owner>/<repo>")
    owner, name = m.group(1), m.group(2)
    if owner in (".", "..") or name in (".", ".."):
        raise CloneError("INVALID_URL", "invalid owner/repository in URL")
    canonical = f"https://github.com/{owner}/{name}"
    return {"owner": owner, "name": name, "full_name": f"{owner}/{name}",
            "canonical_url": canonical}


def _validate_repo_id(repo_id: str) -> str:
    rid = (repo_id or "").strip()
    if not _REPO_ID_RE.match(rid):
        raise CloneError("WORKSPACE_ERROR", "invalid repository id for workspace use")
    return rid


def managed_repo_dir(workspace: str, repo_id: str) -> Path:
    """Return WORKSPACE_DIR/repositories/<repo-id>, confined to the workspace.

    Resolves symlinks and refuses anything escaping the workspace root.
    """
    rid = _validate_repo_id(repo_id)
    root = Path(workspace).expanduser().resolve()
    target = (root / "repositories" / rid).resolve()
    # ensure target stays inside <root>/repositories even with symlinks present
    try:
        target.relative_to((root / "repositories").resolve())
    except ValueError:
        raise CloneError("WORKSPACE_ERROR", "workspace path escapes the managed workspace")
    return target


def source_dir(workspace: str, repo_id: str) -> Path:
    return managed_repo_dir(workspace, repo_id) / "source"


def _classify_clone_error(stderr: str, stdout: str, returncode: int) -> tuple[str, str]:
    """Map git stderr to a stable error category + human message (no secrets)."""
    blob = f"{stderr}\n{stdout}".lower()
    if "could not resolve host" in blob or "failed to connect" in blob \
            or "network is unreachable" in blob or "connection timed out" in blob \
            or "unable to access" in blob and ("could not resolve" in blob or "connect" in blob):
        return ("NETWORK_ERROR",
                "network error reaching github.com; check connectivity and proxy settings")
    if "repository not found" in blob or "not found" in blob and "repository" in blob \
            or "the requested url returned error: 404" in blob:
        return ("REPOSITORY_NOT_FOUND",
                "repository not found on github.com; check the URL or access rights")
    if "authentication failed" in blob or "could not read username" in blob \
            or "invalid username or password" in blob or "401" in blob and "authorization" in blob \
            or "403" in blob and "rate limit" not in blob and "denied" in blob \
            or "permission denied" in blob or "empty password" in blob:
        return ("AUTHENTICATION_FAILED",
                "authentication failed; the repository may be private — "
                "configure a github_token in Settings and retry")
    if "couldn't find remote ref" in blob or "remote branch" in blob and "not found" in blob:
        return ("BRANCH_NOT_FOUND", "requested branch was not found in the remote repository")
    if "rate limit" in blob or "429" in blob:
        return ("NETWORK_ERROR",
                "github.com rate limit reached; retry later or configure a github_token in Settings")
    return ("UNKNOWN_GIT_ERROR",
            f"git clone failed (exit {returncode}); see backend logs for sanitized details")


def _write_metadata(repo_dir: Path, payload: dict) -> None:
    """Persist clone metadata. Must never contain credentials (enforced by caller)."""
    meta = dict(payload)
    meta.pop("access_token", None)
    meta.pop("token", None)
    (repo_dir / "metadata.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")


def build_clone_cmd(canonical_url: str, dest: str, branch: str = "",
                    token: str = "") -> list[str]:
    """Build the verified clone argv (arg list only, never executed here).

    Full clone (NO --depth): FlagShark skips ALL git-blame age signals on
    shallow clones (verified: `git rev-parse --is-shallow-repository` gate
    in its staleness engine), so shallow workspaces would silently lose the
    primary stale signal. Full history is required for honest detection.
    """
    cmd = [settings.GIT_BIN]
    if (token or "").strip():
        cmd += ["-c", f"http.extraHeader=AUTHORIZATION: bearer {token.strip()}"]
    cmd += ["clone"]
    if (branch or "").strip():
        cmd += ["--branch", branch.strip()]
    cmd += ["--", canonical_url, dest]
    return cmd


def clone_repository(repository_url: str, repo_id: str, branch: str = "",
                      access_token: str | None = None,
                      timeout: int | None = None) -> dict:
    """Clone a GitHub repo into its isolated workspace. Returns structured info.

    Layout: WORKSPACE_DIR/repositories/<repo-id>/source (+ metadata.json).
    Raises CloneError on any failure; partial workspaces are always removed.
    """
    from ..utils.helpers import utcnow_iso  # local import: avoid circulars

    info = validate_repository_url(repository_url)
    rid = _validate_repo_id(repo_id)
    ws = settings.WORKSPACE_DIR
    repo_dir = managed_repo_dir(ws, rid)
    dest = repo_dir / "source"
    token = (access_token or "").strip() or ""
    secrets = [token] if token else []
    timeout_sec = timeout or settings.CLONE_TIMEOUT_SEC

    git_bin = which(settings.GIT_BIN)
    if not git_bin:
        raise CloneError("GIT_UNAVAILABLE", f"'{settings.GIT_BIN}' binary not found on PATH")

    try:
        repo_dir.mkdir(parents=True, exist_ok=True)
    except Exception as exc:
        raise CloneError("WORKSPACE_ERROR", f"cannot create workspace directory: {exc}") from exc
    if dest.exists():
        shutil.rmtree(repo_dir, ignore_errors=True)
        raise CloneError("WORKSPACE_ERROR", "workspace already exists for this repository id")

    # -c http.extraHeader carries auth without touching remote URL / on-disk config.
    # GIT_TERMINAL_PROMPT=0 prevents interactive credential hangs.
    cmd = build_clone_cmd(info["canonical_url"], str(dest),
                           branch=(branch or "").strip(), token=token)

    env = dict(os.environ)
    env["GIT_TERMINAL_PROMPT"] = "0"

    import subprocess

    def _run(clone_cmd: list[str]):
        return subprocess.run(clone_cmd, capture_output=True, text=True,
                              timeout=timeout_sec, env=env)

    try:
        proc = _run(cmd)
        timed_out = False
    except subprocess.TimeoutExpired as exc:
        out = exc.stdout if isinstance(exc.stdout, str) else ""
        err = exc.stderr if isinstance(exc.stderr, str) else ""
        shutil.rmtree(repo_dir, ignore_errors=True)
        raise CloneError("CLONE_TIMEOUT",
                         f"clone timed out after {timeout_sec}s; incomplete workspace removed. "
                         f"sanitized output: {sanitize((err or out)[-500:], secrets)}") from exc
    except FileNotFoundError as exc:
        shutil.rmtree(repo_dir, ignore_errors=True)
        raise CloneError("GIT_UNAVAILABLE", f"git binary not found: {exc}") from exc
    except Exception as exc:
        shutil.rmtree(repo_dir, ignore_errors=True)
        raise CloneError("UNKNOWN_GIT_ERROR",
                         f"clone subprocess error: {sanitize(str(exc), secrets)[:300]}") from exc

    stderr = sanitize((proc.stderr or "")[-4000:], secrets)
    stdout = sanitize((proc.stdout or "")[-4000:], secrets)
    if proc.returncode != 0:
        code, message = _classify_clone_error(stderr, stdout, proc.returncode)
        if code == "BRANCH_NOT_FOUND" and (branch or "").strip():
            # Requested branch doesn't exist upstream (e.g. assumed "main" vs
            # actual "master"): retry with the remote's default branch.
            shutil.rmtree(repo_dir, ignore_errors=True)
            repo_dir.mkdir(parents=True, exist_ok=True)
            retry = [c for c in cmd if c != "--branch" and c != branch.strip()]
            try:
                proc = _run(retry)
            except subprocess.TimeoutExpired as exc:
                shutil.rmtree(repo_dir, ignore_errors=True)
                raise CloneError("CLONE_TIMEOUT",
                                 f"clone timed out after {timeout_sec}s; incomplete workspace removed.") from exc
            stderr = sanitize((proc.stderr or "")[-4000:], secrets)
            stdout = sanitize((proc.stdout or "")[-4000:], secrets)
            if proc.returncode != 0:
                shutil.rmtree(repo_dir, ignore_errors=True)
                code, message = _classify_clone_error(stderr, stdout, proc.returncode)
                detail = (stderr.splitlines() or [""])[-1][-200:] if stderr.strip() else ""
                raise CloneError(code, f"{message} ({detail})" if detail else message)
        else:
            shutil.rmtree(repo_dir, ignore_errors=True)
            # keep a sanitized tail for operators without leaking anything sensitive
            detail = (stderr.splitlines() or [""])[-1][-200:] if stderr.strip() else ""
            raise CloneError(code, f"{message} ({detail})" if detail else message)

    if not git_service.is_git_repo(dest):
        shutil.rmtree(repo_dir, ignore_errors=True)
        raise CloneError("UNKNOWN_GIT_ERROR",
                         "clone completed but the directory is not a valid git repository; "
                         "workspace removed")

    evidence = git_service.collect_git_evidence(dest)
    if not evidence.get("available"):
        shutil.rmtree(repo_dir, ignore_errors=True)
        raise CloneError("UNKNOWN_GIT_ERROR",
                         f"cloned repository failed git verification ({evidence.get('reason', 'unknown')}); "
                         "workspace removed")

    result = {
        "repository_id": rid,
        "source_url": info["canonical_url"],
        "local_path": str(dest),
        "branch": evidence.get("branch", "") or (branch or "").strip(),
        "commit_hash": evidence.get("commit", ""),
        "remote_url": info["canonical_url"],
        "owner": info["owner"],
        "name": info["name"],
        "full_name": info["full_name"],
        "cloned_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "managed": True,
    }
    _write_metadata(repo_dir, {**result,
                               "default_branch": result["branch"]})
    return result
