"""Append-only audit log helper."""
from __future__ import annotations

from sqlalchemy.orm import Session

from ..models.lifecycle_models import AuditLog
from ..utils.helpers import new_id, utcnow_iso


def log(db: Session, action: str, entity_type: str = "", entity_id: str = "",
        project_id: str | None = None, feature_flag_id: str | None = None,
        actor: str = "system", old_value: str = "", new_value: str = "",
        metadata: dict | None = None) -> AuditLog:
    row = AuditLog(id=new_id("audit"), project_id=project_id,
                   feature_flag_id=feature_flag_id, user_or_actor=actor,
                   action=action, entity_type=entity_type, entity_id=entity_id,
                   old_value=old_value, new_value=new_value,
                   timestamp=utcnow_iso(), meta=metadata or {})
    db.add(row)
    db.flush()
    return row
