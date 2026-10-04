"""SQLAlchemy models mirroring src/types/index.ts (snake_case in DB)."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base


class TimestampMixin:
    """Adds id + created_at/updated_at to every table. Mix in FIRST: class X(TimestampMixin, Base)."""
    __abstract__ = True
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class Repository(TimestampMixin, Base):
    __tablename__ = "repositories"

    name: Mapped[str] = mapped_column(String(256), index=True)
    full_name: Mapped[str] = mapped_column(String(512), default="")
    owner: Mapped[str] = mapped_column(String(256), default="")
    url: Mapped[str] = mapped_column(String(1024), default="")
    local_path: Mapped[str] = mapped_column(String(1024), default="")  # backend-only: checked-out path
    default_branch: Mapped[str] = mapped_column(String(128), default="main")
    language: Mapped[str] = mapped_column(String(128), default="")
    scan_status: Mapped[str] = mapped_column(String(32), default="idle", index=True)
    last_scanned_at: Mapped[str] = mapped_column(String(64), default="")
    total_flags: Mapped[int] = mapped_column(Integer, default=0)
    active_flags: Mapped[int] = mapped_column(Integer, default=0)
    stale_flags: Mapped[int] = mapped_column(Integer, default=0)
    potentially_stale_flags: Mapped[int] = mapped_column(Integer, default=0)
    lines_of_code: Mapped[int] = mapped_column(Integer, default=0)

    scans: Mapped[list["Scan"]] = relationship(back_populates="repository", cascade="all, delete-orphan")
    flags: Mapped[list["FeatureFlag"]] = relationship(back_populates="repository", cascade="all, delete-orphan")


class Scan(TimestampMixin, Base):
    __tablename__ = "scans"

    repository_id: Mapped[str] = mapped_column(ForeignKey("repositories.id"), index=True)
    repository_name: Mapped[str] = mapped_column(String(256), default="")
    timestamp: Mapped[str] = mapped_column(String(64), default="")
    status: Mapped[str] = mapped_column(String(32), default="success")  # success|partial|failed
    total_flags_detected: Mapped[int] = mapped_column(Integer, default=0)
    stale_flags_detected: Mapped[int] = mapped_column(Integer, default=0)
    scanner_engine: Mapped[str] = mapped_column(String(64), default="FlagShark-engine")
    scan_duration_ms: Mapped[int] = mapped_column(Integer, default=0)
    commit_hash: Mapped[str] = mapped_column(String(128), default="")
    branch: Mapped[str] = mapped_column(String(128), default="")
    raw_output: Mapped[str] = mapped_column(Text, default="")  # captured FlagShark stdout (truncated)
    error_message: Mapped[str] = mapped_column(Text, default="")

    repository: Mapped["Repository"] = relationship(back_populates="scans")
    findings: Mapped[list["ScanFinding"]] = relationship(back_populates="scan", cascade="all, delete-orphan")


class ScanFinding(TimestampMixin, Base):
    __tablename__ = "scan_findings"

    scan_id: Mapped[str] = mapped_column(ForeignKey("scans.id"), index=True)
    flag_key: Mapped[str] = mapped_column(String(256), index=True)
    file_path: Mapped[str] = mapped_column(String(1024), default="")
    line_number: Mapped[int] = mapped_column(Integer, default=0)
    ast_node_type: Mapped[str] = mapped_column(String(128), default="")
    is_stale: Mapped[int] = mapped_column(Integer, default=0)
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    reason: Mapped[str] = mapped_column(Text, default="")

    scan: Mapped["Scan"] = relationship(back_populates="findings")


class FeatureFlag(TimestampMixin, Base):
    __tablename__ = "feature_flags"

    name: Mapped[str] = mapped_column(String(256), default="")
    key: Mapped[str] = mapped_column(String(256), index=True, unique=False)
    description: Mapped[str] = mapped_column(Text, default="")
    repository_id: Mapped[str] = mapped_column(ForeignKey("repositories.id"), index=True)
    repository_name: Mapped[str] = mapped_column(String(256), default="")
    status: Mapped[str] = mapped_column(String(32), default="active", index=True)
    risk: Mapped[str] = mapped_column(String(32), default="medium")
    flag_type: Mapped[str] = mapped_column(String(32), default="release")
    owner: Mapped[str] = mapped_column(String(256), default="")
    owner_team: Mapped[str] = mapped_column(String(256), default="")
    created_at_flag: Mapped[str] = mapped_column(String(64), default="")  # domain createdAt (ISO)
    last_modified: Mapped[str] = mapped_column(String(64), default="")
    stale_since: Mapped[str] = mapped_column(String(64), default="")
    evaluations_count: Mapped[int] = mapped_column(Integer, default=0)
    evaluations_last_7d: Mapped[int] = mapped_column(Integer, default=0)
    days_inactive: Mapped[int] = mapped_column(Integer, default=0)
    rollout_percentage: Mapped[int] = mapped_column(Integer, default=0)
    environment: Mapped[str] = mapped_column(String(32), default="production")
    tags: Mapped[list] = mapped_column(JSON, default=list)
    default_value: Mapped[str] = mapped_column(String(64), default="false")  # stored as string; parsed on read

    repository: Mapped["Repository"] = relationship(back_populates="flags")


class EvidenceRecord(TimestampMixin, Base):
    __tablename__ = "evidence_records"

    flag_id: Mapped[str] = mapped_column(String(64), index=True)
    flag_name: Mapped[str] = mapped_column(String(256), default="")
    repository_name: Mapped[str] = mapped_column(String(256), default="")
    evidence_type: Mapped[str] = mapped_column(String(64), default="")
    confidence_score: Mapped[float] = mapped_column(Float, default=0.0)
    detected_at: Mapped[str] = mapped_column(String(64), default="")
    source: Mapped[str] = mapped_column(String(256), default="")
    summary: Mapped[str] = mapped_column(Text, default="")
    # Generic evidence fields required by spec (nullable so frontend payloads still fit)
    severity: Mapped[str] = mapped_column(String(32), default="")
    value: Mapped[str] = mapped_column(Text, default="")
    payload: Mapped[dict] = mapped_column(JSON, default=dict)


class CodeReference(TimestampMixin, Base):
    __tablename__ = "code_references"

    flag_id: Mapped[str] = mapped_column(String(64), index=True)
    flag_name: Mapped[str] = mapped_column(String(256), default="")
    repository_id: Mapped[str] = mapped_column(String(64), default="")
    repository_name: Mapped[str] = mapped_column(String(256), default="")
    file_path: Mapped[str] = mapped_column(String(1024), default="")
    line_number: Mapped[int] = mapped_column(Integer, default=0)
    column_number: Mapped[int] = mapped_column(Integer, default=0)
    code_snippet: Mapped[str] = mapped_column(Text, default="")
    reference_type: Mapped[str] = mapped_column(String(64), default="check")
    is_enclosing_control_flow: Mapped[int] = mapped_column(Integer, default=0)
    ast_node_type: Mapped[str] = mapped_column(String(128), default="")


class CodePath(TimestampMixin, Base):
    __tablename__ = "code_paths"

    flag_id: Mapped[str] = mapped_column(String(64), index=True)
    file_path: Mapped[str] = mapped_column(String(1024), default="")
    branch_condition: Mapped[str] = mapped_column(String(512), default="")
    reachable_state: Mapped[int] = mapped_column(Integer, default=1)
    dead_code_lines: Mapped[list] = mapped_column(JSON, default=list)
    dead_code_snippet: Mapped[str] = mapped_column(Text, default="")
    complexity_reduction_score: Mapped[int] = mapped_column(Integer, default=0)
    # Spec fields (nullable-friendly defaults)
    true_branch: Mapped[str] = mapped_column(Text, default="")
    false_branch: Mapped[str] = mapped_column(Text, default="")
    functions_involved: Mapped[list] = mapped_column(JSON, default=list)
    coverage_status: Mapped[str] = mapped_column(String(32), default="unavailable")


class RiskAssessment(TimestampMixin, Base):
    __tablename__ = "risk_assessments"

    flag_id: Mapped[str] = mapped_column(String(64), index=True)
    flag_name: Mapped[str] = mapped_column(String(256), default="")
    overall_risk: Mapped[str] = mapped_column(String(32), default="medium")
    blast_radius_score: Mapped[int] = mapped_column(Integer, default=0)
    recommendations: Mapped[list] = mapped_column(JSON, default=list)
    assessed_at: Mapped[str] = mapped_column(String(64), default="")
    estimated_cleanup_hours: Mapped[int] = mapped_column(Integer, default=0)
    score: Mapped[int] = mapped_column(Integer, default=0)  # numeric 0-100 mirror of blast radius

    factors: Mapped[list["RiskFactor"]] = relationship(back_populates="assessment", cascade="all, delete-orphan")


class RiskFactor(TimestampMixin, Base):
    __tablename__ = "risk_factors"

    assessment_id: Mapped[str] = mapped_column(ForeignKey("risk_assessments.id"), index=True)
    category: Mapped[str] = mapped_column(String(128), default="")
    description: Mapped[str] = mapped_column(Text, default="")
    score: Mapped[int] = mapped_column(Integer, default=0)
    level: Mapped[str] = mapped_column(String(32), default="medium")

    assessment: Mapped["RiskAssessment"] = relationship(back_populates="factors")


class RemovalOperation(TimestampMixin, Base):
    __tablename__ = "removal_operations"

    flag_id: Mapped[str] = mapped_column(String(64), index=True)
    flag_name: Mapped[str] = mapped_column(String(256), default="")
    repository_id: Mapped[str] = mapped_column(String(64), default="")
    repository_name: Mapped[str] = mapped_column(String(256), default="")
    target_branch: Mapped[str] = mapped_column(String(128), default="main")
    pr_url: Mapped[str] = mapped_column(String(1024), default="")
    pr_number: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(32), default="draft", index=True)  # + SUCCESS/FAILED/UNVERIFIED terminal note in verification
    tool_target: Mapped[str] = mapped_column(String(32), default="Piranha")
    files_affected: Mapped[int] = mapped_column(Integer, default=0)
    lines_removed: Mapped[int] = mapped_column(Integer, default=0)
    lines_added: Mapped[int] = mapped_column(Integer, default=0)
    completed_at: Mapped[str] = mapped_column(String(64), default="")
    executed_by: Mapped[str] = mapped_column(String(256), default="")
    diff_summary: Mapped[str] = mapped_column(Text, default="")
    # Safety / provenance (backend workflow)
    safety_branch: Mapped[str] = mapped_column(String(256), default="")
    base_commit: Mapped[str] = mapped_column(String(128), default="")
    stdout_log: Mapped[str] = mapped_column(Text, default="")
    stderr_log: Mapped[str] = mapped_column(Text, default="")
    verification_status: Mapped[str] = mapped_column(String(32), default="UNVERIFIED")


class TestRun(TimestampMixin, Base):
    __tablename__ = "test_runs"

    operation_id: Mapped[str] = mapped_column(String(64), index=True, default="")
    repository_id: Mapped[str] = mapped_column(String(64), default="")
    command: Mapped[str] = mapped_column(String(1024), default="")
    status: Mapped[str] = mapped_column(String(32), default="running")  # passed|failed|running|skipped
    success: Mapped[int] = mapped_column(Integer, default=0)
    test_count: Mapped[int] = mapped_column(Integer, default=0)
    failed_tests: Mapped[list] = mapped_column(JSON, default=list)
    output: Mapped[str] = mapped_column(Text, default="")
    branch_coverage: Mapped[str] = mapped_column(String(64), default="unavailable")
    line_coverage: Mapped[str] = mapped_column(String(64), default="unavailable")


class VerificationResult(TimestampMixin, Base):
    __tablename__ = "verification_results"

    operation_id: Mapped[str] = mapped_column(String(64), index=True)
    flag_id: Mapped[str] = mapped_column(String(64), default="")
    flag_name: Mapped[str] = mapped_column(String(256), default="")
    repository_name: Mapped[str] = mapped_column(String(256), default="")
    test_suite_status: Mapped[str] = mapped_column(String(32), default="running")
    build_status: Mapped[str] = mapped_column(String(32), default="running")
    ast_validation_status: Mapped[str] = mapped_column(String(32), default="running")
    dead_code_eliminated: Mapped[int] = mapped_column(Integer, default=0)
    syntax_valid: Mapped[int] = mapped_column(Integer, default=0)
    regression_detected: Mapped[int] = mapped_column(Integer, default=0)
    unresolved_references: Mapped[int] = mapped_column(Integer, default=0)
    verified_at: Mapped[str] = mapped_column(String(64), default="")
    summary: Mapped[str] = mapped_column(Text, default="")
    test_output_summary: Mapped[str] = mapped_column(Text, default="")


class Report(TimestampMixin, Base):
    __tablename__ = "reports"

    title: Mapped[str] = mapped_column(String(512), default="")
    type: Mapped[str] = mapped_column(String(64), default="stale-summary")
    generated_at: Mapped[str] = mapped_column(String(64), default="")
    repository_id: Mapped[str] = mapped_column(String(64), default="")
    repository_name: Mapped[str] = mapped_column(String(256), default="")
    total_scanned_flags: Mapped[int] = mapped_column(Integer, default=0)
    stale_flags_identified: Mapped[int] = mapped_column(Integer, default=0)
    removal_operations_completed: Mapped[int] = mapped_column(Integer, default=0)
    tech_debt_reduction_hours: Mapped[int] = mapped_column(Integer, default=0)
    code_lines_eliminated: Mapped[int] = mapped_column(Integer, default=0)
    download_format: Mapped[str] = mapped_column(String(16), default="json")
    status: Mapped[str] = mapped_column(String(32), default="ready")
