"""Analysis runs, detection results, untested paths, risk, dry-run/removal/rollback, evidence, audit."""
from __future__ import annotations

import time
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..database import get_db
from ..models.lifecycle_models import (
    ANALYSIS_TYPES,
    AnalysisRun,
    AuditLog,
    DetectionResult,
    FlagEvaluation,
    UntestedPath,
)
from ..models.models import (
    CodePath,
    CodeReference,
    EvidenceRecord,
    FeatureFlag,
    RemovalOperation,
    Repository,
    RiskAssessment,
    RiskFactor,
    TestRun,
    VerificationResult,
)
from ..schemas.lifecycle_schemas import (
    AnalysisRunCreate,
    AnalysisRunOut,
    AuditLogOut,
    DetectionResultOut,
    DryRunIn,
    EvidenceOut2,
    RemovalCreate2,
    RiskAssessmentCreate,
    UntestedPathOut,
)
from ..schemas.schemas import RemovalOut, RiskAssessmentOut
from ..services import audit_service, detection_service, flagshark_service, git_service, lifecycle_service
from ..services import piranha_service, risk_service, test_service
from ..services.cleanup_flow import CleanupFlowError, run_governed_cleanup
from ..services.lifecycle_service import LifecycleError
from ..utils.helpers import new_id, utcnow_iso
from .lifecycle_mappers import (
    audit_out,
    detection_out,
    evidence2_out,
    run_out,
    untested_out,
)
from .mappers import removal_out, risk_out

router = APIRouter(tags=["analysis"])


def _flag_or_404(db: Session, flag_id: str) -> FeatureFlag:
    f = db.get(FeatureFlag, flag_id) or db.query(FeatureFlag).filter_by(key=flag_id).first()
    if not f:
        raise HTTPException(status_code=404, detail="flag not found")
    return f


def _git_touch_days(repo: Repository | None, flag_key: str) -> int | None:
    if not repo or not repo.local_path or not Path(repo.local_path).exists():
        return None
    try:
        from datetime import datetime
        hist = git_service.flag_git_history(Path(repo.local_path), flag_key, limit=1)
        if hist.get("available") and hist.get("commits"):
            dt = datetime.fromisoformat(hist["commits"][0]["date"].replace("Z", "+00:00"))
            return (datetime.now(dt.tzinfo) - dt).days
    except Exception:
        return None
    return None


# ------------------------------------------------------------------ analysis
@router.get("/api/analysis", response_model=list[AnalysisRunOut])
def list_runs(db: Session = Depends(get_db)):
    return [run_out(r) for r in
            db.query(AnalysisRun).order_by(AnalysisRun.created_at.desc()).limit(100).all()]


@router.get("/api/analysis/{analysis_id}", response_model=AnalysisRunOut)
def get_run(analysis_id: str, db: Session = Depends(get_db)):
    r = db.get(AnalysisRun, analysis_id)
    if not r:
        raise HTTPException(status_code=404, detail="analysis run not found")
    return run_out(r)


@router.post("/api/analysis/run", response_model=AnalysisRunOut, status_code=201,
             summary="Run detection workflow; persists run, detections, untested paths, evidence, audit")
