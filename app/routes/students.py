from typing import List, Optional
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.branch_scope import BranchScope, get_branch_scope
from app.core.exceptions import NotFoundError, PermissionDeniedError
from app.core.permissions import Action, require_permission
from app.core.security import get_current_user_payload
from app.db.session import get_db
from app.models.student import Student
from app.schemas.common import PaginatedResponse, StatusResponse
from app.schemas.student import StudentCreate, StudentResponse, StudentUpdate
from app.services.audit_service import audit_service

router = APIRouter(prefix="/students", tags=["Students"])


@router.get("", response_model=PaginatedResponse[StudentResponse])
def list_students(
    page: int = 1,
    page_size: int = 20,
    status: Optional[str] = None,
    scope: BranchScope = Depends(get_branch_scope),
    current_user: dict = Depends(require_permission("students", Action.VIEW)),
    db: Session = Depends(get_db),
):
    query = db.query(Student).filter(Student.is_archived.is_(False))
    query = scope.apply_query_filter(query, Student)
    if status:
        query = query.filter(Student.status == status)

    total = query.count()
    items = query.order_by(Student.id.desc()).offset((page - 1) * page_size).limit(page_size).all()
    pages = (total + page_size - 1) // page_size
    return PaginatedResponse(items=items, total=total, page=page, page_size=page_size, pages=pages)


@router.post("", response_model=StudentResponse)
def create_student(
    data: StudentCreate,
    scope: BranchScope = Depends(get_branch_scope),
    current_user: dict = Depends(require_permission("students", Action.CREATE)),
    db: Session = Depends(get_db),
):
    scope.ensure_access(data.branch_id)
    std_num = data.student_number or f"STD-{data.branch_id}-{Student.id}"
    student = Student(**data.model_dump())
    if not data.student_number:
        student.student_number = f"STD-{data.branch_id}-MANUAL"
    db.add(student)
    db.flush()
    if not data.student_number:
        student.student_number = f"STD-{data.branch_id}-{student.id:05d}"

    audit_service.log(
        db=db,
        action="create_student",
        entity="Student",
        entity_id=student.id,
        user_id=int(current_user["sub"]),
    )
    db.commit()
    db.refresh(student)
    return student


@router.get("/me", response_model=StudentResponse)
def get_student_me(
    current_user: dict = Depends(get_current_user_payload),
    db: Session = Depends(get_db),
):
    user_id = int(current_user["sub"])
    student = db.query(Student).filter(Student.user_id == user_id, Student.is_archived.is_(False)).first()
    if not student:
        raise NotFoundError(message_key="resource_not_found")
    return student


@router.get("/{id}", response_model=StudentResponse)
def get_student(
    id: int,
    scope: BranchScope = Depends(get_branch_scope),
    current_user: dict = Depends(require_permission("students", Action.VIEW)),
    db: Session = Depends(get_db),
):
    student = db.query(Student).filter(Student.id == id, Student.is_archived.is_(False)).first()
    if not student:
        raise NotFoundError(message_key="resource_not_found")
    scope.ensure_access(student.branch_id)
    return student


@router.put("/{id}", response_model=StudentResponse)
def update_student(
    id: int,
    data: StudentUpdate,
    scope: BranchScope = Depends(get_branch_scope),
    current_user: dict = Depends(require_permission("students", Action.UPDATE)),
    db: Session = Depends(get_db),
):
    student = db.query(Student).filter(Student.id == id, Student.is_archived.is_(False)).first()
    if not student:
        raise NotFoundError(message_key="resource_not_found")
    scope.ensure_access(student.branch_id)

    for field, val in data.model_dump(exclude_unset=True).items():
        setattr(student, field, val)

    audit_service.log(
        db=db,
        action="update_student",
        entity="Student",
        entity_id=student.id,
        user_id=int(current_user["sub"]),
    )
    db.commit()
    db.refresh(student)
    return student


@router.delete("/{id}", response_model=StatusResponse)
def delete_student(
    id: int,
    scope: BranchScope = Depends(get_branch_scope),
    current_user: dict = Depends(require_permission("students", Action.DELETE_ARCHIVE)),
    db: Session = Depends(get_db),
):
    student = db.query(Student).filter(Student.id == id, Student.is_archived.is_(False)).first()
    if not student:
        raise NotFoundError(message_key="resource_not_found")
    scope.ensure_access(student.branch_id)

    student.is_archived = True
    audit_service.log(
        db=db,
        action="archive_student",
        entity="Student",
        entity_id=student.id,
        user_id=int(current_user["sub"]),
    )
    db.commit()
    return StatusResponse(code="SUCCESS", message="Student archived successfully.")

