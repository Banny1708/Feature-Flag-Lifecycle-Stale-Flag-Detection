"""Pydantic schemas with camelCase aliases to match src/types/index.ts."""
from __future__ import annotations

from typing import Any, Generic, Literal, TypeVar

from pydantic import BaseModel, ConfigDict, Field


def _camel(s: str) -> str:
    parts = s.split("_")
    return parts[0] + "".join(p.capitalize() for p in parts[1:])


class CamelModel(BaseModel):
    model_config = ConfigDict(alias_generator=_camel, populate_by_name=True, from_attributes=True)


# ---------- generic ----------
T = TypeVar("T")


class ErrorResponse(CamelModel):
    detail: str
    code: str = "error"


class ToolStatus(CamelModel):
    name: str
    available: bool
    version: str = ""
    path: str = ""
    hint: str = ""


# ---------- repositories ----------
class RepositoryCreate(CamelModel):
    name: str = ""
    full_name: str = ""
    owner: str = ""
    url: str = ""
    local_path: str = Field(default="", description="Absolute path to a local git checkout to analyze")
    default_branch: str = "main"
    language: str = ""


class RepositoryOut(CamelModel):
    id: str
    name: str
    full_name: str = ""
    owner: str = ""
    url: str = ""
    default_branch: str = "main"
    language: str = ""
    scan_status: str = "idle"
    last_scanned_at: str = ""
    total_flags: int = 0
    active_flags: int = 0
    stale_flags: int = 0
    potentially_stale_flags: int = 0
    lines_of_code: int = 0


# ---------- scans ----------
class ScanCreate(CamelModel):
    repository_id: str
    branch: str = ""


class ScanFindingOut(CamelModel):
    flag_key: str
    file_path: str = ""
    line_number: int = 0
    ast_node_type: str = ""
    is_stale: bool = False
    confidence: float = 0.0
    reason: str = ""


class ScanOut(CamelModel):
    id: str
    repository_id: str
    repository_name: str = ""
    timestamp: str = ""
    status: str = "success"
    total_flags_detected: int = 0
    stale_flags_detected: int = 0
    scanner_engine: str = "FlagShark-engine"
    scan_duration_ms: int = 0
    commit_hash: str = ""
    branch: str = ""
    findings: list[ScanFindingOut] = []


# ---------- flags ----------
class UsageMetricsOut(CamelModel):
    evaluations_count: int = 0
    evaluations_last7d: int = 0
    days_inactive: int = 0
    rollout_percentage: int = 0
    environment: str = "production"


class FeatureFlagOut(CamelModel):
    id: str
    name: str
    key: str
    description: str = ""
    repository_id: str
    repository_name: str = ""
    status: str = "active"
    risk: str = "medium"
    flag_type: str = "release"
    owner: str = ""
    owner_team: str | None = None
    created_at: str = ""
    last_modified: str = ""
    stale_since: str | None = None
    metrics: UsageMetricsOut
    tags: list[str] = []
    default_value: bool | str | int = False


# ---------- evidence / code paths / risk ----------
class EvidenceOut(CamelModel):
    id: str
    flag_id: str
    flag_name: str = ""
    repository_name: str = ""
    evidence_type: str = ""
    confidence_score: float = 0.0
    detected_at: str = ""
    source: str = ""
    summary: str = ""
    severity: str = ""
    value: str = ""
    payload: dict[str, Any] = {}


class CodeReferenceOut(CamelModel):
    id: str
    flag_id: str
    flag_name: str = ""
    repository_id: str = ""
    repository_name: str = ""
    file_path: str = ""
    line_number: int = 0
    column_number: int = 0
    code_snippet: str = ""
    reference_type: str = "check"
    is_enclosing_control_flow: bool = False
    ast_node_type: str = ""


class CodePathOut(CamelModel):
    id: str
    flag_id: str
    file_path: str = ""
    branch_condition: str = ""
    reachable_state: bool = True
    dead_code_lines: list[int] = []
    dead_code_snippet: str = ""
    complexity_reduction_score: int = 0
    true_branch: str = ""
    false_branch: str = ""
    functions_involved: list[str] = []
    coverage_status: str = "unavailable"


class RiskFactorOut(CamelModel):
    category: str = ""
    description: str = ""
    score: int = 0
    level: str = "medium"


class RiskAssessmentOut(CamelModel):
    id: str
    flag_id: str
    flag_name: str = ""
    overall_risk: str = "medium"
    risk_level: str = "MEDIUM"
    score: int = 0
    blast_radius_score: int = 0
    factors: list[RiskFactorOut] = []
    recommendations: list[str] = []
    assessed_at: str = ""
    estimated_cleanup_hours: int = 0


# ---------- removals / verification ----------
class RemovalCreate(CamelModel):
    flag_id: str
    target_branch: str = "main"
    tool_target: str = "Piranha"
    permanent_value: str = "false"
    executed_by: str = "local-user"


class RemovalOut(CamelModel):
    id: str
    flag_id: str
    flag_name: str = ""
    repository_id: str = ""
    repository_name: str = ""
    target_branch: str = "main"
    pr_url: str | None = None
    pr_number: int | None = None
    status: str = "draft"
    tool_target: str = "Piranha"
    files_affected: int = 0
    lines_removed: int = 0
    lines_added: int = 0
    created_at: str = ""
    completed_at: str | None = None
    executed_by: str = ""
    diff_summary: str | None = None
    safety_branch: str = ""
    base_commit: str = ""
    verification_status: str = "UNVERIFIED"


class DiffCheckOut(CamelModel):
    dead_code_eliminated: bool = False
    syntax_valid: bool = False
    regression_detected: bool = False
    unresolved_references: int = 0


class VerificationOut(CamelModel):
    id: str
    operation_id: str
    flag_id: str
    flag_name: str = ""
    repository_name: str = ""
    test_suite_status: str = "running"
    build_status: str = "running"
    ast_validation_status: str = "running"
    diff_analysis: DiffCheckOut
    verified_at: str = ""
    summary: str = ""
    test_output_summary: str | None = None


class TestRunOut(CamelModel):
    id: str
    operation_id: str = ""
    repository_id: str = ""
    command: str = ""
    status: str = "running"
    success: bool = False
    test_count: int = 0
    failed_tests: list[str] = []
    output: str = ""
    branch_coverage: str = "unavailable"
    line_coverage: str = "unavailable"


# ---------- reports ----------
class ReportSummaryOut(CamelModel):
    total_scanned_flags: int = 0
    stale_flags_identified: int = 0
    removal_operations_completed: int = 0
    tech_debt_reduction_hours: int = 0
    code_lines_eliminated: int = 0


class ReportOut(CamelModel):
    id: str
    title: str
    type: str = "stale-summary"
    generated_at: str = ""
    repository_id: str | None = None
    repository_name: str | None = None
    summary: ReportSummaryOut
    download_format: str = "json"
    status: str = "ready"


class ReportCreate(CamelModel):
    title: str
    type: str = "stale-summary"
    repository_id: str | None = None
    download_format: str = "json"