def run_analysis(body: AnalysisRunCreate, db: Session = Depends(get_db)):
    if body.analysis_type not in ANALYSIS_TYPES:
        raise HTTPException(status_code=422, detail=f"unknown analysis_type '{body.analysis_type}'")
    started = time.time()
    run = AnalysisRun(id=new_id("run"), project_id=body.project_id,
                      repository_id=body.repository_id, analysis_type=body.analysis_type,
                      tool_name="FlagShark", started_at=utcnow_iso(), status="RUNNING",
                      configuration=body.configuration or {})
    fs = flagshark_service.flagshark_status()
    run.tool_version = (fs.get("version", "") or "")[:300]
    db.add(run)
    db.flush()
    from .settings import get_effective_settings
    thresholds = get_effective_settings(db)
    audit_service.log(db, "ANALYSIS_STARTED", entity_type="analysis_run", entity_id=run.id,
                      project_id=body.project_id,
                      metadata={"type": body.analysis_type, "thresholds": thresholds})

    try:
        q = db.query(FeatureFlag)
        if body.repository_id:
            q = q.filter_by(repository_id=body.repository_id)
        if body.project_id:
            q = q.filter_by(project_id=body.project_id)
        flags = q.limit(500).all()
        stale_n = untested_n = candidates_n = 0
        for f in flags:
            repo = db.get(Repository, f.repository_id) if f.repository_id else None
            latest_eval = (db.query(FlagEvaluation).filter_by(feature_flag_id=f.id)
                           .order_by(FlagEvaluation.created_at.desc()).first())
            # Only real FlagEvaluation rows count as evidence; the legacy
            # evaluations_last_7d default of 0 on new flags is NOT evidence.
            eval_info = {"evaluations_last_7d": latest_eval.evaluation_count} if latest_eval else None
            ref_count = db.query(CodeReference).filter_by(flag_id=f.id).count()
            # ref_count None would mean "no info"; count 0 is real info (scan ran, nothing found)
            has_scan = db.query(CodeReference).filter_by(flag_id=f.id).first() is not None or ref_count > 0
            verdict = detection_service.evaluate(
                {"days_inactive": f.days_inactive, "rollout_percentage": f.rollout_percentage,
                 "last_modified": f.last_modified, "expected_expiry_date": getattr(f, "expected_expiry_date", "") or "",
                 "evaluations_last_7d": f.evaluations_last_7d},
                eval_info, ref_count if (has_scan or ref_count) else None,
                _git_touch_days(repo, f.key), thresholds)
            det = DetectionResult(id=new_id("det"), analysis_run_id=run.id,
                                  feature_flag_id=f.id, detection_status=verdict["detection_status"],
                                  stale_score=verdict["stale_score"], confidence=verdict["confidence"],
                                  reason="; ".join(verdict["reasons"])[:2000],
                                  evidence_summary={"signals": verdict["signals"],
                                                    "action": verdict["recommended_action"]},
                                  detected_at=utcnow_iso())
            db.add(det)
            db.add(EvidenceRecord(id=new_id("evi"), flag_id=f.id, flag_name=f.key,
                                  repository_name=f.repository_name, evidence_type="DETECTION_RESULT",
                                  confidence_score=verdict["confidence"], detected_at=utcnow_iso(),
                                  source="detection-engine",
                                  summary=f"{verdict['detection_status']} (score {verdict['stale_score']})",
                                  severity="HIGH" if verdict["detection_status"] == "STALE" else "MEDIUM",
                                  value=str(verdict["stale_score"]),
                                  payload={"reasons": verdict["reasons"]},
                                  project_id=getattr(f, "project_id", None),
                                  analysis_run_id=run.id))
            if verdict["detection_status"] in ("STALE", "CANDIDATE"):
                try:
                    lifecycle_service.transition(db, f, "STALE_CANDIDATE", action="STALE_FLAG_DETECTED",
                                                 metadata={"run_id": run.id, "score": verdict["stale_score"]})
                except LifecycleError:
                    audit_service.log(db, "STALE_FLAG_DETECTED", entity_type="feature_flag",
                                      entity_id=f.id, feature_flag_id=f.id,
                                      project_id=getattr(f, "project_id", None),
                                      new_value=verdict["detection_status"],
                                      metadata={"run_id": run.id, "note": "lifecycle unchanged (transition not valid yet)"})
                if verdict["detection_status"] == "STALE":
                    stale_n += 1
                else:
                    candidates_n += 1
            # untested paths for this flag
            for p in db.query(CodePath).filter_by(flag_id=f.id).all():
                cov = (p.coverage_status or "unavailable").lower()
                if cov in ("unavailable", "uncovered"):
                    lvl = "HIGH" if cov == "uncovered" else "MEDIUM"
                    db.add(UntestedPath(id=new_id("unp"), analysis_run_id=run.id,
                                        feature_flag_id=f.id, code_path_id=p.id,
                                        risk_level=lvl,
                                        reason=f"flag-controlled branch without test coverage proof ({cov})",
                                        test_coverage=p.coverage_status or "unavailable",
                                        detected_at=utcnow_iso()))
                    untested_n += 1
        run.total_flags = len(flags)
        run.stale_flags = stale_n
        run.untested_paths = untested_n
        run.removal_candidates = stale_n + candidates_n
        run.status = "COMPLETED"
    except Exception as exc:  # never leave a ghost RUNNING run
        run.status = "FAILED"
        run.error_message = str(exc)[:2000]
    run.completed_at = utcnow_iso()
    run.duration_ms = int((time.time() - started) * 1000)
    db.commit()
    db.refresh(run)
    return run_out(run)


