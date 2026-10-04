"""POST /api/scans runs the real workflow: git probe -> FlagShark -> persist."""
from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..config import get_settings
from ..database import get_db
from ..models.models import CodePath, CodeReference, EvidenceRecord, FeatureFlag, Repository, Scan, ScanFinding
from ..schemas.schemas import ScanCreate, ScanOut
from ..services import evidence_service, flagshark_service, git_service
from ..services.codepath_service import analyze_flag_codepaths
from ..utils.helpers import new_id, utcnow_iso
from .mappers import scan_out

router = APIRouter(tags=["scans"])
settings = get_settings()


def _upsert_flag(db: Session, repo: Repository, key: str, finding: dict) -> FeatureFlag:
    f = db.query(FeatureFlag).filter_by(key=key, repository_id=repo.id).first()
    if f:
        f.last_modified = utcnow_iso()
        return f
    f = FeatureFlag(id=new_id("flag"), name=key, key=key,
                    description=f"Detected by scan in {repo.name}.",
                    repository_id=repo.id, repository_name=repo.name,
                    status="active", risk="medium", flag_type="release",
                    created_at_flag=utcnow_iso(), last_modified=utcnow_iso(),
                    evaluations_count=0, evaluations_last_7d=0, days_inactive=0,
                    rollout_percentage=0, environment="production",
                    tags=[], default_value="false")
    db.add(f)
    return f


@router.post("/api/scans", response_model=ScanOut, status_code=201, summary="Run detection on a repository")
def create_scan(body: ScanCreate, db: Session = Depends(get_db)):
    repo = db.get(Repository, body.repository_id)
    if not repo:
        raise HTTPException(status_code=404, detail="repository not found")
    if not repo.local_path:
        raise HTTPException(status_code=400, detail="repository has no local_path; register it with a local checkout path first")
    path = Path(repo.local_path)
    if not path.exists():
        raise HTTPException(status_code=400, detail=f"repository path missing: {path}")

    git_info = git_service.collect_git_evidence(path)
    if not git_info.get("available"):
        # still allow scan on non-git dirs, but record the fact
        branch, commit = body.branch or repo.default_branch, ""
    else:
        branch = body.branch or git_info.get("branch", "") or repo.default_branch
        commit = git_info.get("commit", "")

    repo.scan_status = "scanning"
    db.commit()

    det = flagshark_service.run_detection(path)
    now = utcnow_iso()
    scan = Scan(id=new_id("scan"), repository_id=repo.id, repository_name=repo.name,
                timestamp=now, status="success" if det["findings"] else ("failed" if det["error"] and "not installed" in det["error"] and not det["findings"] else "partial"),
                total_flags_detected=len({f["flag_key"] for f in det["findings"]}),
                stale_flags_detected=sum(1 for f in det["findings"] if f.get("is_stale")),
                scanner_engine=det["engine"], scan_duration_ms=det["duration_ms"],
                commit_hash=(commit or "")[:64], branch=branch,
                raw_output=(det["raw"] or "")[:20000], error_message=(det["error"] or "")[:4000])
    # FlagShark-missing with zero local refs => explicit failure, no fake flags
    if not det["tool_available"] and not det["findings"]:
        scan.status = "failed"
    db.add(scan)
    db.flush()

    seen: dict[str, list[dict]] = {}
    for fd in det["findings"]:
        db.add(ScanFinding(id=new_id("find"), scan_id=scan.id, flag_key=fd["flag_key"],
                           file_path=fd.get("file_path", ""), line_number=int(fd.get("line_number", 0) or 0),
                           ast_node_type=fd.get("ast_node_type", ""), is_stale=1 if fd.get("is_stale") else 0,
                           confidence=float(fd.get("confidence", 0.0) or 0.0), reason=fd.get("reason", "")))
        seen.setdefault(fd["flag_key"], []).append(fd)

    for key, refs in seen.items():
        flag = _upsert_flag(db, repo, key, refs[0])
        db.flush()
        _, paths = analyze_flag_codepaths(path, key, refs)
        for i, r in enumerate(refs[:25]):
            snippet = ""
            try:
                fp = path / r.get("file_path", "")
                lines = fp.read_text(encoding="utf-8", errors="ignore").splitlines()
                ln = int(r.get("line_number", 0) or 0)
                if 1 <= ln <= len(lines):
                    snippet = "\n".join(lines[max(0, ln - 4):min(len(lines), ln + 8)])[:3000]
            except Exception:
                snippet = ""
            db.add(CodeReference(id=new_id("ref"), flag_id=flag.id, flag_name=key,
                                 repository_id=repo.id, repository_name=repo.name,
                                 file_path=r.get("file_path", ""), line_number=int(r.get("line_number", 0) or 0),
                                 column_number=0, code_snippet=snippet, reference_type="check",
                                 is_enclosing_control_flow=1, ast_node_type=r.get("ast_node_type", "")))
        for p in paths[:25]:
            db.add(CodePath(id=new_id("path"), flag_id=flag.id, file_path=p["file_path"],
                            branch_condition=p["branch_condition"], reachable_state=1,
                            dead_code_lines=[], dead_code_snippet=p.get("dead_code_snippet", ""),
                            complexity_reduction_score=p.get("complexity_reduction_score", 1),
                            true_branch=p.get("true_branch", "")[:3000],
                            false_branch=p.get("false_branch", "")[:3000],
                            functions_involved=p.get("functions_involved", [])[:5],
                            coverage_status="unavailable"))
        for ev in evidence_service.build_evidence(path, key, None, git_info, refs, {"engine": det["engine"]}):
            db.add(EvidenceRecord(id=new_id("evi"), flag_id=flag.id, flag_name=key,
                                  repository_name=repo.name, evidence_type=ev["evidence_type"],
                                  confidence_score=ev["confidence_score"], detected_at=now,
                                  source=ev["source"], summary=ev["summary"],
                                  severity=ev.get("severity", ""), value=str(ev.get("value", ""))[:2000],
                                  payload=ev.get("payload", {})))

    # repo counters from real data
    keys = list(seen.keys())
    repo.total_flags = db.query(FeatureFlag).filter_by(repository_id=repo.id).count()
    repo.last_scanned_at = now
    repo.scan_status = "completed" if scan.status != "failed" else "failed"
    try:
        repo.lines_of_code = sum(1 for _ in list(path.rglob("*.py"))[:1])  # cheap probe; real LOC via cloc unavailable
    except Exception:
        pass
    db.commit()
    db.refresh(scan)
    findings = db.query(ScanFinding).filter_by(scan_id=scan.id).all()
    out = scan_out(scan, findings)
    if scan.status == "failed":
        # 201 with failed status + clear message; frontend shows error state
        out.status = "failed"
    return out


@router.get("/api/scans", response_model=list[ScanOut], summary="List scans")
def list_scans(db: Session = Depends(get_db)):
    scans = db.query(Scan).order_by(Scan.created_at.desc()).limit(100).all()
    return [scan_out(s) for s in scans]


@router.get("/api/scans/{scan_id}", response_model=ScanOut, summary="Get scan + findings")
def get_scan(scan_id: str, db: Session = Depends(get_db)):
    s = db.get(Scan, scan_id)
    if not s:
        raise HTTPException(status_code=404, detail="scan not found")
    from ..models.models import ScanFinding as SF
    findings = db.query(SF).filter_by(scan_id=scan_id).all()
    return scan_out(s, findings)
