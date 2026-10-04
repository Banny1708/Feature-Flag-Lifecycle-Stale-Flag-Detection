from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..database import get_db
from ..models.models import FeatureFlag
from ..schemas.schemas import FeatureFlagOut
from .mappers import flag_out

router = APIRouter(tags=["flags"])


@router.get("/api/flags", response_model=list[FeatureFlagOut], summary="List flags (status/repository/search)")
def list_flags(status: str = Query(default="all"), repositoryId: str = Query(default="all"),
               searchQuery: str = Query(default=""), db: Session = Depends(get_db)):
    q = db.query(FeatureFlag)
    if status and status != "all":
        q = q.filter_by(status=status)
    if repositoryId and repositoryId != "all":
        q = q.filter_by(repository_id=repositoryId)
    flags = q.order_by(FeatureFlag.key).limit(500).all()
    if searchQuery:
        s = searchQuery.lower()
        flags = [f for f in flags if s in (f.name or "").lower() or s in (f.key or "").lower()
                 or s in (f.description or "").lower()
                 or any(s in (t or "").lower() for t in (f.tags or []))]
    return [flag_out(f) for f in flags]


@router.get("/api/flags/stale", response_model=list[FeatureFlagOut], summary="List stale + potentially-stale flags")
def stale_flags(db: Session = Depends(get_db)):
    flags = db.query(FeatureFlag).filter(FeatureFlag.status.in_(["stale", "potentially-stale"])).all()
    return [flag_out(f) for f in flags]


@router.get("/api/flags/{flag_id}", response_model=FeatureFlagOut, summary="Get one flag")
def get_flag(flag_id: str, db: Session = Depends(get_db)):
    f = db.get(FeatureFlag, flag_id)
    if not f:
        # also allow lookup by key
        f = db.query(FeatureFlag).filter_by(key=flag_id).first()
    if not f:
        raise HTTPException(status_code=404, detail="flag not found")
    return flag_out(f)
