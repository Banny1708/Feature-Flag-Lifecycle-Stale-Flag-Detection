"""Repository registration.

Two supported modes (both persist to the same `repositories` table):

MODE A (managed clone):  body.url is a GitHub HTTPS URL and no local_path is
    given -> FlagOps clones into WORKSPACE_DIR/repositories/<repo-id>/source,
    stores that path in local_path, and records branch/commit. Clone failures
    return an API error and leave no repository record / no partial workspace.

MODE B (operator checkout): body.local_path points at an existing local git
    checkout -> validated read-only, never cloned, never deleted.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models.models import Repository
from ..schemas.schemas import RepositoryCreate, RepositoryOut
from ..services import git_service, repo_service
from ..services.repo_service import CloneError
from ..utils.helpers import ensure_workspace, new_id, safe_repo_path
from .mappers import repo_out
from ..config import get_settings

router = APIRouter(tags=["repositories"])
settings = get_settings()

# CloneError.code -> HTTP status. Auth uses 401 so the UI can hint at tokens;
# missing repos are 404; timeouts/network map to gateway-ish codes.
_CODE_TO_STATUS = {
    "INVALID_URL": 400,
    "REPOSITORY_NOT_FOUND": 404,
    "AUTHENTICATION_FAILED": 401,
    "BRANCH_NOT_FOUND": 400,
    "NETWORK_ERROR": 502,
    "GIT_UNAVAILABLE": 500,
    "CLONE_TIMEOUT": 504,
    "WORKSPACE_ERROR": 500,
    "UNKNOWN_GIT_ERROR": 500,
}


def _github_token(db: Session) -> str:
    """Read the operator-configured github_token without ever exposing it."""
    try:
        from .settings import get_effective_settings
        val = get_effective_settings(db).get("github_token", "")
        return val if isinstance(val, str) else ""
    except Exception:
        return ""


@router.get("/api/repositories", response_model=list[RepositoryOut], summary="List monitored repositories")
def list_repositories(db: Session = Depends(get_db)):
    return [repo_out(r) for r in db.query(Repository).order_by(Repository.name).all()]


@router.post("/api/repositories", response_model=RepositoryOut, status_code=201,
             summary="Register a repository: GitHub URL is cloned, or a local checkout is validated")
def create_repository(body: RepositoryCreate, db: Session = Depends(get_db)):
    ensure_workspace(settings.WORKSPACE_DIR)
    url = (body.url or "").strip()
    local_path = (body.local_path or "").strip()

    # ---- MODE B: explicit local checkout (unchanged legacy behavior) ----
    if local_path:
        try:
            p = safe_repo_path(local_path, settings.WORKSPACE_DIR)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        git_info = git_service.collect_git_evidence(p)
        name = body.name or p.name
        repo = Repository(
            id=new_id("repo"), name=name, full_name=body.full_name or name,
            owner=body.owner, url=url, local_path=str(p),
            default_branch=body.default_branch or "main", language=body.language,
            scan_status="idle", last_scanned_at="",
        )
        if git_info.get("available"):
            repo.default_branch = git_info.get("branch") or repo.default_branch
            repo.branch = git_info.get("branch", "")
            repo.commit_hash = git_info.get("commit", "")
        db.add(repo)
        db.commit()
        db.refresh(repo)
        return repo_out(repo)

    # ---- MODE A: GitHub URL -> real clone into isolated workspace ----
    if url:
        try:
            validated = repo_service.validate_repository_url(url)
        except CloneError as exc:
            raise HTTPException(status_code=_CODE_TO_STATUS[exc.code], detail=str(exc))
        repo_id = new_id("repo")
        token = _github_token(db)
        try:
            cloned = repo_service.clone_repository(
                validated["canonical_url"], repo_id,
                branch=(body.default_branch or "").strip() or "",
                access_token=token or None)
        except CloneError as exc:
            # No DB record is created; the service already removed any partial
            # workspace. Never include token material (service sanitizes).
            raise HTTPException(status_code=_CODE_TO_STATUS.get(exc.code, 500), detail=str(exc))
        name = body.name or cloned["name"]
        repo = Repository(
            id=repo_id, name=name,
            full_name=body.full_name or cloned["full_name"],
            owner=body.owner or cloned["owner"],
            url=cloned["source_url"],  # canonical URL only, never credentials
            local_path=cloned["local_path"],
            default_branch=cloned["branch"] or body.default_branch or "main",
            language=body.language,
            scan_status="idle", last_scanned_at="",
        )
        repo.branch = cloned["branch"]
        repo.commit_hash = cloned["commit_hash"]
        db.add(repo)
        db.commit()
        db.refresh(repo)
        return repo_out(repo)

    raise HTTPException(status_code=400,
                        detail="provide either a GitHub repository URL (url) or an existing "
                               "local checkout path (local_path)")


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
        return {"available": False, "reason": "no local checkout registered; connect via GitHub URL or local path first"}
    from pathlib import Path
    return git_service.collect_git_evidence(Path(r.local_path))
