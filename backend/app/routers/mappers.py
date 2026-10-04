"""DB row -> response schema (camelCase via aliases)."""
from __future__ import annotations

from ..models.models import (
    CodePath,
    CodeReference,
    EvidenceRecord,
    FeatureFlag,
    RemovalOperation,
    Repository,
    Report,
    RiskAssessment,
    Scan,
    TestRun,
    VerificationResult,
)
from ..schemas.schemas import (
    CodePathOut,
    CodeReferenceOut,
    DiffCheckOut,
    EvidenceOut,
    FeatureFlagOut,
    RemovalOut,
    ReportOut,
    ReportSummaryOut,
    RepositoryOut,
    RiskAssessmentOut,
    RiskFactorOut,
    ScanFindingOut,
    ScanOut,
    TestRunOut,
    UsageMetricsOut,
    VerificationOut,
)
from ..utils.helpers import parse_boolish


def repo_out(r: Repository) -> RepositoryOut:
    return RepositoryOut(id=r.id, name=r.name, full_name=r.full_name, owner=r.owner, url=r.url,
                         default_branch=r.default_branch, language=r.language, scan_status=r.scan_status,
                         last_scanned_at=r.last_scanned_at, total_flags=r.total_flags,
                         active_flags=r.active_flags, stale_flags=r.stale_flags,
                         potentially_stale_flags=r.potentially_stale_flags, lines_of_code=r.lines_of_code)


def scan_out(s: Scan, findings: list | None = None) -> ScanOut:
    fs = findings if findings is not None else getattr(s, "findings", []) or []
    return ScanOut(id=s.id, repository_id=s.repository_id, repository_name=s.repository_name,
                   timestamp=s.timestamp, status=s.status,
                   total_flags_detected=s.total_flags_detected,
                   stale_flags_detected=s.stale_flags_detected, scanner_engine=s.scanner_engine,
                   scan_duration_ms=s.scan_duration_ms, commit_hash=s.commit_hash, branch=s.branch,
                   findings=[ScanFindingOut(flag_key=f.flag_key, file_path=f.file_path,
                                            line_number=f.line_number, ast_node_type=f.ast_node_type,
                                            is_stale=bool(f.is_stale), confidence=f.confidence,
                                            reason=f.reason) for f in fs])


def flag_out(f: FeatureFlag) -> FeatureFlagOut:
    stale = f.stale_since or None
    return FeatureFlagOut(id=f.id, name=f.name, key=f.key, description=f.description,
                          repository_id=f.repository_id, repository_name=f.repository_name,
                          status=f.status, risk=f.risk, flag_type=f.flag_type, owner=f.owner,
                          owner_team=f.owner_team or None, created_at=f.created_at_flag,
                          last_modified=f.last_modified, stale_since=stale,
                          metrics=UsageMetricsOut(evaluations_count=f.evaluations_count,
                                                  evaluations_last7d=f.evaluations_last_7d,
                                                  days_inactive=f.days_inactive,
                                                  rollout_percentage=f.rollout_percentage,
                                                  environment=f.environment),
                          tags=f.tags or [], default_value=parse_boolish(f.default_value))


def evidence_out(e: EvidenceRecord) -> EvidenceOut:
    return EvidenceOut(id=e.id, flag_id=e.flag_id, flag_name=e.flag_name,
                       repository_name=e.repository_name, evidence_type=e.evidence_type,
                       confidence_score=e.confidence_score, detected_at=e.detected_at,
                       source=e.source, summary=e.summary, severity=e.severity or "",
                       value=e.value or "", payload=e.payload or {})


def ref_out(r: CodeReference) -> CodeReferenceOut:
    return CodeReferenceOut(id=r.id, flag_id=r.flag_id, flag_name=r.flag_name,
                            repository_id=r.repository_id, repository_name=r.repository_name,
                            file_path=r.file_path, line_number=r.line_number,
                            column_number=r.column_number, code_snippet=r.code_snippet,
                            reference_type=r.reference_type,
                            is_enclosing_control_flow=bool(r.is_enclosing_control_flow),
                            ast_node_type=r.ast_node_type)


