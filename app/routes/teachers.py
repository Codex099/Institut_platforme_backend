from datetime import date, datetime, timedelta
from typing import List, Optional
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.branch_scope import BranchScope, get_branch_scope
from app.core.exceptions import NotFoundError, PermissionDeniedError
from app.core.permissions import Action, Role, require_permission
from app.core.security import get_current_user_payload
from app.db.session import get_db
from app.models.group import Group
from app.models.schedule import ScheduleSlot
from app.models.session import ClassSession
from app.models.teacher import Teacher
from app.schemas.group import GroupResponse
from app.schemas.session import ClassSessionResponse
from app.schemas.teacher import TeacherCreate, TeacherResponse, TeacherUpdate

router = APIRouter(prefix="/teachers", tags=["Teachers"])


@router.get("", response_model=List[TeacherResponse])
def list_teachers(
    scope: BranchScope = Depends(get_branch_scope),
    current_user: dict = Depends(require_permission("teachers", Action.VIEW)),
    db: Session = Depends(get_db),
):
    query = db.query(Teacher).filter(Teacher.is_archived.is_(False))
    query = scope.apply_query_filter(query, Teacher)
    teachers = query.all()

    results = []
    for t in teachers:
        results.append(
            TeacherResponse(
                id=t.id,
                user_id=t.user_id,
                branch_id=t.branch_id,
                phone=t.phone,
                specialties=t.specialties,
                pay_mode=t.pay_mode,
                pay_rate=t.pay_rate,
                contract_notes=t.contract_notes,
                user_full_name=t.user.full_name if t.user else None,
                user_email=t.user.email if t.user else None,
                created_at=t.created_at,
            )
        )
    return results


@router.post("", response_model=TeacherResponse)
def create_teacher(
    data: TeacherCreate,
    scope: BranchScope = Depends(get_branch_scope),
    current_user: dict = Depends(require_permission("teachers", Action.CREATE)),
    db: Session = Depends(get_db),
):
    scope.ensure_access(data.branch_id)
    teacher = Teacher(**data.model_dump())
    db.add(teacher)
    db.commit()
    db.refresh(teacher)
    return TeacherResponse(
        id=teacher.id,
        user_id=teacher.user_id,
        branch_id=teacher.branch_id,
        phone=teacher.phone,
        specialties=teacher.specialties,
        pay_mode=teacher.pay_mode,
        pay_rate=teacher.pay_rate,
        contract_notes=teacher.contract_notes,
        user_full_name=teacher.user.full_name if teacher.user else None,
        user_email=teacher.user.email if teacher.user else None,
        created_at=teacher.created_at,
    )


@router.get("/me/groups", response_model=List[GroupResponse])
def get_teacher_groups(
    current_user: dict = Depends(get_current_user_payload),
    db: Session = Depends(get_db),
):
    user_id = int(current_user["sub"])
    teacher = db.query(Teacher).filter(Teacher.user_id == user_id, Teacher.is_archived.is_(False)).first()
    if not teacher:
        raise PermissionDeniedError(message_key="teacher_forbidden_resource")

    # Find distinct groups assigned to teacher via slots
    group_ids = (
        db.query(ScheduleSlot.group_id)
        .filter(ScheduleSlot.teacher_id == teacher.id)
        .distinct()
        .all()
    )
    ids = [g[0] for g in group_ids]
    return db.query(Group).filter(Group.id.in_(ids), Group.is_archived.is_(False)).all()


@router.get("/me/sessions", response_model=List[ClassSessionResponse])
def get_teacher_sessions(
    days_ahead: int = 7,
    current_user: dict = Depends(get_current_user_payload),
    db: Session = Depends(get_db),
):
    user_id = int(current_user["sub"])
    teacher = db.query(Teacher).filter(Teacher.user_id == user_id, Teacher.is_archived.is_(False)).first()
    if not teacher:
        raise PermissionDeniedError(message_key="teacher_forbidden_resource")

    today = date.today()
    end_dt = today + timedelta(days=days_ahead)

    return (
        db.query(ClassSession)
        .filter(
            ClassSession.teacher_id == teacher.id,
            ClassSession.session_date >= today,
            ClassSession.session_date <= end_dt,
            ClassSession.status != "cancelled",
        )
        .order_by(ClassSession.session_date.asc(), ClassSession.start_time.asc())
        .all()
    )


@router.get("/{id}", response_model=TeacherResponse)
def get_teacher(
    id: int,
    scope: BranchScope = Depends(get_branch_scope),
    current_user: dict = Depends(require_permission("teachers", Action.VIEW)),
    db: Session = Depends(get_db),
):
    t = db.query(Teacher).filter(Teacher.id == id, Teacher.is_archived.is_(False)).first()
    if not t:
        raise NotFoundError(message_key="resource_not_found")
    scope.ensure_access(t.branch_id)
    return TeacherResponse(
        id=t.id,
        user_id=t.user_id,
        branch_id=t.branch_id,
        phone=t.phone,
        specialties=t.specialties,
        pay_mode=t.pay_mode,
        pay_rate=t.pay_rate,
        contract_notes=t.contract_notes,
        user_full_name=t.user.full_name if t.user else None,
        user_email=t.user.email if t.user else None,
        created_at=t.created_at,
    )


@router.put("/{id}", response_model=TeacherResponse)
def update_teacher(
    id: int,
    data: TeacherUpdate,
    scope: BranchScope = Depends(get_branch_scope),
    current_user: dict = Depends(require_permission("teachers", Action.UPDATE)),
    db: Session = Depends(get_db),
):
    t = db.query(Teacher).filter(Teacher.id == id, Teacher.is_archived.is_(False)).first()
    if not t:
        raise NotFoundError(message_key="resource_not_found")
    scope.ensure_access(t.branch_id)

    for field, val in data.model_dump(exclude_unset=True).items():
        setattr(t, field, val)

    db.commit()
    db.refresh(t)
    return TeacherResponse(
        id=t.id,
        user_id=t.user_id,
        branch_id=t.branch_id,
        phone=t.phone,
        specialties=t.specialties,
        pay_mode=t.pay_mode,
        pay_rate=t.pay_rate,
        contract_notes=t.contract_notes,
        user_full_name=t.user.full_name if t.user else None,
        user_email=t.user.email if t.user else None,
        created_at=t.created_at,
    )

