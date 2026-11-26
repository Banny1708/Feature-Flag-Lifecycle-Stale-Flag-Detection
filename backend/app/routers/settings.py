"""Operator settings: detection thresholds + integrations. Persisted, audited, no secrets in code."""
from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models.lifecycle_models import SETTING_DEFAULTS, SystemSetting
from ..services import audit_service
from ..utils.helpers import new_id

router = APIRouter(tags=["settings"])

_INT_KEYS = {"stale_days_threshold": (1, 3650), "warn_days_threshold": (1, 3650)}
_STR_KEYS = {"scanner_engine", "github_token", "slack_webhook"}


def _decode(raw: str, default: object) -> object:
    try:
        return json.loads(raw)
    except Exception:
        return default


def get_effective_settings(db: Session) -> dict[str, object]:
    out: dict[str, object] = dict(SETTING_DEFAULTS)
    for row in db.query(SystemSetting).all():
        if row.key in out:
            out[row.key] = _decode(row.value, out[row.key])
    # guard: warn window must not exceed stale window
    try:
        if int(out["warn_days_threshold"]) > int(out["stale_days_threshold"]):  # type: ignore[arg-type]
            out["warn_days_threshold"] = out["stale_days_threshold"]
    except Exception:
        pass
    return out


@router.get("/api/settings", summary="Effective settings (stored rows merged over defaults)")
def get_settings(db: Session = Depends(get_db)):
    return get_effective_settings(db)


@router.put("/api/settings", summary="Update settings; unknown keys or out-of-range values rejected")
def put_settings(body: dict, db: Session = Depends(get_db)):
    if not isinstance(body, dict) or not body:
        raise HTTPException(status_code=422, detail="settings body must be a non-empty object")
    for key, value in body.items():
        if key in _INT_KEYS:
            lo, hi = _INT_KEYS[key]
            if not isinstance(value, int) or isinstance(value, bool) or not (lo <= value <= hi):
                raise HTTPException(status_code=422,
                                    detail=f"'{key}' must be an integer in [{lo}, {hi}]")
        elif key in _STR_KEYS:
            if not isinstance(value, str) or len(value) > 2048:
                raise HTTPException(status_code=422, detail=f"'{key}' must be a string ≤ 2048 chars")
        else:
            raise HTTPException(status_code=422, detail=f"unknown setting '{key}'")
    for key, value in body.items():
        row = db.query(SystemSetting).filter_by(key=key).first()
        if row:
            row.value = json.dumps(value)
        else:
            db.add(SystemSetting(id=new_id("set"), key=key, value=json.dumps(value)))
    audit_service.log(db, "SETTINGS_UPDATED", entity_type="system_settings",
                      new_value=json.dumps(sorted(body.keys())))
    db.commit()
    return get_effective_settings(db)
