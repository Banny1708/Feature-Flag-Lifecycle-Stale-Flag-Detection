"""Pydantic schemas for lifecycle entities (camelCase to match frontend conventions)."""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


def _camel(s: str) -> str:
    parts = s.split("_")
    return parts[0] + "".join(p.capitalize() for p in parts[1:])


class CamelModel(BaseModel):
    model_config = ConfigDict(alias_generator=_camel, populate_by_name=True, from_attributes=True)


# ---------- projects ----------
class ProjectCreate(CamelModel):
    name: str
    description: str = ""
    repository_url: str = ""
    default_branch: str = "main"


class ProjectOut(CamelModel):
    id: str
    name: str
    description: str = ""
    repository_url: str = ""
    default_branch: str = "main"
    created_at: str = ""
    updated_at: str = ""


# ---------- flags (lifecycle extensions) ----------
class FlagCreate(CamelModel):
    project_id: str | None = None
    repository_id: str = ""
    name: str
    key: str
    description: str = ""
    flag_type: str = "release"
    owner: str = ""
    environment: str = "production"
    current_value: str = "false"
    rollout_start_date: str = ""
    rollout_end_date: str = ""
    expected_expiry_date: str = ""


class FlagPatch(CamelModel):
    lifecycle_state: str | None = None
    status: str | None = None  # legacy UI status; mapped to lifecycle when possible
    owner: str | None = None
    description: str | None = None
    expected_expiry_date: str | None = None
    current_value: str | None = None


class EvaluationIn(CamelModel):
    environment: str = "production"
    evaluation_count: int = 0
    enabled_count: int = 0
    disabled_count: int = 0
    last_evaluated_at: str = ""
    evaluation_frequency: str = "unknown"


class EvaluationOut(EvaluationIn):
    id: str
    feature_flag_id: str


# ---------- analysis ----------
class AnalysisRunCreate(CamelModel):
    project_id: str | None = None
    repository_id: str | None = None
    analysis_type: str = "FULL_ANALYSIS"
    configuration: dict[str, Any] = {}


class AnalysisRunOut(CamelModel):
    id: str
    project_id: str | None = None
    repository_id: str | None = None
    analysis_type: str = "FULL_ANALYSIS"
    tool_name: str = ""
    tool_version: str = ""
    started_at: str = ""
    completed_at: str = ""
    status: str = "RUNNING"
    total_flags: int = 0
    stale_flags: int = 0
    untested_paths: int = 0
    removal_candidates: int = 0
    error_message: str = ""
    commit_hash: str = ""
    exit_code: int = 0
    duration_ms: int = 0


class DetectionResultOut(CamelModel):
    id: str
    analysis_run_id: str
    feature_flag_id: str
    detection_status: str = "CANDIDATE"
    stale_score: int = 0
    confidence: float = 0.0
    reason: str = ""
    evidence_summary: dict[str, Any] = {}
    detected_at: str = ""


class UntestedPathOut(CamelModel):
    id: str
    analysis_run_id: str
    feature_flag_id: str
    code_path_id: str | None = None
    risk_level: str = "MEDIUM"
    reason: str = ""
    test_coverage: str = "unavailable"
    detected_at: str = ""


class RiskAssessmentCreate(CamelModel):
    flag_id: str = Field(description="Feature flag id (or key)")


class EvidenceOut2(CamelModel):
    """Full evidence row incl. lifecycle columns (superset of legacy EvidenceOut)."""
    id: str
    project_id: str | None = None
    analysis_run_id: str | None = None
    flag_id: str = ""
    flag_name: str = ""
    repository_name: str = ""
    evidence_type: str = ""
    source: str = ""
    summary: str = ""
    description: str = ""
    file_path: str | None = None
    line_reference: str | None = None
    value: str = ""
    severity: str = ""
    confidence_score: float = 0.0
    detected_at: str = ""
    payload: dict[str, Any] = {}


class AuditLogOut(CamelModel):
    id: str
    project_id: str | None = None
    feature_flag_id: str | None = None
    user_or_actor: str = "system"
    action: str = ""
    entity_type: str = ""
    entity_id: str = ""
    old_value: str = ""
    new_value: str = ""
    timestamp: str = ""
    metadata: dict[str, Any] = {}


# ---------- removals ----------
class DryRunIn(CamelModel):
    flag_id: str
    target_branch: str = "main"
    permanent_value: str = "false"


class RemovalCreate2(CamelModel):
    flag_id: str
    analysis_run_id: str | None = None
    target_branch: str = "main"
    tool_target: str = "Piranha"
    permanent_value: str = "false"
    executed_by: str = "local-user"
