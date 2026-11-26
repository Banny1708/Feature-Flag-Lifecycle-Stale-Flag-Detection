"""Lifecycle schema: projects, evaluations, analysis runs, detection, risk, removal, evidence, audit.

Extends the UI-mirroring tables in models.py without breaking their API shapes.
All lifecycle transitions are validated in services/lifecycle_service.py.
"""
from __future__ import annotations

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base
from .models import TimestampMixin

# --------------------------------------------------------------------------
# Canonical value sets (validated in service layer, documented in README)
# --------------------------------------------------------------------------
LIFECYCLE_STATES = (
    "ACTIVE", "ROLLOUT", "CONCLUDED", "STALE_CANDIDATE",
    "RISK_REVIEW", "REMOVAL_PENDING", "REMOVED",
)

VALID_TRANSITIONS: dict[str, tuple[str, ...]] = {
    "ACTIVE": ("ROLLOUT", "CONCLUDED"),
    "ROLLOUT": ("CONCLUDED", "ACTIVE"),
    "CONCLUDED": ("STALE_CANDIDATE", "ACTIVE"),
    "STALE_CANDIDATE": ("RISK_REVIEW", "ACTIVE"),
    "RISK_REVIEW": ("REMOVAL_PENDING", "CONCLUDED", "ACTIVE"),
    "REMOVAL_PENDING": ("REMOVED", "RISK_REVIEW"),
    # REMOVED -> RISK_REVIEW is recovery-only, reachable solely via the rollback endpoint.
    "REMOVED": ("RISK_REVIEW",),
}

# UI status (src/types) <-> lifecycle mapping; kept in sync on every transition.
LIFECYCLE_TO_UI_STATUS = {
    "ACTIVE": "active",
    "ROLLOUT": "active",
    "CONCLUDED": "potentially-stale",
    "STALE_CANDIDATE": "stale",
    "RISK_REVIEW": "potentially-stale",
    "REMOVAL_PENDING": "removal-pending",
    "REMOVED": "removed",
}

ANALYSIS_TYPES = ("FLAG_SCAN", "STALE_DETECTION", "CODE_PATH_ANALYSIS",
                  "RISK_ANALYSIS", "REMOVAL_ANALYSIS", "FULL_ANALYSIS")
DETECTION_STATUSES = ("ACTIVE", "CANDIDATE", "STALE", "REVIEW_REQUIRED", "REJECTED")
RISK_LEVELS = ("LOW", "MEDIUM", "HIGH", "CRITICAL")
RECOMMENDATIONS = ("SAFE_TO_REMOVE", "REVIEW_REQUIRED", "DO_NOT_REMOVE")
OPERATION_TYPES = ("DRY_RUN", "REMOVE", "ROLLBACK")
REMOVAL_STATUSES = ("PENDING", "RUNNING", "SUCCESS", "FAILED", "ROLLED_BACK")


class Project(TimestampMixin, Base):
    __tablename__ = "projects"

    name: Mapped[str] = mapped_column(String(256), index=True)
    description: Mapped[str] = mapped_column(Text, default="")
    repository_url: Mapped[str] = mapped_column(String(1024), default="")
    default_branch: Mapped[str] = mapped_column(String(128), default="main")

    repositories: Mapped[list["Repository"]] = relationship(back_populates="project")
    flags: Mapped[list["FeatureFlag"]] = relationship(back_populates="project")


class FlagEvaluation(TimestampMixin, Base):
    __tablename__ = "flag_evaluations"

    feature_flag_id: Mapped[str] = mapped_column(ForeignKey("feature_flags.id"), index=True)
    environment: Mapped[str] = mapped_column(String(64), default="production")
    evaluation_count: Mapped[int] = mapped_column(Integer, default=0)
    enabled_count: Mapped[int] = mapped_column(Integer, default=0)
    disabled_count: Mapped[int] = mapped_column(Integer, default=0)
    last_evaluated_at: Mapped[str] = mapped_column(String(64), default="")
    evaluation_frequency: Mapped[str] = mapped_column(String(64), default="unknown")


