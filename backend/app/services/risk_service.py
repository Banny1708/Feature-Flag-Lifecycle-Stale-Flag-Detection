"""Explainable, rule-based risk assessment. No AI, no external service."""
from __future__ import annotations


def _level(score: int) -> str:
    if score >= 70:
        return "HIGH"
    if score >= 40:
        return "MEDIUM"
    return "LOW"


def assess_risk(flag: dict, evidence: list[dict], code_paths: list[dict],
                git_info: dict | None = None, test_status: str = "unavailable") -> dict:
    factors: list[dict] = []
    git_info = git_info or {}

    # 1. staleness / age
    stale_days = int(flag.get("days_inactive", 0) or 0)
    if stale_days >= 180:
        factors.append({"category": "Staleness", "factor": "LONG_INACTIVE",
                        "impact": "HIGH", "score": 30,
                        "description": f"Flag inactive for {stale_days} days (>=180)."})
    elif stale_days >= 90:
        factors.append({"category": "Staleness", "factor": "MODERATELY_STALE",
                        "impact": "MEDIUM", "score": 18,
                        "description": f"Flag inactive for {stale_days} days (>=90)."})
    elif stale_days > 0:
        factors.append({"category": "Staleness", "factor": "RECENTLY_ACTIVE",
                        "impact": "LOW", "score": 5,
                        "description": f"Flag inactive for {stale_days} days."})

    # 2. references
    ref_count = sum(1 for e in evidence if e.get("evidence_type") in ("ast-unreachable", "code-commit-staleness"))
    n_refs = 0
    for e in evidence:
        try:
            n_refs = max(n_refs, int(e.get("payload", {}).get("reference_count", 0)))
        except Exception:
            pass
    if n_refs == 0:
        factors.append({"category": "Code References", "factor": "ZERO_REFERENCES",
                        "impact": "HIGH", "score": 25,
                        "description": "No source references found; removal is likely safe but verify."})
    elif n_refs == 1:
        factors.append({"category": "Code References", "factor": "SINGLE_REFERENCE",
                        "impact": "LOW", "score": 5,
                        "description": "Single source reference; contained blast radius."})
    else:
        factors.append({"category": "Code References", "factor": "MULTIPLE_REFERENCES",
                        "impact": "MEDIUM", "score": min(20, 6 * n_refs),
                        "description": f"{n_refs} source references; each must be cleaned."})

    # 3. coverage
    uncovered = [p for p in code_paths if p.get("coverage_status") == "uncovered"]
    unknown = [p for p in code_paths if p.get("coverage_status") == "unavailable"]
    if uncovered:
        factors.append({"category": "Branch Coverage", "factor": "UNTESTED_BRANCH",
                        "impact": "HIGH", "score": 20,
                        "description": f"{len(uncovered)} flag-controlled branch(es) have no recorded test coverage."})
    elif unknown and code_paths:
        factors.append({"category": "Branch Coverage", "factor": "COVERAGE_UNKNOWN",
                        "impact": "MEDIUM", "score": 10,
                        "description": "Coverage data unavailable (JaCoCo not present); treat branches as untested."})

    # 4. test results
    if test_status == "failed":
        factors.append({"category": "Test Results", "factor": "FAILING_TESTS",
                        "impact": "HIGH", "score": 20,
                        "description": "Recorded test run failed; removal must not proceed until green."})
    elif test_status == "unavailable":
        factors.append({"category": "Test Results", "factor": "NO_TEST_SIGNAL",
                        "impact": "MEDIUM", "score": 8,
                        "description": "No passing test run recorded for this flag/repo."})

    # 5. dirty repo
    if git_info.get("available") and git_info.get("clean") is False:
        factors.append({"category": "Repository State", "factor": "DIRTY_WORKTREE",
                        "impact": "MEDIUM", "score": 10,
                        "description": "Repository has uncommitted changes; removal requires a clean safety point."})

    # 6. rollout 100%
    if int(flag.get("rollout_percentage", 0) or 0) >= 100:
        factors.append({"category": "Production Traffic", "factor": "FULL_ROLLOUT",
                        "impact": "LOW", "score": -5,
                        "description": "100% rollout: one branch likely permanent; simplifies cleanup."})

    score = max(0, min(100, sum(f["score"] for f in factors)))
    level = _level(score)
    recs = []
    if any(f["factor"] == "UNTESTED_BRANCH" for f in factors):
        recs.append("Add or confirm tests covering the surviving branch before merging removal.")
    if any(f["factor"] == "DIRTY_WORKTREE" for f in factors):
        recs.append("Commit or stash unrelated changes; removal creates its own safety branch.")
    if any(f["factor"] == "ZERO_REFERENCES" for f in factors):
        recs.append("Zero references found — safe to remove after one verification build.")
    if not recs:
        recs.append("Review the listed factors, run Piranha on a safety branch, then run the test suite.")
    hours = 1 + len(code_paths) + (2 if level == "HIGH" else 0)
    return {"risk_level": level, "overall_risk": level.lower(), "score": score,
            "blast_radius_score": score, "factors": factors,
            "recommendations": recs, "estimated_cleanup_hours": hours}
