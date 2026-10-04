"""Evidence engine: every item comes from git / scan / FS inspection. No invention."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from . import git_service


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _days_between(iso_a: str, iso_b: str) -> int | None:
    try:
        a = datetime.fromisoformat(iso_a.replace("Z", "+00:00"))
        b = datetime.fromisoformat(iso_b.replace("Z", "+00:00"))
        return abs((b - a).days)
    except Exception:
        return None


def build_evidence(repo_path: Path, flag_key: str, flag_row=None,
                   git_info: dict | None = None, refs: list[dict] | None = None,
                   scan_info: dict | None = None) -> list[dict]:
    git_info = git_info if git_info is not None else git_service.collect_git_evidence(repo_path)
    hist = git_service.flag_git_history(repo_path, flag_key)
    refs = refs or []
    out: list[dict] = []
    now = _iso_now()

    # FLAG_AGE from git history of the flag token
    if hist.get("available") and hist.get("commits"):
        last = hist["commits"][0]["date"]
        days = _days_between(last, now)
        out.append({
            "evidence_type": "code-commit-staleness",
            "severity": "HIGH" if (days or 0) > 180 else ("MEDIUM" if (days or 0) > 90 else "LOW"),
            "value": f"{days} days since last flag-related commit" if days is not None else last,
            "source": "git",
            "summary": f"Last commit touching '{flag_key}' was {days} days ago." if days is not None else f"Last touch: {last}",
            "confidence_score": 0.85,
            "payload": {"last_touch": last, "related_commits": len(hist["commits"])},
        })
    elif git_info.get("available"):
        last = git_info.get("last_commit_date", "UNAVAILABLE")
        out.append({
            "evidence_type": "code-commit-staleness",
            "severity": "LOW",
            "value": str(last),
            "source": "git",
            "summary": f"No git history found for token '{flag_key}'; repo last commit {last}.",
            "confidence_score": 0.4,
            "payload": {"last_repo_commit": last, "related_commits": 0},
        })
    else:
        out.append({
            "evidence_type": "code-commit-staleness",
            "severity": "LOW",
            "value": "UNAVAILABLE",
            "source": "git",
            "summary": f"Git unavailable: {git_info.get('reason', 'unknown')}.",
            "confidence_score": 0.2,
            "payload": {"reason": git_info.get("reason", "unknown")},
        })

    # REFERENCE_COUNT from actual scan
    out.append({
        "evidence_type": "ast-unreachable" if not refs else "code-commit-staleness",
        "severity": "HIGH" if len(refs) == 0 else ("MEDIUM" if len(refs) == 1 else "LOW"),
        "value": str(len(refs)),
        "source": (scan_info or {}).get("engine", "scan"),
        "summary": f"{len(refs)} source reference(s) to '{flag_key}' found in latest scan."
                   + (" Zero references suggests dead code." if not refs else ""),
        "confidence_score": 0.9 if refs else 0.7,
        "payload": {"reference_count": len(refs),
                    "files": sorted({r.get("file_path", "") for r in refs})[:10]},
    })

    # REPO_STATE from git status
    if git_info.get("available"):
        out.append({
            "evidence_type": "pr-closure",
            "severity": "MEDIUM" if not git_info.get("clean", True) else "LOW",
            "value": git_info.get("branch", "UNAVAILABLE"),
            "source": "git",
            "summary": f"Repo on branch '{git_info.get('branch')}', commit {str(git_info.get('commit'))[:8]}, "
                       f"{'clean' if git_info.get('clean') else 'dirty (uncommitted changes)'}.",
            "confidence_score": 0.95,
            "payload": {"branch": git_info.get("branch"), "commit": git_info.get("commit"),
                        "clean": git_info.get("clean")},
        })

    # FLAG_AGE from DB timestamps when present
    if flag_row is not None and getattr(flag_row, "stale_since", ""):
        out.append({
            "evidence_type": "time-decay",
            "severity": "MEDIUM",
            "value": str(flag_row.stale_since),
            "source": "database",
            "summary": f"Flag marked stale since {flag_row.stale_since}.",
            "confidence_score": 0.8,
            "payload": {"stale_since": flag_row.stale_since},
        })
    return out
