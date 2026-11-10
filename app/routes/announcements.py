from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.branch_scope import BranchScope, get_branch_scope
from app.core.exceptions import NotFoundError
from app.core.permissions import Action, require_permission
from app.db.session import get_db
from app.models.announcement import Announcement
from app.schemas.announcement import AnnouncementCreate, AnnouncementResponse, AnnouncementUpdate
from app.schemas.common import StatusResponse

router = APIRouter(prefix="/announcements", tags=["Announcements"])


@router.get("", response_model=List[AnnouncementResponse])
def list_announcements(
    scope: BranchScope = Depends(get_branch_scope),
    current_user: dict = Depends(require_permission("announcements", Action.VIEW)),
    db: Session = Depends(get_db),
):
    query = db.query(Announcement).filter(Announcement.is_archived.is_(False))
    if not scope.is_global:
        query = query.filter((Announcement.branch_id == scope.selected_branch_id) | (Announcement.branch_id.is_(None)))
    return query.order_by(Announcement.published_at.desc()).all()


@router.post("", response_model=AnnouncementResponse)
def create_announcement(
    data: AnnouncementCreate,
    scope: BranchScope = Depends(get_branch_scope),
    current_user: dict = Depends(require_permission("announcements", Action.CREATE)),
    db: Session = Depends(get_db),
):
    if data.branch_id:
        scope.ensure_access(data.branch_id)
    ann = Announcement(**data.model_dump())
    db.add(ann)
    db.commit()
    db.refresh(ann)
    return ann


@router.delete("/{id}", response_model=StatusResponse)
def delete_announcement(
    id: int,
    current_user: dict = Depends(require_permission("announcements", Action.DELETE_ARCHIVE)),
    db: Session = Depends(get_db),
):
    ann = db.query(Announcement).filter(Announcement.id == id).first()
    if not ann:
        raise NotFoundError(message_key="resource_not_found")
    ann.is_archived = True
    db.commit()
    return StatusResponse(code="SUCCESS", message="Announcement archived.")

