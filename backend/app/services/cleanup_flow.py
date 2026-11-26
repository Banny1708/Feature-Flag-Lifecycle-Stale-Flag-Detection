"""Governed Piranha cleanup flow shared by both removal APIs.

Single implementation of: safety branch -> language gate -> real Piranha
cleanup -> actual git diff -> tests -> syntax check -> reference re-scan ->
verification -> post-cleanup FlagShark re-scan -> lifecycle/audit.

The legacy `POST /api/flags/{id}/remove` and the governed
`POST /api/removals` both delegate here; they differ only in preconditions
(risk/lifecycle guards live in the routers, not here).

Approval and dry-run purity are enforced by callers: this function always
modifies the worktree (never call it for a dry-run) and must only run on a
safety branch after user approval.
"""
from __future__ import annotations

from pathlib import Path

from sqlalchemy.orm import Session

from ..models.models import (EvidenceRecord, FeatureFlag, RemovalOperation,
                             Repository, TestRun, VerificationResult)
from . import flagshark_service, git_service, piranha_service, test_service
from .audit_service import log as audit_log
from .lifecycle_service import LifecycleError, transition
from ..utils.helpers import new_id, utcnow_iso


class CleanupFlowError(Exception):
    def __init__(self, code: str, message: str, http_status: int = 500):
        super().__init__(f"[{code}] {message}")
        self.code = code
        self.message = message
        self.http_status = http_status


def _fail(db: Session, op: RemovalOperation, flag: FeatureFlag | None,
          code: str, message: str, new_status: str = "FAILED") -> None:
    op.status = new_status
    op.verification_status = "FAILED"
    op.completed_at = utcnow_iso()
    if code == "UNSUPPORTED_LANGUAGE":
        op.cleanup_status = "UNSUPPORTED"
    elif code == "NO_CHANGES":
        op.cleanup_status = "NO_CHANGES"
    audit_log(db, "CLEANUP_FAILED", entity_type="removal_operation",
              entity_id=op.id, feature_flag_id=op.flag_id,
              project_id=getattr(flag, "project_id", None),
              new_value=f"{code}: {message[:300]}")
    db.commit()


def record_post_cleanup_scan(db: Session, repo_path: Path, flag: FeatureFlag,
                             operation_id: str) -> dict:
    """Re-scan with FlagShark after cleanup; never fails the operation."""
    try:
        det = flagshark_service.run_detection(repo_path)
    except Exception as exc:  # defensive: evidence must never break cleanup
        det = {"engine": "unavailable", "findings": [], "error": str(exc)[:300]}
    remaining = [f for f in det.get("findings", []) if f.get("flag_key") == flag.key]
    target_present = len(remaining) > 0
    try:
        db.add(EvidenceRecord(
            id=new_id("evi"), flag_id=flag.id, flag_name=flag.key,
            repository_name=flag.repository_name,
            evidence_type="post-cleanup-scan",
            confidence_score=0.9 if not target_present else 0.5,
            detected_at=utcnow_iso(), source=str(det.get("engine", "")),
            summary=(f"Post-cleanup re-scan: target {'STILL PRESENT' if target_present else 'REMOVED'} "
                     f"({len(remaining)} reference(s)); engine {det.get('engine', '')}."),
            severity="HIGH" if target_present else "LOW",
            value=str(len(remaining)),
            payload={"operation_id": operation_id,
                     "target_present": target_present,
                     "engine": str(det.get("engine", ""))}))
        db.flush()
        audit_log(db, "CLEANUP_RESCANNED", entity_type="removal_operation",
                  entity_id=operation_id, feature_flag_id=flag.id,
                  project_id=getattr(flag, "project_id", None),
                  new_value=f"target_present={target_present}")
    except Exception:
        pass
    return {"target_present": target_present,
            "remaining": len(remaining),
            "engine": str(det.get("engine", ""))}


