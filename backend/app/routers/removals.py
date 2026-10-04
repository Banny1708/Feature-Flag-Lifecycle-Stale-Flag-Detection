"""Removal workflow: safety branch -> Piranha -> tests -> verification. Explicit user confirm only."""
from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models.models import FeatureFlag, RemovalOperation, Repository, TestRun, VerificationResult
from ..schemas.schemas import RemovalCreate, RemovalOut, TestRunOut, VerificationOut
from ..services import git_service, piranha_service, test_service
from ..services.codepath_service import apply_jacoco_to_paths
from ..utils.helpers import new_id, utcnow_iso
from .mappers import removal_out, testrun_out, verification_out

router = APIRouter(tags=["removals"])

TERMINAL_STATUSES = ("SUCCESS", "FAILED", "UNVERIFIED")


@router.post("/api/flags/{flag_id}/remove", response_model=RemovalOut, status_code=201,
             summary="User-confirmed removal: safety branch + Piranha + tests + verification")
def remove_flag(flag_id: str, body: RemovalCreate, db: Session = Depends(get_db)):
    f = db.get(FeatureFlag, body.flag_id) or db.query(FeatureFlag).filter_by(key=body.flag_id).first()
    if not f:
        raise HTTPException(status_code=404, detail="flag not found")
    if flag_id not in (f.id, f.key):
        raise HTTPException(status_code=400, detail="flag_id mismatch")
    repo = db.get(Repository, f.repository_id)
    if not repo or not repo.local_path or not Path(repo.local_path).exists():
        raise HTTPException(status_code=400, detail="repository local checkout UNAVAILABLE; cannot remove safely")
    rp = Path(repo.local_path)

    avail, _ = git_service.git_available()
    if not avail:
        raise HTTPException(status_code=500, detail="git is not installed; removal requires git safety branch (UNAVAILABLE)")
    if not git_service.is_git_repo(rp):
        raise HTTPException(status_code=400, detail="repository path is not a git repo")

    op = RemovalOperation(id=new_id("op"), flag_id=f.id, flag_name=f.key,
                          repository_id=repo.id, repository_name=repo.name,
                          target_branch=body.target_branch or repo.default_branch,
                          status="in-review", tool_target=body.tool_target or "Piranha",
                          executed_by=body.executed_by or "local-user")
    db.add(op)
    db.flush()

    # 1. safety point
    safety = piranha_service.create_safety_branch(rp, f.key)
    if not safety["ok"]:
        op.status = "failed"
        op.verification_status = "FAILED"
        op.stderr_log = safety["error"]
        db.commit()
        raise HTTPException(status_code=500, detail=f"safety branch creation failed: {safety['error']}")
    op.safety_branch = safety["branch"]
    op.base_commit = safety["base_commit"]

    # 2. Piranha
    pir = piranha_service.run_piranha(rp, f.key, (body.permanent_value or "false").lower())
    op.stdout_log = pir.get("stdout", "")
    op.stderr_log = pir.get("stderr", "")
    op.files_affected = len(pir.get("changed_files", []))
    op.lines_added = pir.get("lines_added", 0)
    op.lines_removed = pir.get("lines_removed", 0)
    op.diff_summary = (pir.get("diff_stat", "") or "")[:2000]
    if not pir.get("available"):
        op.status = "failed"; op.verification_status = "FAILED"
        db.commit()
        raise HTTPException(status_code=500, detail=pir.get("error", "Piranha UNAVAILABLE"))
    if not pir.get("ok"):
        op.status = "failed"; op.verification_status = "FAILED"
        op.completed_at = utcnow_iso()
        db.commit()
        raise HTTPException(status_code=500, detail=f"Piranha failed: {pir.get('error', '')[:1000]}")

    # 3. tests (+ JaCoCo where present)
    tres = test_service.run_tests(rp)
    tr = TestRun(id=new_id("test"), operation_id=op.id, repository_id=repo.id,
                 command=tres.get("command", ""), status=tres.get("status", "failed"),
                 success=1 if tres.get("success") else 0, test_count=tres.get("test_count", 0),
                 failed_tests=tres.get("failed", []), output=tres.get("output", "")[:20000])
    jac = test_service.find_jacoco_xml(rp)
    if jac:
        summ = test_service.parse_jacoco_summary(jac)
        tr.branch_coverage = summ.get("branch_coverage", "unavailable")
        tr.line_coverage = summ.get("line_coverage", "unavailable")
    db.add(tr)
    db.flush()

    # 4. verification: flag refs gone? tests green?
    remaining = 0
    try:
        for p in rp.rglob("*"):
            if not p.is_file() or ".git" in p.parts or p.stat().st_size > 1_000_000:
                continue
            try:
                if f.key in p.read_text(encoding="utf-8", errors="ignore"):
                    remaining += 1
                    if remaining > 20:
                        break
            except Exception:
                continue
    except Exception:
        remaining = -1  # unknown
    dead_elim = 1 if remaining == 0 else 0
    syntax_ok = 1 if tres.get("success") else 0
    regression = 0 if tres.get("success") else 1
    if remaining == 0 and tres.get("success"):
        verdict = "SUCCESS"; op.status = "merged"; op.verification_status = "SUCCESS"
        f.status = "removed"
    elif not tres.get("success"):
        verdict = "FAILED"; op.status = "failed"; op.verification_status = "FAILED"
    else:
        verdict = "UNVERIFIED"; op.status = "prepared"; op.verification_status = "UNVERIFIED"
    op.completed_at = utcnow_iso()
    ver = VerificationResult(id=new_id("verif"), operation_id=op.id, flag_id=f.id, flag_name=f.key,
                             repository_name=repo.name,
                             test_suite_status=tres.get("status", "failed"),
                             build_status="passed" if tres.get("success") else "failed",
                             ast_validation_status="passed" if dead_elim else "failed",
                             dead_code_eliminated=dead_elim, syntax_valid=syntax_ok,
                             regression_detected=regression, unresolved_references=max(0, remaining),
                             verified_at=utcnow_iso(),
                             summary=f"Removal {verdict}: Piranha changed {op.files_affected} file(s); "
                                     f"{remaining} file(s) still reference {f.key}; tests {tres.get('status')}. "
                                     f"Safety branch {op.safety_branch} preserved.",
                             test_output_summary=(tres.get("output", "")[:2000]))
    db.add(ver)
    db.commit()
    db.refresh(op)
    return removal_out(op)