@router.get("/api/risk-assessments", response_model=list[RiskAssessmentOut],
             summary="List risk assessments, newest first")
def list_risk_assessments(db: Session = Depends(get_db)):
    rows = (db.query(RiskAssessment).order_by(RiskAssessment.assessed_at.desc())
            .limit(200).all())
    return [risk_out(a) for a in rows]


@router.get("/api/detection-results", response_model=list[DetectionResultOut])
def list_detections(analysis_run_id: str | None = None, feature_flag_id: str | None = None,
                    db: Session = Depends(get_db)):
    q = db.query(DetectionResult)
    if analysis_run_id:
        q = q.filter_by(analysis_run_id=analysis_run_id)
    if feature_flag_id:
        q = q.filter_by(feature_flag_id=feature_flag_id)
    return [detection_out(d) for d in q.order_by(DetectionResult.detected_at.desc()).limit(200).all()]


@router.get("/api/untested-paths", response_model=list[UntestedPathOut])
def list_untested(analysis_run_id: str | None = None, db: Session = Depends(get_db)):
    q = db.query(UntestedPath)
    if analysis_run_id:
        q = q.filter_by(analysis_run_id=analysis_run_id)
    return [untested_out(u) for u in q.order_by(UntestedPath.detected_at.desc()).limit(200).all()]


# ---------------------------------------------------------------------- risk
def _recommendation(level: str, factors: list[dict], tests_ok: bool | None) -> str:
    if tests_ok is False:
        return "DO_NOT_REMOVE"
    if level in ("HIGH", "CRITICAL"):
        return "DO_NOT_REMOVE" if level == "CRITICAL" else "REVIEW_REQUIRED"
    if any(f.get("factor") in ("UNTESTED_BRANCH", "COVERAGE_UNKNOWN", "NO_TEST_SIGNAL") for f in factors):
        return "REVIEW_REQUIRED"
    return "SAFE_TO_REMOVE"


@router.post("/api/risk-assessments", response_model=RiskAssessmentOut, status_code=201,
             summary="Create a persisted, explainable risk assessment for a flag")
