from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models.lifecycle_models import AuditLog, FlagEvaluation, Project
from ..models.models import FeatureFlag, Repository
from ..schemas.lifecycle_schemas import (
    EvaluationIn,
    EvaluationOut,
    FlagCreate,
    FlagPatch,
    ProjectCreate,
    ProjectOut,
)
from ..schemas.schemas import FeatureFlagOut
from ..services import audit_service, lifecycle_service
from ..services.lifecycle_service import LifecycleError
from ..utils.helpers import new_id, utcnow_iso
from .lifecycle_mappers import eval_out, project_out
from .mappers import flag_out

router = APIRouter(tags=["projects"])

LEGACY_STATUS_TO_LIFECYCLE = {
    "active": "ACTIVE",
    "potentially-stale": "CONCLUDED",
    "stale": "STALE_CANDIDATE",
    "removal-pending": "REMOVAL_PENDING",
    "removed": "REMOVED",
}


@router.get("/api/projects", response_model=list[ProjectOut])
def list_projects(db: Session = Depends(get_db)):
    return [project_out(p) for p in db.query(Project).order_by(Project.name).all()]


@router.post("/api/projects", response_model=ProjectOut, status_code=201)
def create_project(body: ProjectCreate, db: Session = Depends(get_db)):
    p = Project(id=new_id("proj"), name=body.name, description=body.description,
                repository_url=body.repository_url, default_branch=body.default_branch)
    db.add(p)
    audit_service.log(db, "FLAG_CREATED", entity_type="project", entity_id=p.id,
                      project_id=p.id, new_value=body.name)
    db.commit()
    db.refresh(p)
    return project_out(p)


@router.get("/api/projects/{project_id}", response_model=ProjectOut)
def get_project(project_id: str, db: Session = Depends(get_db)):
    p = db.get(Project, project_id)
    if not p:
        raise HTTPException(status_code=404, detail="project not found")
    return project_out(p)


@router.get("/api/projects/{project_id}/flags", response_model=list[FeatureFlagOut])
def project_flags(project_id: str, db: Session = Depends(get_db)):
    if not db.get(Project, project_id):
        raise HTTPException(status_code=404, detail="project not found")
    return [flag_out(f) for f in db.query(FeatureFlag).filter_by(project_id=project_id).all()]


@router.post("/api/projects/{project_id}/flags", response_model=FeatureFlagOut, status_code=201)
def project_create_flag(project_id: str, body: FlagCreate, db: Session = Depends(get_db)):
    if not db.get(Project, project_id):
        raise HTTPException(status_code=404, detail="project not found")
    if db.query(FeatureFlag).filter_by(key=body.key, project_id=project_id).first():
        raise HTTPException(status_code=409, detail="flag key already exists in project")
    repo_id = (body.repository_id or "").strip() or None
    if repo_id and not db.get(Repository, repo_id):
        raise HTTPException(status_code=422, detail=f"repository '{repo_id}' not found")
    f = FeatureFlag(id=new_id("flag"), name=body.name, key=body.key,
                    description=body.description, repository_id=repo_id,
                    status="active", risk="medium", flag_type=body.flag_type,
                    owner=body.owner, created_at_flag=utcnow_iso(), last_modified=utcnow_iso(),
                    environment=body.environment, tags=[], default_value=body.current_value)
    f.project_id = project_id  # type: ignore[attr-defined]
    f.lifecycle_state = "ACTIVE"  # type: ignore[attr-defined]
    f.current_value = body.current_value  # type: ignore[attr-defined]
    f.rollout_start_date = body.rollout_start_date  # type: ignore[attr-defined]
    f.rollout_end_date = body.rollout_end_date  # type: ignore[attr-defined]
    f.expected_expiry_date = body.expected_expiry_date  # type: ignore[attr-defined]
    db.add(f)
    audit_service.log(db, "FLAG_CREATED", entity_type="feature_flag", entity_id=f.id,
                      project_id=project_id, feature_flag_id=f.id, new_value=body.key)
    db.commit()
    db.refresh(f)
    return flag_out(f)


def _flag_or_404(db: Session, flag_id: str) -> FeatureFlag:
    f = db.get(FeatureFlag, flag_id) or db.query(FeatureFlag).filter_by(key=flag_id).first()
    if not f:
        raise HTTPException(status_code=404, detail="flag not found")
    return f


@router.patch("/api/flags/{flag_id}", response_model=FeatureFlagOut,
              summary="Update flag; lifecycle_state transitions are validated")
def patch_flag(flag_id: str, body: FlagPatch, db: Session = Depends(get_db)):
    f = _flag_or_404(db, flag_id)
    try:
        if body.lifecycle_state:
            lifecycle_service.transition(db, f, body.lifecycle_state, action="FLAG_UPDATED")
        elif body.status:
            target = LEGACY_STATUS_TO_LIFECYCLE.get(body.status)
            if not target:
                raise HTTPException(status_code=422, detail=f"unknown status '{body.status}'")
            lifecycle_service.transition(db, f, target, action="FLAG_UPDATED")
    except LifecycleError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    if body.owner is not None:
        f.owner = body.owner
    if body.description is not None:
        f.description = body.description
    if body.expected_expiry_date is not None:
        f.expected_expiry_date = body.expected_expiry_date  # type: ignore[attr-defined]
    if body.current_value is not None:
        f.current_value = body.current_value  # type: ignore[attr-defined]
    f.last_modified = utcnow_iso()
    db.commit()
    db.refresh(f)
    return flag_out(f)


@router.get("/api/flags/{flag_id}/history", summary="Audit history for a flag")
def flag_history(flag_id: str, db: Session = Depends(get_db)):
    f = _flag_or_404(db, flag_id)
    from .lifecycle_mappers import audit_out
    rows = (db.query(AuditLog).filter_by(feature_flag_id=f.id)
            .order_by(AuditLog.timestamp).all())
    return [audit_out(a) for a in rows]


@router.post("/api/flags/{flag_id}/evaluations", response_model=EvaluationOut, status_code=201,
             summary="Record real evaluation telemetry for a flag")
def record_evaluation(flag_id: str, body: EvaluationIn, db: Session = Depends(get_db)):
    f = _flag_or_404(db, flag_id)
    row = FlagEvaluation(id=new_id("eval"), feature_flag_id=f.id, environment=body.environment,
                         evaluation_count=body.evaluation_count, enabled_count=body.enabled_count,
                         disabled_count=body.disabled_count, last_evaluated_at=body.last_evaluated_at,
                         evaluation_frequency=body.evaluation_frequency)
    db.add(row)
    f.last_evaluated_at = body.last_evaluated_at  # type: ignore[attr-defined]
    f.evaluations_last_7d = body.evaluation_count
    f.evaluations_count = (f.evaluations_count or 0) + body.evaluation_count
    db.commit()
    db.refresh(row)
    return eval_out(row)


@router.get("/api/flags/{flag_id}/evaluations", response_model=list[EvaluationOut])
def list_evaluations(flag_id: str, db: Session = Depends(get_db)):
    f = _flag_or_404(db, flag_id)
    rows = db.query(FlagEvaluation).filter_by(feature_flag_id=f.id).order_by(FlagEvaluation.created_at.desc()).all()
    return [eval_out(r) for r in rows]
