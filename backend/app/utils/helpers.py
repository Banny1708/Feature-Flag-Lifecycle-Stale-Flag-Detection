from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone
from pathlib import Path


def new_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


def utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def safe_repo_path(path: str, workspace: str) -> Path:
    """Validate a repository path: must exist, must be inside workspace OR be a git repo the user explicitly pointed at.

    We allow absolute paths that exist, but resolve symlinks and reject clearly invalid inputs.
    We never delete anything here.
    """
    p = Path(path).expanduser()
    if not p.is_absolute():
        p = (Path(workspace).resolve() / p).resolve()
    else:
        p = p.resolve()
    if not p.exists() or not p.is_dir():
        raise ValueError(f"repository path does not exist or is not a directory: {p}")
    return p


def ensure_workspace(workspace: str) -> Path:
    ws = Path(workspace).expanduser().resolve()
    ws.mkdir(parents=True, exist_ok=True)
    return ws


def parse_boolish(value: str) -> bool | str | int:
    v = (value or "").strip().lower()
    if v in ("true", "1", "yes"):
        return True
    if v in ("false", "0", "no"):
        return False
    try:
        return int(value)
    except Exception:
        return value