def create_risk_assessment(body: RiskAssessmentCreate, db: Session = Depends(get_db)):
    f = _flag_or_404(db, body.flag_id)
    repo = db.get(Repository, f.repository_id) if f.repository_id else None
    git_info = {}
    if repo and repo.local_path and Path(repo.local_path).exists():
        git_info = git_service.collect_git_evidence(Path(repo.local_path))
    ev_rows = db.query(EvidenceRecord).filter_by(flag_id=f.id).all()
    ev_dicts = [{"evidence_type": e.evidence_type, "payload": e.payload or {}} for e in ev_rows]
    path_rows = db.query(CodePath).filter_by(flag_id=f.id).all()
    path_dicts = [{"coverage_status": p.coverage_status} for p in path_rows]
    res = risk_service.assess_risk(
        {"days_inactive": f.days_inactive, "rollout_percentage": f.rollout_percentage},
        ev_dicts, path_dicts, git_info)
    tests_ok: bool | None = None
    last_run = (db.query(TestRun).filter(TestRun.repository_id == f.repository_id)
                .order_by(TestRun.created_at.desc()).first())
    if last_run:
        tests_ok = bool(last_run.success)
    rec = _recommendation(res["risk_level"], res["factors"], tests_ok)
    a = RiskAssessment(id=new_id("risk"), flag_id=f.id, flag_name=f.key,
           overall_risk=res["overall_risk"], blast_radius_score=res["blast_radius_score"],
           recommendations=res["recommendations"], assessed_at=utcnow_iso(),
           estimated_cleanup_hours=res["estimated_cleanup_hours"], score=res["score"])
    a.risk_level = res["risk_level"]  # type: ignore[attr-defined]
    a.affected_code_paths = [p.file_path for p in path_rows][:20]  # type: ignore[attr-defined]
    a.affected_environments = [f.environment]  # type: ignore[attr-defined]
    a.dependency_count = len(path_rows)  # type: ignore[attr-defined]
    a.test_coverage = "unavailable" if any(p.coverage_status == "unavailable" for p in path_rows) else "partial"  # type: ignore[attr-defined]
    a.rollback_available = 1 if (repo and repo.local_path) else 0  # type: ignore[attr-defined]
    a.recommendation = rec  # type: ignore[attr-defined]
    db.add(a)
    db.flush()
    for fac in res["factors"]:
        db.add(RiskFactor(id=new_id("rf"), assessment_id=a.id, category=fac.get("category", ""),
                          description=fac.get("description", ""), score=fac.get("score", 0),
                          level=fac.get("impact", "MEDIUM").lower()))
    f.risk = res["overall_risk"]
    audit_service.log(db, "RISK_ASSESSED", entity_type="risk_assessment", entity_id=a.id,
                      project_id=getattr(f, "project_id", None), feature_flag_id=f.id,
                      new_value=f"{res['risk_level']}/{rec}")
    db.commit()
    db.refresh(a)
    out = risk_out(a)
    return out


# ------------------------------------------------------------------- removal
def _expected_changes(db: Session, flag: FeatureFlag) -> tuple[list[str], int]:
    paths = db.query(CodePath).filter_by(flag_id=flag.id).all()
    refs = db.query(CodeReference).filter_by(flag_id=flag.id).all()
    files = sorted({(p.file_path or "") for p in paths} | {(r.file_path or "") for r in refs} - {""})
    lines = sum(len(p.dead_code_lines or []) or max(1, len((p.dead_code_snippet or "").splitlines()))
                for p in paths) or len(refs) * 3
    return files, lines


@router.post("/api/removals/dry-run", summary="Plan a removal without touching the repository")
def dry_run(body: DryRunIn, db: Session = Depends(get_db)):
    f = _flag_or_404(db, body.flag_id)
    files, lines = _expected_changes(db, f)
    real_files: list[str] | None = None
    real_rules: list[str] = []
    real_engine = ""
    # Real Piranha dry-run when a checkout, tool, and verified language exist.
    # Piranha dry_run=True never writes; purity is verified afterwards.
    repo = db.get(Repository, f.repository_id) if f.repository_id else None
    if repo and repo.local_path and Path(repo.local_path).exists():
        lang = piranha_service.repo_language_to_piranha(repo.language)
        st = piranha_service.piranha_status()
        if lang and st["available"]:
            try:
                cfg = piranha_service.build_config(
                    lang, f.key, body.permanent_value or "false", dry_run=True)
                res = piranha_service.run_cleanup(Path(repo.local_path), cfg)
                real_files = res.files_changed
                real_rules = sorted({str(r.get("rule", "")) for r in res.rewrites})
                real_engine = f"polyglot-piranha {st['version']}"
                if not git_service.tracked_clean(Path(repo.local_path)):
                    raise CleanupFlowError("DRY_RUN_DIRTY",
                                           "dry-run found uncommitted tracked changes; refusing plan")
            except CleanupFlowError as exc:
                raise HTTPException(status_code=500, detail=str(exc))
            except piranha_service.PiranhaError as exc:
                raise HTTPException(status_code=500, detail=str(exc))
    if real_files is not None:
        files = sorted(set(real_files))
        diff_text = (f"DRY RUN (no changes made, worktree verified clean): "
                     f"{real_engine} would rewrite {len(files)} file(s), "
                     f"keep permanent value {body.permanent_value}. "
                     f"Rules: {', '.join(real_rules) or 'none'}.")
        lines_out, added_out = lines, 0
    else:
        diff_text = (f"DRY RUN (no changes made): would rewrite {len(files)} file(s), "
                     f"remove ~{lines} line(s), keep permanent value {body.permanent_value}. "
                     f"(estimate from recorded references; no Piranha execution)")
        lines_out, added_out = lines, 1
    op = RemovalOperation(id=new_id("op"), flag_id=f.id, flag_name=f.key,
                          repository_id=f.repository_id, repository_name=f.repository_name,
                          target_branch=body.target_branch, status="SUCCESS", tool_target="Piranha",
                          files_affected=len(files), lines_removed=lines_out, lines_added=added_out,
                          executed_by="local-user", diff_summary=diff_text)
    op.operation_type = "DRY_RUN"  # type: ignore[attr-defined]
    op.cleanup_status = "DRY_RUN"  # type: ignore[attr-defined]
    op.started_at = utcnow_iso()  # type: ignore[attr-defined]
    op.completed_at = utcnow_iso()
    op.verification_status = "UNVERIFIED"
    db.add(op)
    audit_service.log(db, "CLEANUP_DRY_RUN", entity_type="removal_operation", entity_id=op.id,
                      project_id=getattr(f, "project_id", None), feature_flag_id=f.id,
                      new_value="DRY_RUN", metadata={"files": files, "engine": real_engine})
    db.commit()
    db.refresh(op)
    out = removal_out(op)
    return {**out.model_dump(by_alias=True), "plannedFiles": files}


