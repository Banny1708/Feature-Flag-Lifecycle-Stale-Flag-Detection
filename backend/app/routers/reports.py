from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session
import json

from ..database import get_db
from ..models.models import FeatureFlag, RemovalOperation, Report, Scan
from ..schemas.schemas import ReportCreate, ReportOut
from ..utils.helpers import new_id, utcnow_iso
from .mappers import report_out

router = APIRouter(tags=["reports"])


def _summarize(db: Session, repository_id: str | None) -> dict:
    fq = db.query(FeatureFlag)
    sq = db.query(Scan)
    if repository_id:
        fq = fq.filter_by(repository_id=repository_id)
        sq = sq.filter_by(repository_id=repository_id)
    flags = fq.all()
    scans = sq.all()
    removals = db.query(RemovalOperation)
    if repository_id:
        removals = removals.filter_by(repository_id=repository_id)
    removals = removals.all()
    stale = sum(1 for f in flags if f.status in ("stale", "potentially-stale"))
    done = sum(1 for r in removals if r.status == "merged")
    lines = sum(r.lines_removed for r in removals)
    return {"total_scanned_flags": len(flags) or sum(s.total_flags_detected for s in scans),
            "stale_flags_identified": stale,
            "removal_operations_completed": done,
            "tech_debt_reduction_hours": done * 5,
            "code_lines_eliminated": lines}


@router.get("/api/reports", response_model=list[ReportOut])
def list_reports(db: Session = Depends(get_db)):
    return [report_out(r) for r in db.query(Report).order_by(Report.created_at.desc()).limit(100).all()]


@router.post("/api/reports", response_model=ReportOut, status_code=201)
def create_report(body: ReportCreate, db: Session = Depends(get_db)):
    s = _summarize(db, body.repository_id)
    repo_name = ""
    if body.repository_id:
        from ..models.models import Repository
        repo = db.get(Repository, body.repository_id)
        repo_name = repo.name if repo else ""
    r = Report(id=new_id("rep"), title=body.title, type=body.type, generated_at=utcnow_iso(),
               repository_id=body.repository_id or "", repository_name=repo_name,
               total_scanned_flags=s["total_scanned_flags"],
               stale_flags_identified=s["stale_flags_identified"],
               removal_operations_completed=s["removal_operations_completed"],
               tech_debt_reduction_hours=s["tech_debt_reduction_hours"],
               code_lines_eliminated=s["code_lines_eliminated"],
               download_format=body.download_format or "json", status="ready")
    db.add(r)
    db.commit()
    db.refresh(r)
    return report_out(r)


@router.get("/api/reports/{report_id}", response_model=ReportOut)
def get_report(report_id: str, db: Session = Depends(get_db)):
    r = db.get(Report, report_id)
    if not r:
        raise HTTPException(status_code=404, detail="report not found")
    return report_out(r)


@router.get("/api/reports/{report_id}/download")
def download_report(report_id: str, db: Session = Depends(get_db)):
    r = db.get(Report, report_id)
    if not r:
        raise HTTPException(status_code=404, detail="report not found")
    out = report_out(r)
    if (r.download_format or "json") == "csv":
        csv = ("title,type,total_scanned,stale,removals_completed,debt_hours,lines_eliminated\n"
               f'"{r.title}",{r.type},{r.total_scanned_flags},{r.stale_flags_identified},'
               f"{r.removal_operations_completed},{r.tech_debt_reduction_hours},{r.code_lines_eliminated}\n")
        return Response(content=csv, media_type="text/csv",
                        headers={"Content-Disposition": f"attachment; filename={r.id}.csv"})
    payload = json.dumps(out.model_dump(by_alias=True), indent=2)
    return Response(content=payload, media_type="application/json",
                    headers={"Content-Disposition": f"attachment; filename={r.id}.json"})
