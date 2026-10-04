from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models.models import Repository
from ..schemas.schemas import RepositoryCreate, RepositoryOut
from ..services import git_service
from ..utils.helpers import ensure_workspace, new_id, safe_repo_path, utcnow_iso
from .mappers import repo_out
from ..config import get_settings

router = APIRouter(tags=["repositories"])
settings = get_settings()


@router.get("/api/repositories", response_model=list[RepositoryOut], summary="List monitored repositories")
def list_repositories(db: Session = Depends(get_db)):
    return [repo_out(r) for r in db.query(Repository).order_by(Repository.name).all()]


@router.post("/api/repositories", response_model=RepositoryOut, status_code=201,
             summary="Register a repository (local path validated, git probed read-only)")
def create_repository(body: RepositoryCreate, db: Session = Depends(get_db)):
    ensure_workspace(settings.WORKSPACE_DIR)
    local = (body.local_path or body.url or "").strip()
    git_info: dict = {"available": False}
    if local and not local.startswith("http"):
        try:
            p = safe_repo_path(local, settings.WORKSPACE_DIR)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        git_info = git_service.collect_git_evidence(p)
        local = str(p)
    name = body.name or (local.split("/")[-1] if local else "repo")
    repo = Repository(
        id=new_id("repo"), name=name, full_name=body.full_name or name,
        owner=body.owner, url=body.url, local_path=local,
        default_branch=body.default_branch or "main", language=body.language,
        scan_status="idle", last_scanned_at="",
    )
    if git_info.get("available"):
        repo.default_branch = git_info.get("branch") or repo.default_branch
    db.add(repo)
    db.commit()
    db.refresh(repo)
    return repo_out(repo)


@router.get("/api/repositories/{repo_id}", response_model=RepositoryOut, summary="Get one repository")
def get_repository(repo_id: str, db: Session = Depends(get_db)):
    r = db.get(Repository, repo_id)
    if not r:
        raise HTTPException(status_code=404, detail="repository not found")
    return repo_out(r)


@router.get("/api/repositories/{repo_id}/git", summary="Live read-only git evidence for a repository")
def repository_git(repo_id: str, db: Session = Depends(get_db)):
    r = db.get(Repository, repo_id)
    if not r:
        raise HTTPException(status_code=404, detail="repository not found")
    if not r.local_path:
        return {"available": False, "reason": "no local_path registered; git evidence UNAVAILABLE"}
    from pathlib import Path
    return git_service.collect_git_evidence(Path(r.local_path))