@router.post("/api/removals", response_model=RemovalOut, status_code=201,
             summary="Approved removal: safety branch + Piranha + tests + verification + audit")
def approved_removal(body: RemovalCreate2, confirmed_high_risk: bool = Query(default=False),
                     db: Session = Depends(get_db)):
    f = _flag_or_404(db, body.flag_id)
    latest = (db.query(RiskAssessment).filter_by(flag_id=f.id)
              .order_by(RiskAssessment.assessed_at.desc()).first())
    if not latest:
        raise HTTPException(status_code=422, detail="no risk assessment for this flag; POST /api/risk-assessments first")
    rec = (getattr(latest, "recommendation", "") or "").upper()
    lvl = (getattr(latest, "risk_level", "") or latest.overall_risk or "").upper()
    if rec == "DO_NOT_REMOVE":
        raise HTTPException(status_code=422, detail="risk assessment says DO_NOT_REMOVE; removal refused")
    if lvl in ("HIGH", "CRITICAL") and not confirmed_high_risk:
        raise HTTPException(status_code=422,
                            detail=f"flag risk is {lvl}; re-submit with ?confirmed_high_risk=true after review")
    state = lifecycle_service.current_state(f)
    try:
        if state == "RISK_REVIEW":
            lifecycle_service.transition(db, f, "REMOVAL_PENDING", action="REMOVAL_STARTED")
        elif state != "REMOVAL_PENDING":
            raise LifecycleError(f"flag must be in REMOVAL_PENDING (now {state}) before removal")
    except LifecycleError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    repo = db.get(Repository, f.repository_id)
    try:
        op = run_governed_cleanup(
            db, f, repo, permanent_value=(body.permanent_value or "false"),
            executed_by=body.executed_by or "local-user",
            tool_target=body.tool_target or "Piranha",
            analysis_run_id=body.analysis_run_id, manage_lifecycle=True)
    except CleanupFlowError as exc:
        raise HTTPException(status_code=exc.http_status, detail=str(exc))
    return removal_out(op)