@router.get("/api/removals", response_model=list[RemovalOut])
def list_removals(db: Session = Depends(get_db)):
    return [removal_out(o) for o in db.query(RemovalOperation).order_by(RemovalOperation.created_at.desc()).limit(100).all()]


@router.get("/api/removals/{removal_id}", response_model=RemovalOut)
def get_removal(removal_id: str, db: Session = Depends(get_db)):
    o = db.get(RemovalOperation, removal_id)
    if not o:
        raise HTTPException(status_code=404, detail="removal not found")
    return removal_out(o)


@router.get("/api/removals/{removal_id}/verification", response_model=VerificationOut)
def removal_verification(removal_id: str, db: Session = Depends(get_db)):
    v = db.query(VerificationResult).filter_by(operation_id=removal_id).first()
    if not v:
        raise HTTPException(status_code=404, detail="verification not found")
    return verification_out(v)


@router.get("/api/test-runs/{test_run_id}", response_model=TestRunOut)
def get_test_run(test_run_id: str, db: Session = Depends(get_db)):
    t = db.get(TestRun, test_run_id)
    if not t:
        raise HTTPException(status_code=404, detail="test run not found")
    return testrun_out(t)


@router.get("/api/verifications", response_model=list[VerificationOut], summary="All verification results")
def list_verifications(db: Session = Depends(get_db)):
    return [verification_out(v) for v in db.query(VerificationResult).order_by(VerificationResult.created_at.desc()).limit(100).all()]
