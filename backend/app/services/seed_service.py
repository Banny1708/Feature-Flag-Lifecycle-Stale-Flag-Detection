"""Seed SQLite from the existing frontend mocks so the UI works immediately.

Reads ../src/data/mock*.ts? No — TS can't be imported. Instead we embed a
compact representative seed (mirrors mock data shapes) on first run.
Seed only runs when tables are empty; real scans/removals append afterwards.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from ..models.models import (
    CodePath,
    CodeReference,
    EvidenceRecord,
    FeatureFlag,
    RemovalOperation,
    Repository,
    Report,
    RiskAssessment,
    RiskFactor,
    Scan,
    ScanFinding,
    VerificationResult,
)
from ..utils.helpers import utcnow_iso

SEED_REPOS = [
    {"id": "repo-01", "name": "core-checkout-service", "full_name": "acme-corp/core-checkout-service",
     "owner": "Payments Team", "url": "https://github.com/acme-corp/core-checkout-service",
     "default_branch": "main", "language": "TypeScript", "scan_status": "completed",
     "last_scanned_at": "2026-09-21T14:30:00Z", "total_flags": 24, "active_flags": 14,
     "stale_flags": 6, "potentially_stale_flags": 4, "lines_of_code": 84200},
    {"id": "repo-02", "name": "api-gateway", "full_name": "acme-corp/api-gateway",
     "owner": "Platform Infrastructure", "url": "https://github.com/acme-corp/api-gateway",
     "default_branch": "main", "language": "Go", "scan_status": "completed",
     "last_scanned_at": "2026-09-20T09:15:00Z", "total_flags": 18, "active_flags": 11,
     "stale_flags": 4, "potentially_stale_flags": 3, "lines_of_code": 62100},
    {"id": "repo-03", "name": "customer-portal-web", "full_name": "acme-corp/customer-portal-web",
     "owner": "Frontend Guild", "url": "https://github.com/acme-corp/customer-portal-web",
     "default_branch": "main", "language": "TypeScript / React", "scan_status": "scanning",
     "last_scanned_at": "2026-09-21T16:45:00Z", "total_flags": 32, "active_flags": 18,
     "stale_flags": 8, "potentially_stale_flags": 6, "lines_of_code": 115400},
    {"id": "repo-04", "name": "auth-identity-engine", "full_name": "acme-corp/auth-identity-engine",
     "owner": "Security Core", "url": "https://github.com/acme-corp/auth-identity-engine",
     "default_branch": "master", "language": "Java", "scan_status": "completed",
     "last_scanned_at": "2026-09-19T21:00:00Z", "total_flags": 15, "active_flags": 8,
     "stale_flags": 4, "potentially_stale_flags": 3, "lines_of_code": 58700},
    {"id": "repo-05", "name": "search-ranking-service", "full_name": "acme-corp/search-ranking-service",
     "owner": "Search & Discovery", "url": "https://github.com/acme-corp/search-ranking-service",
     "default_branch": "main", "language": "Python", "scan_status": "idle",
     "last_scanned_at": "2026-09-15T10:00:00Z", "total_flags": 9, "active_flags": 6,
     "stale_flags": 2, "potentially_stale_flags": 1, "lines_of_code": 31400},
]

SEED_FLAGS = [
    {"id": "flag-01", "name": "Apple Pay V2 Integration", "key": "ENABLE_APPLE_PAY_V2",
     "description": "Native Apple Pay express checkout.", "repository_id": "repo-01",
     "repository_name": "core-checkout-service", "status": "active", "risk": "medium",
     "flag_type": "release", "owner": "sarah.chen@acme.internal", "owner_team": "Payments Team",
     "created_at_flag": "2026-08-10T10:00:00Z", "last_modified": "2026-09-18T14:22:00Z",
     "stale_since": "", "evaluations_count": 1420500, "evaluations_last_7d": 382000,
     "days_inactive": 0, "rollout_percentage": 75, "environment": "production",
     "tags": ["checkout", "payment-methods"], "default_value": "false"},
    {"id": "flag-02", "name": "Legacy OAuth V1 Fallback", "key": "LEGACY_OAUTH_V1_FALLBACK",
     "description": "Fallback auth for pre-2022 API clients.", "repository_id": "repo-04",
     "repository_name": "auth-identity-engine", "status": "stale", "risk": "critical",
     "flag_type": "operational", "owner": "alex.rodriguez@acme.internal", "owner_team": "Security Core",
     "created_at_flag": "2023-03-15T08:00:00Z", "last_modified": "2024-01-10T11:00:00Z",
     "stale_since": "2024-06-01T00:00:00Z", "evaluations_count": 120, "evaluations_last_7d": 0,
     "days_inactive": 284, "rollout_percentage": 100, "environment": "production",
     "tags": ["security", "tech-debt"], "default_value": "true"},
    {"id": "flag-04", "name": "Deprecated Stripe Webhook Handler", "key": "DEPRECATED_STRIPE_WEBHOOK",
     "description": "Legacy Stripe v1 webhook path.", "repository_id": "repo-01",
     "repository_name": "core-checkout-service", "status": "stale", "risk": "high",
     "flag_type": "operational", "owner": "jordan.lee@acme.internal", "owner_team": "Payments Team",
     "created_at_flag": "2024-01-20T08:00:00Z", "last_modified": "2024-03-25T11:00:00Z",
     "stale_since": "2024-09-25T00:00:00Z", "evaluations_count": 45, "evaluations_last_7d": 0,
     "days_inactive": 180, "rollout_percentage": 100, "environment": "production",
     "tags": ["payments", "legacy-deprecations"], "default_value": "false"},
    {"id": "flag-03", "name": "Search Algorithm V3", "key": "ROLLOUT_NEW_SEARCH_ALGO",
     "description": "Vector blended search ranking.", "repository_id": "repo-03",
     "repository_name": "customer-portal-web", "status": "potentially-stale", "risk": "high",
     "flag_type": "experiment", "owner": "dmitri.ivanov@acme.internal", "owner_team": "Search & Discovery",
     "created_at_flag": "2026-04-02T12:00:00Z", "last_modified": "2026-07-20T16:40:00Z",
     "stale_since": "2026-08-20T00:00:00Z", "evaluations_count": 4950000, "evaluations_last_7d": 890000,
     "days_inactive": 62, "rollout_percentage": 100, "environment": "production",
     "tags": ["search", "ai-ml"], "default_value": "false"},
]


def seed_if_empty(db: Session) -> bool:
    if db.query(Repository).count() > 0:
        return False
    now = utcnow_iso()
    for r in SEED_REPOS:
        db.add(Repository(**r))
    for f in SEED_FLAGS:
        db.add(FeatureFlag(**f))
    db.add(Scan(id="scan-01", repository_id="repo-01", repository_name="core-checkout-service",
                timestamp="2026-09-21T14:30:00Z", status="success", total_flags_detected=24,
                stale_flags_detected=6, scanner_engine="FlagShark-engine", scan_duration_ms=4210,
                commit_hash="7c8b21e", branch="main"))
    db.add(ScanFinding(id="find-01", scan_id="scan-01", flag_key="DEPRECATED_STRIPE_WEBHOOK",
                       file_path="src/services/webhookHandler.ts", line_number=142,
                       ast_node_type="IfStatement", is_stale=1, confidence=0.98,
                       reason="Condition statically false for >180 days."))
    db.add(EvidenceRecord(id="evi-01", flag_id="flag-04", flag_name="DEPRECATED_STRIPE_WEBHOOK",
                          repository_name="core-checkout-service", evidence_type="zero-traffic",
                          confidence_score=0.99, detected_at="2026-09-21T02:00:00Z",
                          source="DataDog Metrics Ingestion",
                          summary="0 evaluations in production for 180 days.",
                          severity="HIGH", value="180 days",
                          payload={"zeroDaysObserved": 180}))
    db.add(CodeReference(id="ref-02", flag_id="flag-04", flag_name="DEPRECATED_STRIPE_WEBHOOK",
                         repository_id="repo-01", repository_name="core-checkout-service",
                         file_path="src/services/webhookHandler.ts", line_number=142, column_number=8,
                         code_snippet="if (flagClient.evaluate('DEPRECATED_STRIPE_WEBHOOK')) { return handleLegacyStripePayload(payload); }",
                         reference_type="check", is_enclosing_control_flow=1, ast_node_type="IfStatement"))
    db.add(CodePath(id="path-01", flag_id="flag-04", file_path="src/services/webhookHandler.ts",
                    branch_condition="DEPRECATED_STRIPE_WEBHOOK == true", reachable_state=0,
                    dead_code_lines=[143, 144], dead_code_snippet="return handleLegacyStripePayload(payload);",
                    complexity_reduction_score=18, coverage_status="unavailable"))
    db.add(RiskAssessment(id="risk-02", flag_id="flag-02", flag_name="LEGACY_OAUTH_V1_FALLBACK",
                          overall_risk="critical", blast_radius_score=88,
                          recommendations=["Coordinate with partner clients before removal."],
                          assessed_at="2026-09-20T10:00:00Z", estimated_cleanup_hours=14, score=88))
    db.add(RiskFactor(id="rf-01", assessment_id="risk-02", category="Blast Radius",
                      description="Affects global auth filter chain.", score=92, level="critical"))
    db.add(RemovalOperation(id="op-01", flag_id="flag-04", flag_name="DEPRECATED_STRIPE_WEBHOOK",
                            repository_id="repo-01", repository_name="core-checkout-service",
                            target_branch="main", pr_url="https://github.com/acme-corp/core-checkout-service/pull/412",
                            pr_number=412, status="in-review", tool_target="Piranha", files_affected=3,
                            lines_removed=64, lines_added=2, completed_at="",
                            executed_by="jordan.lee@acme.internal",
                            diff_summary="Eliminated legacy Stripe v1 webhook handler."))
    db.add(VerificationResult(id="verif-01", operation_id="op-01", flag_id="flag-04",
                              flag_name="DEPRECATED_STRIPE_WEBHOOK", repository_name="core-checkout-service",
                              test_suite_status="passed", build_status="passed", ast_validation_status="passed",
                              dead_code_eliminated=1, syntax_valid=1, regression_detected=0,
                              unresolved_references=0, verified_at="2026-09-21T09:15:00Z",
                              summary="148/148 tests passed.", test_output_summary="All 148 tests passed in 42.4s."))
    db.add(Report(id="rep-01", title="Q3 Enterprise Stale Flag Elimination Audit", type="stale-summary",
                  generated_at="2026-09-21T08:00:00Z", total_scanned_flags=98, stale_flags_identified=24,
                  removal_operations_completed=14, tech_debt_reduction_hours=72,
                  code_lines_eliminated=1480, download_format="json", status="ready"))
    db.commit()
    return True
