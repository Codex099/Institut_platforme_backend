from typing import List, Optional
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.branch_scope import BranchScope, get_branch_scope
from app.core.exceptions import NotFoundError
from app.core.permissions import Action, require_permission
from app.db.session import get_db
from app.models.course import Course
from app.schemas.common import StatusResponse
from app.schemas.course import CourseCreate, CourseResponse, CourseUpdate

router = APIRouter(prefix="/courses", tags=["Courses"])


@router.get("", response_model=List[CourseResponse])
def list_courses(
    scope: BranchScope = Depends(get_branch_scope),
    current_user: dict = Depends(require_permission("courses", Action.VIEW)),
    db: Session = Depends(get_db),
):
    query = db.query(Course).filter(Course.is_archived.is_(False))
    query = scope.apply_query_filter(query, Course)
    return query.all()


@router.post("", response_model=CourseResponse)
def create_course(
    data: CourseCreate,
    scope: BranchScope = Depends(get_branch_scope),
    current_user: dict = Depends(require_permission("courses", Action.CREATE)),
    db: Session = Depends(get_db),
):
    scope.ensure_access(data.branch_id)
    course = Course(**data.model_dump())
    db.add(course)
    db.commit()
    db.refresh(course)
    return course


@router.get("/{id}", response_model=CourseResponse)
def get_course(
    id: int,
    scope: BranchScope = Depends(get_branch_scope),
    current_user: dict = Depends(require_permission("courses", Action.VIEW)),
    db: Session = Depends(get_db),
):
    course = db.query(Course).filter(Course.id == id, Course.is_archived.is_(False)).first()
    if not course:
        raise NotFoundError(message_key="resource_not_found")
    scope.ensure_access(course.branch_id)
    return course


@router.put("/{id}", response_model=CourseResponse)
def update_course(
    id: int,
    data: CourseUpdate,
    scope: BranchScope = Depends(get_branch_scope),
    current_user: dict = Depends(require_permission("courses", Action.UPDATE)),
    db: Session = Depends(get_db),
):
    course = db.query(Course).filter(Course.id == id, Course.is_archived.is_(False)).first()
    if not course:
        raise NotFoundError(message_key="resource_not_found")
    scope.ensure_access(course.branch_id)

    for field, val in data.model_dump(exclude_unset=True).items():
        setattr(course, field, val)

    db.commit()
    db.refresh(course)
    return course


@router.delete("/{id}", response_model=StatusResponse)
def delete_course(
    id: int,
    scope: BranchScope = Depends(get_branch_scope),
    current_user: dict = Depends(require_permission("courses", Action.DELETE_ARCHIVE)),
    db: Session = Depends(get_db),
):
    course = db.query(Course).filter(Course.id == id, Course.is_archived.is_(False)).first()
    if not course:
        raise NotFoundError(message_key="resource_not_found")
    scope.ensure_access(course.branch_id)

    course.is_archived = True
    db.commit()
    return StatusResponse(code="SUCCESS", message="Course archived successfully.")

