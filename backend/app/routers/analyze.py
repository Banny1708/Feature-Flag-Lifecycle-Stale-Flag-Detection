"""Evidence / code-paths / risk + explicit re-analyze for a flag."""
from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models.models import CodePath, CodeReference, EvidenceRecord, FeatureFlag, Repository, RiskAssessment, RiskFactor
from ..schemas.schemas import CodePathOut, CodeReferenceOut, EvidenceOut, RiskAssessmentOut
from ..services import evidence_service, git_service, risk_service
from ..services.codepath_service import analyze_flag_codepaths, apply_jacoco_to_paths
from ..services.test_service import find_jacoco_xml
from ..utils.helpers import new_id, utcnow_iso
from .mappers import evidence_out, path_out, ref_out, risk_out

router = APIRouter(tags=["analysis"])


def _flag_or_404(db: Session, flag_id: str) -> FeatureFlag:
    f = db.get(FeatureFlag, flag_id) or db.query(FeatureFlag).filter_by(key=flag_id).first()
    if not f:
        raise HTTPException(status_code=404, detail="flag not found")
    return f


@router.get("/api/flags/{flag_id}/evidence", response_model=list[EvidenceOut])
def flag_evidence(flag_id: str, db: Session = Depends(get_db)):
    f = _flag_or_404(db, flag_id)
    rows = db.query(EvidenceRecord).filter_by(flag_id=f.id).order_by(EvidenceRecord.detected_at.desc()).all()
    return [evidence_out(e) for e in rows]


@router.get("/api/flags/{flag_id}/code-paths", response_model=list[CodePathOut])
def flag_code_paths(flag_id: str, db: Session = Depends(get_db)):
    f = _flag_or_404(db, flag_id)
    rows = db.query(CodePath).filter_by(flag_id=f.id).all()
    return [path_out(p) for p in rows]


@router.get("/api/flags/{flag_id}/references", response_model=list[CodeReferenceOut])
def flag_references(flag_id: str, db: Session = Depends(get_db)):
    f = _flag_or_404(db, flag_id)
    rows = db.query(CodeReference).filter_by(flag_id=f.id).all()
    return [ref_out(r) for r in rows]


@router.get("/api/flags/{flag_id}/risk", response_model=RiskAssessmentOut)
def flag_risk(flag_id: str, db: Session = Depends(get_db)):
    f = _flag_or_404(db, flag_id)
    a = db.query(RiskAssessment).filter_by(flag_id=f.id).order_by(RiskAssessment.assessed_at.desc()).first()
    if not a:
        raise HTTPException(status_code=404, detail="no risk assessment yet; POST /api/flags/{id}/analyze first")
    db.refresh(a)
    return risk_out(a)


@router.post("/api/flags/{flag_id}/analyze", summary="Re-collect git+code evidence and recompute risk")
def analyze_flag(flag_id: str, db: Session = Depends(get_db)):
    f = _flag_or_404(db, flag_id)
    repo = db.get(Repository, f.repository_id)
    git_info: dict = {}
    refs_payload: list[dict] = []
    if repo and repo.local_path and Path(repo.local_path).exists():
        rp = Path(repo.local_path)
        git_info = git_service.collect_git_evidence(rp)
        existing = db.query(CodeReference).filter_by(flag_id=f.id).all()
        refs_payload = [{"file_path": r.file_path, "line_number": r.line_number,
                         "ast_node_type": r.ast_node_type} for r in existing]
        _, paths = analyze_flag_codepaths(rp, f.key, refs_payload or
                                          [{"file_path": r.file_path, "line_number": r.line_number} for r in existing])
        jac = find_jacoco_xml(rp)
        if jac:
            apply_jacoco_to_paths(jac, paths)
        # refresh stored code paths
        db.query(CodePath).filter_by(flag_id=f.id).delete()
        for p in paths:
            db.add(CodePath(id=new_id("path"), flag_id=f.id, file_path=p["file_path"],
                            branch_condition=p["branch_condition"], reachable_state=1,
                            dead_code_lines=p.get("dead_code_lines", []),
                            dead_code_snippet=p.get("dead_code_snippet", ""),
                            complexity_reduction_score=p.get("complexity_reduction_score", 1),
                            true_branch=p.get("true_branch", "")[:3000],
                            false_branch=p.get("false_branch", "")[:3000],
                            functions_involved=p.get("functions_involved", [])[:5],
                            coverage_status=p.get("coverage_status", "unavailable")))
        hist = git_service.flag_git_history(rp, f.key)
        evidence_rows = evidence_service.build_evidence(
            rp, f.key, f, git_info,
            [{"file_path": r.file_path} for r in existing],
            {"engine": "re-analysis"})
        db.query(EvidenceRecord).filter_by(flag_id=f.id).delete()
        for ev in evidence_rows:
            db.add(EvidenceRecord(id=new_id("evi"), flag_id=f.id, flag_name=f.key,
                                  repository_name=f.repository_name, evidence_type=ev["evidence_type"],
                                  confidence_score=ev["confidence_score"], detected_at=utcnow_iso(),
                                  source=ev["source"], summary=ev["summary"],
                                  severity=ev.get("severity", ""), value=str(ev.get("value", ""))[:2000],
                                  payload=ev.get("payload", {})))
    else:
        git_info = {"available": False, "reason": "repository local_path UNAVAILABLE"}

    flag_dict = {"days_inactive": f.days_inactive, "rollout_percentage": f.rollout_percentage}
    ev_rows = db.query(EvidenceRecord).filter_by(flag_id=f.id).all()
    ev_dicts = [{"evidence_type": e.evidence_type, "payload": e.payload or {}} for e in ev_rows]
    path_rows = db.query(CodePath).filter_by(flag_id=f.id).all()
    path_dicts = [{"coverage_status": p.coverage_status} for p in path_rows]
    res = risk_service.assess_risk(flag_dict, ev_dicts, path_dicts, git_info)
    old = db.query(RiskAssessment).filter_by(flag_id=f.id).all()
    for o in old:
        db.query(RiskFactor).filter_by(assessment_id=o.id).delete()
        db.delete(o)
    a = RiskAssessment(id=new_id("risk"), flag_id=f.id, flag_name=f.key,
                       overall_risk=res["overall_risk"], blast_radius_score=res["blast_radius_score"],
                       recommendations=res["recommendations"], assessed_at=utcnow_iso(),
                       estimated_cleanup_hours=res["estimated_cleanup_hours"], score=res["score"])
    db.add(a)
    db.flush()
    for fac in res["factors"]:
        db.add(RiskFactor(id=new_id("rf"), assessment_id=a.id, category=fac.get("category", ""),
                          description=fac.get("description", ""), score=fac.get("score", 0),
                          level=fac.get("impact", "MEDIUM").lower()))
    # sync flag risk label
    f.risk = res["overall_risk"]
    db.commit()
    db.refresh(a)
    return risk_out(a)