class AnalysisRun(TimestampMixin, Base):
    __tablename__ = "analysis_runs"

    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), nullable=True, index=True)
    repository_id: Mapped[str] = mapped_column(ForeignKey("repositories.id"), nullable=True, index=True)
    analysis_type: Mapped[str] = mapped_column(String(32), default="FULL_ANALYSIS", index=True)
    tool_name: Mapped[str] = mapped_column(String(64), default="")
    tool_version: Mapped[str] = mapped_column(String(256), default="")
    started_at: Mapped[str] = mapped_column(String(64), default="")
    completed_at: Mapped[str] = mapped_column(String(64), default="")
    status: Mapped[str] = mapped_column(String(32), default="RUNNING", index=True)
    total_flags: Mapped[int] = mapped_column(Integer, default=0)
    stale_flags: Mapped[int] = mapped_column(Integer, default=0)
    untested_paths: Mapped[int] = mapped_column(Integer, default=0)
    removal_candidates: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[str] = mapped_column(Text, default="")
    configuration: Mapped[dict] = mapped_column(JSON, default=dict)
    commit_hash: Mapped[str] = mapped_column(String(128), default="")
    # tool execution capture (§8)
    command: Mapped[str] = mapped_column(String(1024), default="")
    exit_code: Mapped[int] = mapped_column(Integer, default=0)
    duration_ms: Mapped[int] = mapped_column(Integer, default=0)
    output_excerpt: Mapped[str] = mapped_column(Text, default="")


class DetectionResult(TimestampMixin, Base):
    __tablename__ = "detection_results"

    analysis_run_id: Mapped[str] = mapped_column(ForeignKey("analysis_runs.id"), index=True)
    feature_flag_id: Mapped[str] = mapped_column(ForeignKey("feature_flags.id"), index=True)
    detection_status: Mapped[str] = mapped_column(String(32), default="CANDIDATE", index=True)
    stale_score: Mapped[int] = mapped_column(Integer, default=0)
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    reason: Mapped[str] = mapped_column(Text, default="")
    evidence_summary: Mapped[dict] = mapped_column(JSON, default=dict)
    detected_at: Mapped[str] = mapped_column(String(64), default="")

    analysis_run: Mapped["AnalysisRun"] = relationship()


class UntestedPath(TimestampMixin, Base):
    __tablename__ = "untested_paths"

    analysis_run_id: Mapped[str] = mapped_column(ForeignKey("analysis_runs.id"), index=True)
    feature_flag_id: Mapped[str] = mapped_column(ForeignKey("feature_flags.id"), index=True)
    code_path_id: Mapped[str] = mapped_column(ForeignKey("code_paths.id"), nullable=True, index=True)
    risk_level: Mapped[str] = mapped_column(String(16), default="MEDIUM", index=True)
    reason: Mapped[str] = mapped_column(Text, default="")
    test_coverage: Mapped[str] = mapped_column(String(64), default="unavailable")
    detected_at: Mapped[str] = mapped_column(String(64), default="")


class SystemSetting(TimestampMixin, Base):
    """Operator-configurable thresholds/integrations. GET merges code defaults over stored rows."""

    __tablename__ = "system_settings"

    key: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    value: Mapped[str] = mapped_column(Text, default="")  # JSON-encoded scalar


SETTING_DEFAULTS: dict[str, object] = {
    "stale_days_threshold": 180,
    "warn_days_threshold": 90,
    "scanner_engine": "FlagShark",
    "github_token": "",
    "slack_webhook": "",
}


class AuditLog(Base):
    """Append-only; no updated_at (immutable history). Has own id/created_at via Base? No:
    Base here is DeclarativeBase without id, so declare explicitly."""
    __tablename__ = "audit_logs"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    project_id: Mapped[str] = mapped_column(String(64), nullable=True, index=True)
    feature_flag_id: Mapped[str] = mapped_column(String(64), nullable=True, index=True)
    user_or_actor: Mapped[str] = mapped_column(String(256), default="system")
    action: Mapped[str] = mapped_column(String(64), index=True)
    entity_type: Mapped[str] = mapped_column(String(64), default="")
    entity_id: Mapped[str] = mapped_column(String(64), default="")
    old_value: Mapped[str] = mapped_column(Text, default="")
    new_value: Mapped[str] = mapped_column(Text, default="")
    timestamp: Mapped[str] = mapped_column(String(64), default="", index=True)
    meta: Mapped[dict] = mapped_column("metadata", JSON, default=dict)