@router.post("/api/removals/{removal_id}/rollback", summary="Restore the pre-removal safety branch")
def rollback_removal(removal_id: str, db: Session = Depends(get_db)):
    op = db.get(RemovalOperation, removal_id)
    if not op:
        raise HTTPException(status_code=404, detail="removal not found")
    if not op.safety_branch:
        raise HTTPException(status_code=422, detail="no safety branch recorded; rollback unavailable")
    f = db.get(FeatureFlag, op.flag_id)
    repo = db.get(Repository, op.repository_id) if op else None
    if not repo or not repo.local_path or not Path(repo.local_path).exists():
        raise HTTPException(status_code=400, detail="repository checkout UNAVAILABLE")
    from ..config import get_settings
    from ..utils.subprocess_util import run_cmd
    rp = Path(repo.local_path)
    r = run_cmd([get_settings().GIT_BIN, "checkout", op.safety_branch],
                cwd=str(rp), timeout=60)
    if r.returncode != 0:
        raise HTTPException(status_code=500, detail=f"rollback checkout failed: {(r.stderr or r.stdout)[-1000:]}")
    # If a valid base commit was recorded, hard-restore the worktree to it so
    # uncommitted cleanup changes are genuinely reverted (checkout alone keeps
    # them when already on the safety branch). Invalid bases keep the legacy
    # checkout-only behavior.
    restored = f"checked out {op.safety_branch}"
    if op.base_commit and op.base_commit not in ("", "UNAVAILABLE"):
        verify = run_cmd([get_settings().GIT_BIN, "rev-parse", "--verify",
                          op.base_commit], cwd=str(rp), timeout=15)
        if verify.returncode == 0:
            rst = piranha_service.restore_workspace(rp, op.base_commit)
            if not rst["ok"]:
                raise HTTPException(status_code=500,
                                    detail=f"rollback restore failed: {rst['error']}")
            restored = f"restored {op.safety_branch} to {op.base_commit[:12]}"
    rb = RemovalOperation(id=new_id("op"), flag_id=op.flag_id, flag_name=op.flag_name,
                          repository_id=op.repository_id, repository_name=op.repository_name,
                          target_branch=op.target_branch, status="ROLLED_BACK",
                          tool_target="git", executed_by="local-user",
                          diff_summary=f"Rolled back: {restored}.")
    rb.operation_type = "ROLLBACK"  # type: ignore[attr-defined]
    rb.started_at = utcnow_iso()  # type: ignore[attr-defined]
    rb.completed_at = utcnow_iso()
    rb.safety_branch = op.safety_branch
    rb.base_commit = op.base_commit
    db.add(rb)
    op.status = "ROLLED_BACK"
    if f:
        try:
            lifecycle_service.transition(db, f, "RISK_REVIEW", action="ROLLBACK_COMPLETED",
                                         metadata={"operation_id": op.id})
        except LifecycleError:
            pass
        audit_service.log(db, "ROLLBACK_COMPLETED", entity_type="removal_operation",
                          entity_id=rb.id, feature_flag_id=op.flag_id,
                          new_value=f"restored {op.safety_branch}")
    db.commit()
    return {"rollback_operation_id": rb.id, "restored_branch": op.safety_branch}


# ---------------------------------------------------------------- evidence/audit
@router.get("/api/evidence", response_model=list[EvidenceOut2])
def list_evidence(project_id: str | None = None, feature_flag_id: str | None = None,
                  analysis_run_id: str | None = None, db: Session = Depends(get_db)):
    q = db.query(EvidenceRecord)
    if feature_flag_id:
        f = db.get(FeatureFlag, feature_flag_id) or db.query(FeatureFlag).filter_by(key=feature_flag_id).first()
        q = q.filter_by(flag_id=f.id if f else feature_flag_id)
    if analysis_run_id:
        q = q.filter_by(analysis_run_id=analysis_run_id)
    if project_id:
        q = q.filter_by(project_id=project_id)
    return [evidence2_out(e) for e in q.order_by(EvidenceRecord.detected_at.desc()).limit(200).all()]


@router.get("/api/audit-logs", response_model=list[AuditLogOut])
def list_audit(project_id: str | None = None, feature_flag_id: str | None = None,
               action: str | None = None, db: Session = Depends(get_db)):
    q = db.query(AuditLog)
    if project_id:
        q = q.filter_by(project_id=project_id)
    if feature_flag_id:
        q = q.filter_by(feature_flag_id=feature_flag_id)
    if action:
        q = q.filter_by(action=action)
    return [audit_out(a) for a in q.order_by(AuditLog.timestamp.desc()).limit(200).all()]
