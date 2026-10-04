"""Read-only Git evidence collection. Never mutates the repo (except safety branches in piranha flow)."""
from __future__ import annotations

from pathlib import Path

from ..config import get_settings
from ..utils.subprocess_util import run_cmd, which

settings = get_settings()


def git_available() -> tuple[bool, str]:
    path = which(settings.GIT_BIN)
    if not path:
        return False, ""
    r = run_cmd([settings.GIT_BIN, "--version"], timeout=15)
    return (r.returncode == 0, (r.stdout or r.stderr).strip())


def is_git_repo(path: Path) -> bool:
    r = run_cmd([settings.GIT_BIN, "rev-parse", "--git-dir"], cwd=str(path), timeout=15)
    return r.returncode == 0


def collect_git_evidence(path: Path) -> dict:
    """Return real git facts; missing data -> 'UNAVAILABLE', never invented."""
    avail, version = git_available()
    if not avail:
        return {"available": False, "reason": "git binary not found", "version": "UNAVAILABLE"}
    if not is_git_repo(path):
        return {"available": False, "reason": "not a git repository", "version": version}

    def g(*args: str, timeout: int = 30) -> str:
        r = run_cmd([settings.GIT_BIN, *args], cwd=str(path), timeout=timeout)
        return r.stdout.strip() if r.returncode == 0 else "UNAVAILABLE"

    branch = g("rev-parse", "--abbrev-ref", "HEAD")
    commit = g("rev-parse", "HEAD")
    status = g("status", "--porcelain")
    log = run_cmd(
        [settings.GIT_BIN, "log", "--pretty=format:%H|%ad|%s", "--date=iso", "-n", "20"],
        cwd=str(path),
        timeout=30,
    )
    commits: list[dict] = []
    if log.returncode == 0:
        for line in log.stdout.strip().splitlines():
            parts = line.split("|", 2)
            if len(parts) == 3:
                commits.append({"hash": parts[0], "date": parts[1], "subject": parts[2]})

    first_commit = g("log", "--reverse", "--pretty=format:%ad", "--date=iso", "--max-count=1")
    last_commit = g("log", "--pretty=format:%ad", "--date=iso", "--max-count=1")
    remotes = g("remote", "-v")
    diff_stat = g("diff", "--stat")
    return {
        "available": True,
        "version": version,
        "branch": branch,
        "commit": commit,
        "clean": len(status.strip()) == 0,
        "status_porcelain": status[:4000],
        "recent_commits": commits,
        "first_commit_date": first_commit,
        "last_commit_date": last_commit,
        "remotes": remotes[:2000],
        "diff_stat": diff_stat[:4000],
    }


def flag_git_history(path: Path, flag_key: str, limit: int = 20) -> dict:
    """git log -S flag_key: real flag-related commits. Read-only."""
    avail, _ = git_available()
    if not avail or not is_git_repo(path):
        return {"available": False, "commits": []}
    r = run_cmd(
        [settings.GIT_BIN, "log", f"-S{flag_key}", "--pretty=format:%H|%ad|%an|%s",
         "--date=iso", "-n", str(limit)],
        cwd=str(path),
        timeout=60,
    )
    commits: list[dict] = []
    if r.returncode == 0 and r.stdout.strip():
        for line in r.stdout.strip().splitlines():
            parts = line.split("|", 3)
            if len(parts) == 4:
                commits.append({"hash": parts[0], "date": parts[1], "author": parts[2], "subject": parts[3]})
    # last modification of files mentioning the flag
    r2 = run_cmd(
        [settings.GIT_BIN, "log", "-1", "--pretty=format:%ad", "--date=iso", f"-S{flag_key}"],
        cwd=str(path),
        timeout=30,
    )
    last_touch = r2.stdout.strip() if r2.returncode == 0 else "UNAVAILABLE"
    return {"available": True, "commits": commits, "last_touch": last_touch, "count": len(commits)}


def file_history(path: Path, rel_file: str, limit: int = 10) -> list[dict]:
    if not is_git_repo(path):
        return []
    r = run_cmd(
        [settings.GIT_BIN, "log", "--pretty=format:%H|%ad|%s", "--date=iso", "-n", str(limit), "--", rel_file],
        cwd=str(path),
        timeout=30,
    )
    out: list[dict] = []
    if r.returncode == 0:
        for line in r.stdout.strip().splitlines():
            parts = line.split("|", 2)
            if len(parts) == 3:
                out.append({"hash": parts[0], "date": parts[1], "subject": parts[2]})
    return out
