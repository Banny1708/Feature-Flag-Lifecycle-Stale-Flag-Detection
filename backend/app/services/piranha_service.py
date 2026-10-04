"""Real Piranha invocation with Git safety point. Never auto-removes without explicit call."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from ..config import get_settings
from ..utils.subprocess_util import run_cmd, which

settings = get_settings()


def piranha_status() -> dict:
    path = which(settings.PIRANHA_BIN)
    if not path:
        return {"available": False, "path": "", "version": "UNAVAILABLE",
                "hint": f"'{settings.PIRANHA_BIN}' not found on PATH. Install Piranha to enable automated removal."}
    r = run_cmd([settings.PIRANHA_BIN, "--help"], timeout=20)
    return {"available": True, "path": path, "version": ((r.stdout or "") + (r.stderr or ""))[:500], "hint": ""}


def create_safety_branch(repo: Path, flag_key: str) -> dict:
    ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    branch = f"flagops-safety-{flag_key.lower()[:32]}-{ts}"
    base = run_cmd([settings.GIT_BIN, "rev-parse", "HEAD"], cwd=str(repo), timeout=15)
    base_commit = base.stdout.strip() if base.returncode == 0 else "UNAVAILABLE"
    r = run_cmd([settings.GIT_BIN, "checkout", "-b", branch], cwd=str(repo), timeout=30)
    if r.returncode != 0:
        return {"ok": False, "branch": "", "base_commit": base_commit,
                "error": (r.stderr or r.stdout)[-2000:]}
    return {"ok": True, "branch": branch, "base_commit": base_commit, "error": ""}


def run_piranha(repo: Path, flag_key: str, permanent_value: str = "false") -> dict:
    """Execute piranha against repo. Tries common CLI shapes; captures everything."""
    st = piranha_status()
    if not st["available"]:
        return {"ok": False, "error": st["hint"], "stdout": "", "stderr": "",
                "changed_files": [], "diff_stat": "", "available": False}
    shapes = [
        [settings.PIRANHA_BIN, "--path", str(repo), "--flag", flag_key, "--value", permanent_value],
        [settings.PIRANHA_BIN, "clean", "--path", str(repo), "--flag", flag_key],
        [settings.PIRANHA_BIN, str(repo), flag_key, permanent_value],
    ]
    last = None
    for shape in shapes:
        r = run_cmd(shape, cwd=str(repo), timeout=settings.PIRANHA_TIMEOUT_SEC)
        last = r
        if r.returncode == 0:
            break
    assert last is not None
    files = run_cmd([settings.GIT_BIN, "diff", "--name-only"], cwd=str(repo), timeout=30)
    stat = run_cmd([settings.GIT_BIN, "diff", "--stat"], cwd=str(repo), timeout=30)
    numstat = run_cmd([settings.GIT_BIN, "diff", "--numstat"], cwd=str(repo), timeout=30)
    added = removed = 0
    for line in (numstat.stdout or "").splitlines():
        parts = line.split()
        if len(parts) >= 2:
            try:
                added += int(parts[0]); removed += int(parts[1])
            except ValueError:
                pass
    changed = [f for f in (files.stdout or "").splitlines() if f.strip()]
    return {"ok": last.returncode == 0 and not last.timed_out,
            "error": "" if last.returncode == 0 else (last.stderr or last.stdout)[-4000:],
            "stdout": last.stdout[-20000:], "stderr": last.stderr[-20000:],
            "changed_files": changed, "diff_stat": (stat.stdout or "")[:4000],
            "lines_added": added, "lines_removed": removed, "available": True,
            "timed_out": last.timed_out}