def run_governed_cleanup(db: Session, flag: FeatureFlag, repo: Repository | None,
                         permanent_value: str = "false",
                         executed_by: str = "local-user",
                         tool_target: str = "Piranha",
                         analysis_run_id: str | None = None,
                         manage_lifecycle: bool = True) -> RemovalOperation:
    """Execute the full cleanup flow. Raises CleanupFlowError on any failure
    (the persisted operation is always marked FAILED first — never silent)."""
    rp = Path(repo.local_path) if repo and repo.local_path else None
    if not rp or not rp.exists():
        raise CleanupFlowError("CHECKOUT_UNAVAILABLE",
                               "repository local checkout UNAVAILABLE; cannot remove safely",
                               http_status=400)
    ok, _ = git_service.git_available()
    if not ok or not git_service.is_git_repo(rp):
        raise CleanupFlowError("GIT_UNAVAILABLE",
                               "git safety branch unavailable; removal refused",
                               http_status=400)

    op = RemovalOperation(
        id=new_id("op"), flag_id=flag.id, flag_name=flag.key,
        repository_id=repo.id, repository_name=repo.name,
        target_branch=repo.default_branch, status="RUNNING",
        tool_target=tool_target or "Piranha",
        executed_by=executed_by or "local-user")
    op.operation_type = "REMOVE"  # type: ignore[attr-defined]
    op.started_at = utcnow_iso()  # type: ignore[attr-defined]
    if analysis_run_id:
        op.analysis_run_id = analysis_run_id  # type: ignore[attr-defined]
    db.add(op)
    db.flush()
    audit_log(db, "CLEANUP_REQUESTED", entity_type="removal_operation",
              entity_id=op.id, feature_flag_id=flag.id,
              project_id=getattr(flag, "project_id", None),
              new_value=f"{flag.key} -> {permanent_value}")

    # Language gate: only verified Piranha languages proceed.
    piranha_lang = piranha_service.repo_language_to_piranha(repo.language)
    if not piranha_lang:
        _fail(db, op, flag, "UNSUPPORTED_LANGUAGE",
              f"repository language '{repo.language or 'unknown'}' has no verified "
              f"Piranha rule configuration (supported: "
              f"{', '.join(piranha_service.SUPPORTED_LANGUAGES)}); refusing cleanup")
        raise CleanupFlowError("UNSUPPORTED_LANGUAGE", op.stderr_log or
                               "unsupported language for Piranha cleanup",
                               http_status=422)
    try:
        config = piranha_service.build_config(
            piranha_lang, flag.key, permanent_value, dry_run=False)
    except piranha_service.PiranhaError as exc:
        _fail(db, op, flag, exc.code, exc.message)
        raise CleanupFlowError(exc.code, exc.message, http_status=422)

    safety = piranha_service.create_safety_branch(rp, flag.key)
    if not safety["ok"]:
        op.stderr_log = safety["error"]
        _fail(db, op, flag, "SAFETY_BRANCH_FAILED",
              f"safety branch creation failed: {safety['error']}")
        raise CleanupFlowError("SAFETY_BRANCH_FAILED", safety["error"],
                               http_status=500)
    op.safety_branch = safety["branch"]
    op.base_commit = safety["base_commit"]
    op.commit_hash_before = safety["base_commit"]  # type: ignore[attr-defined]
    op.backup_location = f"git branch {safety['branch']} @ {safety['base_commit']}"  # type: ignore[attr-defined]
    db.flush()

    # Dirty-worktree gate: sequential cleanups must not conflate diffs.
    # The operator must commit/stash or roll back before the next removal.
    if not git_service.tracked_clean(rp):
        _fail(db, op, flag, "DIRTY_WORKTREE",
              "worktree has uncommitted tracked changes; commit, stash, or roll back "
              "before running another cleanup")
        raise CleanupFlowError("DIRTY_WORKTREE",
                               "worktree has uncommitted tracked changes",
                               http_status=422)

    # Real Piranha execution (isolated subprocess, timeout-guarded).
    try:
        result = piranha_service.run_cleanup(rp, config)
    except piranha_service.PiranhaError as exc:
        op.stderr_log = exc.message
        _fail(db, op, flag, exc.code, exc.message)
        status = 504 if exc.code == "TIMEOUT" else 500
        raise CleanupFlowError(exc.code, exc.message, http_status=status)
    op.stdout_log = f"rules applied: {[r['rule'] for r in result.rewrites][:50]}"
    op.stderr_log = result.stderr
    audit_log(db, "CLEANUP_EXECUTED", entity_type="removal_operation",
              entity_id=op.id, feature_flag_id=flag.id,
              project_id=getattr(flag, "project_id", None),
              new_value=f"{result.cleanup_status}: {len(result.files_changed)} file(s)")

    # Actual git diff (unified) — never synthesized.
    diff = piranha_service.capture_diff(rp)
    op.files_affected = len(diff["files"])
    op.lines_added = diff["lines_added"]
    op.lines_removed = diff["lines_removed"]
    op.diff_summary = (diff["unified"] or diff["stat"] or "")[:60000]
    cur = git_service.collect_git_evidence(rp)
    op.commit_hash_after = (cur.get("commit", "") or "")[:128] if cur.get("available") else ""  # type: ignore[attr-defined]
    db.flush()

    # Tests on the modified worktree.
    tres = test_service.run_tests(rp)
    tr = TestRun(id=new_id("test"), operation_id=op.id, repository_id=repo.id,
                 command=tres.get("command", ""), status=tres.get("status", "failed"),
                 success=1 if tres.get("success") else 0,
                 test_count=tres.get("test_count", 0),
                 failed_tests=tres.get("failed", []),
                 output=(tres.get("output", "") or "")[:20000])
    jac = test_service.find_jacoco_xml(rp)
    if jac:
        summ = test_service.parse_jacoco_summary(jac)
        tr.branch_coverage = summ.get("branch_coverage", "unavailable")
        tr.line_coverage = summ.get("line_coverage", "unavailable")
    db.add(tr)
    db.flush()

    # Reference re-scan: is the flag actually gone?
    remaining = 0
    try:
        for p in rp.rglob("*"):
            if not p.is_file() or ".git" in p.parts:
                continue
            try:
                if p.stat().st_size < 1_000_000 and flag.key in p.read_text(
                        encoding="utf-8", errors="ignore"):
                    remaining += 1
            except Exception:
                continue
    except Exception:
        remaining = -1

    # Syntax check on changed Python files (Piranha validates its own
    # output, but an independent check closes the loop for nested blocks).
    syntax_failures = piranha_service.verify_python_syntax(diff["files"], rp)
    syntax_ok = not syntax_failures

    if result.cleanup_status == "NO_CHANGES":
        op.cleanup_status = "NO_CHANGES"
        verdict, op.status = "FAILED", "FAILED"
        op.verification_status = "FAILED"
        detail = "Piranha made no changes (pattern unsupported or flag unmatched)"
    elif remaining == 0 and tres.get("success") and syntax_ok:
        op.cleanup_status = "APPLIED"
        verdict, op.status = "SUCCESS", "SUCCESS"
        op.verification_status = "SUCCESS"
        detail = "flag references removed, tests green, syntax valid"
    else:
        op.cleanup_status = "APPLIED"
        verdict, op.status = "FAILED", "FAILED"
        op.verification_status = "FAILED"
        reasons = []
        if remaining != 0:
            reasons.append(f"{remaining} file(s) still reference {flag.key}")
        if not tres.get("success"):
            reasons.append(f"tests {tres.get('status')}")
        if not syntax_ok:
            reasons.extend(syntax_failures[:3])
        detail = "; ".join(reasons) or "verification failed"
    op.completed_at = utcnow_iso()
    ver = VerificationResult(
        id=new_id("verif"), operation_id=op.id, flag_id=flag.id,
        flag_name=flag.key, repository_name=repo.name,
        test_suite_status=tres.get("status", "failed"),
        build_status="passed" if tres.get("success") else "failed",
        ast_validation_status="passed" if (remaining == 0 and syntax_ok) else "failed",
        dead_code_eliminated=1 if remaining == 0 else 0,
        syntax_valid=1 if syntax_ok else 0,
        regression_detected=0 if tres.get("success") else 1,
        unresolved_references=max(0, remaining), verified_at=utcnow_iso(),
        summary=(f"Cleanup {verdict}: {op.files_affected} file(s) changed; {detail}. "
                 f"Safety branch {op.safety_branch} preserved."),
        test_output_summary=(tres.get("output", "") or "")[:2000])
    db.add(ver)

    if verdict == "SUCCESS":
        if manage_lifecycle:
            try:
                transition(db, flag, "REMOVED", action="CLEANUP_COMPLETED",
                           metadata={"operation_id": op.id})
            except LifecycleError as exc:
                db.commit()
                raise CleanupFlowError("LIFECYCLE_ERROR",
                                       f"cleanup succeeded but lifecycle transition failed: {exc}",
                                       http_status=500)
        else:
            flag.status = "removed"
            try:
                flag.lifecycle_state = "REMOVED"  # type: ignore[attr-defined]
            except Exception:
                pass
        audit_log(db, "CLEANUP_VERIFIED", entity_type="removal_operation",
                  entity_id=op.id, feature_flag_id=flag.id,
                  project_id=getattr(flag, "project_id", None),
                  new_value="SUCCESS")
    else:
        audit_log(db, "CLEANUP_FAILED", entity_type="removal_operation",
                  entity_id=op.id, feature_flag_id=flag.id,
                  project_id=getattr(flag, "project_id", None),
                  new_value=detail[:300])
    db.commit()

    # Post-cleanup FlagShark re-scan (evidence only; never fails the op).
    try:
        record_post_cleanup_scan(db, rp, flag, op.id)
        db.commit()
    except Exception:
        pass
    db.refresh(op)
    return op
