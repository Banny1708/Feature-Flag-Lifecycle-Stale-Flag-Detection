"""Lifecycle state machine + audit trail.

UI `status` (active/potentially-stale/stale/removal-pending/removed) is kept in
sync with `lifecycle_state` so the existing frontend keeps working unchanged.
Invalid transitions raise LifecycleError -> HTTP 422.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from ..models.lifecycle_models import LIFECYCLE_TO_UI_STATUS, VALID_TRANSITIONS, AuditLog
from ..models.models import FeatureFlag
from ..utils.helpers import new_id, utcnow_iso


class LifecycleError(ValueError):
    pass


def current_state(flag: FeatureFlag) -> str:
    state = getattr(flag, "lifecycle_state", None) or ""
    if state:
        return state
    # backfill legacy rows from UI status
    legacy = {"active": "ACTIVE", "potentially-stale": "CONCLUDED", "stale": "STALE_CANDIDATE",
              "removal-pending": "REMOVAL_PENDING", "removed": "REMOVED"}
    return legacy.get((flag.status or "active"), "ACTIVE")


def allowed_transitions(state: str) -> tuple[str, ...]:
    return VALID_TRANSITIONS.get(state, ())


def transition(db: Session, flag: FeatureFlag, to_state: str, actor: str = "system",
               action: str = "", metadata: dict | None = None) -> FeatureFlag:
    to_state = (to_state or "").upper()
    if to_state not in VALID_TRANSITIONS:
        raise LifecycleError(f"unknown lifecycle state '{to_state}'")
    frm = current_state(flag)
    if to_state != frm and to_state not in VALID_TRANSITIONS.get(frm, ()):
        raise LifecycleError(f"invalid lifecycle transition {frm} -> {to_state}")
    old_ui = flag.status
    flag.lifecycle_state = to_state  # type: ignore[attr-defined]
    flag.status = LIFECYCLE_TO_UI_STATUS[to_state]
    flag.last_modified = utcnow_iso()
    if to_state == "STALE_CANDIDATE" and not getattr(flag, "stale_since", None):
        flag.stale_since = utcnow_iso()
    db.add(AuditLog(id=new_id("audit"), project_id=getattr(flag, "project_id", None),
                    feature_flag_id=flag.id, user_or_actor=actor,
                    action=action or "FLAG_UPDATED", entity_type="feature_flag",
                    entity_id=flag.id, old_value=f"{frm}/{old_ui}",
                    new_value=f"{to_state}/{flag.status}", timestamp=utcnow_iso(),
                    meta=metadata or {}))
    db.flush()
    return flag
