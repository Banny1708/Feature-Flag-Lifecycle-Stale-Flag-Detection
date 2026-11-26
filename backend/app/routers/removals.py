"""Removal workflow: user-confirmed cleanup via the shared governed flow.

This legacy endpoint keeps its own preconditions (no risk/lifecycle guards;
use POST /api/removals for the governed path) but delegates execution to
services.cleanup_flow so both APIs run the same verified Piranha adapter,
safety branch, diff capture, verification, and rollback support.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models.models import (FeatureFlag, RemovalOperation, Repository,
                             TestRun, VerificationResult)
from ..schemas.schemas import RemovalCreate, RemovalOut, TestRunOut, VerificationOut
from ..services.cleanup_flow import CleanupFlowError, run_governed_cleanup
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
    try:
        op = run_governed_cleanup(
            db, f, repo, permanent_value=(body.permanent_value or "false"),
            executed_by=body.executed_by or "local-user",
            tool_target=body.tool_target or "Piranha",
            analysis_run_id=None, manage_lifecycle=False)
    except CleanupFlowError as exc:
        raise HTTPException(status_code=exc.http_status, detail=str(exc))
    if op.status == "SUCCESS":
        op.status = "merged"  # legacy contract (reports count "merged")
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
