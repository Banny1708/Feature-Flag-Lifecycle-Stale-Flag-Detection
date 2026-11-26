"""Explainable multi-signal stale-flag detection.

Scoring (0-100, deterministic; documented here and in README):
  +30  days_inactive >= 180
  +18  days_inactive >= 90
  + 5  days_inactive > 0
  +12  rollout == 100% (settled)            [signal: ROLLOUT_STATE]
  +10  evaluations_last_7d == 0             [signal: EVALUATION_FREQUENCY]
  +25  zero code references in latest data  [signal: CODE_REFERENCE]
  +10  expiry date passed                    [signal: FLAG_AGE vs expected_expiry_date]
  + 8  no flag-related git commits >= 180d  [signal: CODE_REFERENCE/git]
  -15  recently modified (< 30d)            [reduces score: still evolving]

Classification:
  score >= 60 and >= 2 independent signals -> STALE
  score >= 35 and >= 2 signals             -> CANDIDATE
  score >= 35 but < 2 signals              -> REVIEW_REQUIRED (never claim stale without evidence)
  otherwise                                -> ACTIVE
  insufficient data (no refs info AND no eval info AND no git) -> REJECTED

recommended_action: MONITOR / REVIEW / REMOVE_CANDIDATE
"""
from __future__ import annotations

from datetime import datetime


def _days_ago(iso: str) -> int | None:
    try:
        dt = datetime.fromisoformat((iso or "").replace("Z", "+00:00"))
        now = datetime.now(dt.tzinfo)
        return (now - dt).days
    except Exception:
        return None


def evaluate(flag: dict, eval_info: dict | None = None, ref_count: int | None = None,
             git_last_touch_days: int | None = None,
             thresholds: dict | None = None) -> dict:
    signals: list[dict] = []
    score = 0
    stale_days = int((thresholds or {}).get("stale_days_threshold", 180) or 180)
    warn_days = int((thresholds or {}).get("warn_days_threshold", 90) or 90)

    def add(points: int, signal: str, detail: str) -> None:
        nonlocal score
        score += points
        signals.append({"signal": signal, "points": points, "detail": detail})

    inactive = int(flag.get("days_inactive", 0) or 0)
    if inactive >= stale_days:
        add(30, "FLAG_AGE", f"inactive {inactive}d (>={stale_days})")
    elif inactive >= warn_days:
        add(18, "FLAG_AGE", f"inactive {inactive}d (>={warn_days})")
    elif inactive > 0:
        add(5, "FLAG_AGE", f"inactive {inactive}d")

    if int(flag.get("rollout_percentage", 0) or 0) >= 100:
        add(12, "ROLLOUT_STATE", "rollout at 100% (settled)")

    # Only persisted FlagEvaluation rows count; a legacy evaluations_last_7d
    # default of 0 on unevaluated flags is not evidence of anything.
    last7 = (eval_info or {}).get("evaluations_last_7d")
    if last7 is not None and int(last7) == 0:
        add(10, "EVALUATION_FREQUENCY", "0 evaluations in last 7d")

    if ref_count is not None:
        if ref_count == 0:
            add(25, "CODE_REFERENCE", "zero code references found")
        # >0 refs is neutral (no points): referenced code may still be dead, needs review

    exp = flag.get("expected_expiry_date") or ""
    if exp:
        d = _days_ago(exp)
        if d is not None and d > 0:
            add(10, "FLAG_AGE", f"expiry {exp} passed {d}d ago")

    if git_last_touch_days is not None and git_last_touch_days >= stale_days:
        add(8, "CODE_REFERENCE", f"no flag-related commits for {git_last_touch_days}d")

    mod_days = _days_ago(flag.get("last_modified", "") or "")
    if mod_days is not None and mod_days < 30:
        score -= 15
        signals.append({"signal": "FLAG_AGE", "points": -15,
                        "detail": f"modified {mod_days}d ago (still evolving)"})

    score = max(0, min(100, score))
    n_signals = len({s["signal"] for s in signals if s["points"] > 0})
    has_data = (ref_count is not None) or (last7 is not None) or (git_last_touch_days is not None)

    if not has_data:
        status, action, conf = "REJECTED", "MONITOR", 0.2
    elif score >= 60 and n_signals >= 2:
        status, action, conf = "STALE", "REMOVE_CANDIDATE", min(0.95, 0.6 + score / 200)
    elif score >= 35 and n_signals >= 2:
        status, action, conf = "CANDIDATE", "REVIEW", min(0.85, 0.5 + score / 200)
    elif score >= 35:
        status, action, conf = "REVIEW_REQUIRED", "REVIEW", 0.5
    else:
        status, action, conf = "ACTIVE", "MONITOR", 0.7

    reasons = [f"{s['signal']}: {s['detail']} ({s['points']:+d})" for s in signals]
    return {"stale_score": score, "confidence": round(conf, 2), "detection_status": status,
            "reasons": reasons, "signals": signals, "signal_count": n_signals,
            "recommended_action": action}
