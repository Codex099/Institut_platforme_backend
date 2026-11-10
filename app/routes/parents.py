from datetime import datetime, timezone
from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.core.permissions import Action, require_permission
from app.core.security import get_current_user_payload
from app.db.session import get_db
from app.models.parent import Parent, StudentParent
from app.schemas.parent import (
    ParentCreate,
    ParentResponse,
    StudentParentLinkCreate,
    StudentParentLinkResponse,
)
from app.schemas.student import StudentResponse

router = APIRouter(prefix="/parents", tags=["Parents"])


@router.get("", response_model=List[ParentResponse])
def list_parents(
    current_user: dict = Depends(require_permission("parents", Action.VIEW)),
    db: Session = Depends(get_db),
):
    return db.query(Parent).all()


@router.post("", response_model=ParentResponse)
def create_parent(
    data: ParentCreate,
    current_user: dict = Depends(require_permission("parents", Action.CREATE)),
    db: Session = Depends(get_db),
):
    parent = Parent(**data.model_dump())
    db.add(parent)
    db.commit()
    db.refresh(parent)
    return parent


@router.post("/{id}/children", response_model=StudentParentLinkResponse)
def link_child_to_parent(
    id: int,
    data: StudentParentLinkCreate,
    current_user: dict = Depends(require_permission("parents", Action.CREATE)),
    db: Session = Depends(get_db),
):
    parent = db.query(Parent).filter(Parent.id == id).first()
    if not parent:
        raise NotFoundError(message_key="resource_not_found")

    link = StudentParent(
        student_id=data.student_id,
        parent_id=id,
        relationship_type=data.relationship_type,
        is_validated=False,
    )
    db.add(link)
    db.commit()
    db.refresh(link)
    return link


@router.post("/{id}/children/{student_id}/validate", response_model=StudentParentLinkResponse)
def validate_parent_child_link(
    id: int,
    student_id: int,
    current_user: dict = Depends(require_permission("parents", Action.VALIDATE)),
    db: Session = Depends(get_db),
):
    link = (
        db.query(StudentParent)
        .filter(StudentParent.parent_id == id, StudentParent.student_id == student_id)
        .first()
    )
    if not link:
        raise NotFoundError(message_key="resource_not_found")

    link.is_validated = True
    link.validated_by = int(current_user["sub"])
    link.validated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(link)
    return link


@router.get("/me/children", response_model=List[StudentResponse])
def get_parent_children(
    current_user: dict = Depends(get_current_user_payload),
    db: Session = Depends(get_db),
):
    user_id = int(current_user["sub"])
    parent = db.query(Parent).filter(Parent.user_id == user_id).first()
    if not parent:
        raise NotFoundError(message_key="resource_not_found")

    validated_links = (
        db.query(StudentParent)
        .filter(StudentParent.parent_id == parent.id, StudentParent.is_validated.is_(True))
        .all()
    )
    return [link.student for link in validated_links if link.student and not link.student.is_archived]