def path_out(p: CodePath) -> CodePathOut:
    return CodePathOut(id=p.id, flag_id=p.flag_id, file_path=p.file_path,
                       branch_condition=p.branch_condition,
                       reachable_state=bool(p.reachable_state),
                       dead_code_lines=p.dead_code_lines or [],
                       dead_code_snippet=p.dead_code_snippet,
                       complexity_reduction_score=p.complexity_reduction_score,
                       true_branch=p.true_branch or "", false_branch=p.false_branch or "",
                       functions_involved=p.functions_involved or [],
                       coverage_status=p.coverage_status or "unavailable")


def risk_out(a: RiskAssessment) -> RiskAssessmentOut:
    factors = [RiskFactorOut(category=f.category, description=f.description,
                             score=f.score, level=f.level) for f in (a.factors or [])]
    lvl = (a.overall_risk or "medium").upper()
    return RiskAssessmentOut(id=a.id, flag_id=a.flag_id, flag_name=a.flag_name,
                             overall_risk=a.overall_risk, risk_level=lvl, score=a.score or a.blast_radius_score,
                             blast_radius_score=a.blast_radius_score, factors=factors,
                             recommendations=a.recommendations or [],
                             assessed_at=a.assessed_at,
                             estimated_cleanup_hours=a.estimated_cleanup_hours)


def removal_out(o: RemovalOperation) -> RemovalOut:
    return RemovalOut(id=o.id, flag_id=o.flag_id, flag_name=o.flag_name,
                      repository_id=o.repository_id, repository_name=o.repository_name,
                      target_branch=o.target_branch, pr_url=o.pr_url or None,
                      pr_number=o.pr_number or None, status=o.status,
                      tool_target=o.tool_target, files_affected=o.files_affected,
                      lines_removed=o.lines_removed, lines_added=o.lines_added,
                      created_at=o.created_at.isoformat() if hasattr(o.created_at, "isoformat") else "",
                      completed_at=o.completed_at or None, executed_by=o.executed_by,
                      diff_summary=o.diff_summary or None, safety_branch=o.safety_branch or "",
                      base_commit=o.base_commit or "", verification_status=o.verification_status or "UNVERIFIED")


def verification_out(v: VerificationResult) -> VerificationOut:
    return VerificationOut(id=v.id, operation_id=v.operation_id, flag_id=v.flag_id,
                           flag_name=v.flag_name, repository_name=v.repository_name,
                           test_suite_status=v.test_suite_status, build_status=v.build_status,
                           ast_validation_status=v.ast_validation_status,
                           diff_analysis=DiffCheckOut(dead_code_eliminated=bool(v.dead_code_eliminated),
                                                      syntax_valid=bool(v.syntax_valid),
                                                      regression_detected=bool(v.regression_detected),
                                                      unresolved_references=v.unresolved_references),
                           verified_at=v.verified_at, summary=v.summary,
                           test_output_summary=v.test_output_summary or None)


def testrun_out(t: TestRun) -> TestRunOut:
    return TestRunOut(id=t.id, operation_id=t.operation_id, repository_id=t.repository_id,
                      command=t.command, status=t.status, success=bool(t.success),
                      test_count=t.test_count, failed_tests=t.failed_tests or [],
                      output=(t.output or "")[-6000:], branch_coverage=t.branch_coverage,
                      line_coverage=t.line_coverage)


def report_out(r: Report) -> ReportOut:
    return ReportOut(id=r.id, title=r.title, type=r.type, generated_at=r.generated_at,
                     repository_id=r.repository_id or None,
                     repository_name=r.repository_name or None,
                     summary=ReportSummaryOut(total_scanned_flags=r.total_scanned_flags,
                                              stale_flags_identified=r.stale_flags_identified,
                                              removal_operations_completed=r.removal_operations_completed,
                                              tech_debt_reduction_hours=r.tech_debt_reduction_hours,
                                              code_lines_eliminated=r.code_lines_eliminated),
                     download_format=r.download_format, status=r.status)
