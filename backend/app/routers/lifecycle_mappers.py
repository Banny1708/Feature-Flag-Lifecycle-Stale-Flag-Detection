"""Mappers for lifecycle entities."""
from __future__ import annotations

from ..models.lifecycle_models import (
    AnalysisRun,
    AuditLog,
    DetectionResult,
    FlagEvaluation,
    Project,
    UntestedPath,
)
from ..models.models import EvidenceRecord
from ..schemas.lifecycle_schemas import (
    AnalysisRunOut,
    AuditLogOut,
    DetectionResultOut,
    EvaluationOut,
    EvidenceOut2,
    ProjectOut,
    UntestedPathOut,
)


def _iso(v) -> str:
    return v.isoformat() if hasattr(v, "isoformat") else (v or "")


def project_out(p: Project) -> ProjectOut:
    return ProjectOut(id=p.id, name=p.name, description=p.description or "",
                      repository_url=p.repository_url or "", default_branch=p.default_branch or "main",
                      created_at=_iso(p.created_at), updated_at=_iso(p.updated_at))


def eval_out(e: FlagEvaluation) -> EvaluationOut:
    return EvaluationOut(id=e.id, feature_flag_id=e.feature_flag_id, environment=e.environment,
                         evaluation_count=e.evaluation_count, enabled_count=e.enabled_count,
                         disabled_count=e.disabled_count, last_evaluated_at=e.last_evaluated_at,
                         evaluation_frequency=e.evaluation_frequency)


def run_out(r: AnalysisRun) -> AnalysisRunOut:
    return AnalysisRunOut(id=r.id, project_id=r.project_id or None,
                          repository_id=r.repository_id or None, analysis_type=r.analysis_type,
                          tool_name=r.tool_name or "", tool_version=(r.tool_version or "")[:300],
                          started_at=r.started_at or "", completed_at=r.completed_at or "",
                          status=r.status, total_flags=r.total_flags, stale_flags=r.stale_flags,
                          untested_paths=r.untested_paths, removal_candidates=r.removal_candidates,
                          error_message=(r.error_message or "")[:2000], commit_hash=r.commit_hash or "",
                          exit_code=r.exit_code, duration_ms=r.duration_ms)


def detection_out(d: DetectionResult) -> DetectionResultOut:
    return DetectionResultOut(id=d.id, analysis_run_id=d.analysis_run_id,
                              feature_flag_id=d.feature_flag_id,
                              detection_status=d.detection_status, stale_score=d.stale_score,
                              confidence=d.confidence, reason=d.reason or "",
                              evidence_summary=d.evidence_summary or {},
                              detected_at=d.detected_at or "")


def untested_out(u: UntestedPath) -> UntestedPathOut:
    return UntestedPathOut(id=u.id, analysis_run_id=u.analysis_run_id,
                           feature_flag_id=u.feature_flag_id,
                           code_path_id=u.code_path_id or None, risk_level=u.risk_level,
                           reason=u.reason or "", test_coverage=u.test_coverage or "unavailable",
                           detected_at=u.detected_at or "")


def evidence2_out(e: EvidenceRecord) -> EvidenceOut2:
    return EvidenceOut2(id=e.id, project_id=getattr(e, "project_id", None),
                        analysis_run_id=getattr(e, "analysis_run_id", None),
                        flag_id=e.flag_id, flag_name=e.flag_name,
                        repository_name=e.repository_name, evidence_type=e.evidence_type,
                        source=e.source, summary=e.summary, description=e.summary,
                        file_path=getattr(e, "file_path", None),
                        line_reference=getattr(e, "line_reference", None),
                        value=e.value or "", severity=e.severity or "",
                        confidence_score=e.confidence_score, detected_at=e.detected_at,
                        payload=e.payload or {})


def audit_out(a: AuditLog) -> AuditLogOut:
    return AuditLogOut(id=a.id, project_id=a.project_id, feature_flag_id=a.feature_flag_id,
                       user_or_actor=a.user_or_actor, action=a.action,
                       entity_type=a.entity_type, entity_id=a.entity_id,
                       old_value=a.old_value or "", new_value=a.new_value or "",
                       timestamp=a.timestamp or "", metadata=a.meta or {})
