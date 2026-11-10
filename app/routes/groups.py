from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.branch_scope import BranchScope, get_branch_scope
from app.core.exceptions import ConflictError, NotFoundError, PermissionDeniedError
from app.core.permissions import Action, Role, require_permission
from app.db.session import get_db
from app.models.enrollment import Enrollment
from app.models.group import Group
from app.models.student import Student
from app.schemas.common import StatusResponse
from app.schemas.group import (
    GroupAvailabilityResponse,
    GroupCapacityUpdate,
    GroupCreate,
    GroupResponse,
    GroupUpdate,
)
from app.schemas.student import StudentResponse
from app.services.audit_service import audit_service
from app.services.enrollment_service import enrollment_service

router = APIRouter(prefix="/groups", tags=["Groups"])


@router.get("", response_model=List[GroupResponse])
def list_groups(
    level_id: Optional[int] = None,
    scope: BranchScope = Depends(get_branch_scope),
    current_user: dict = Depends(require_permission("groups", Action.VIEW)),
    db: Session = Depends(get_db),
):
    query = db.query(Group).filter(Group.is_archived.is_(False))
    query = scope.apply_query_filter(query, Group)
    if level_id:
        query = query.filter(Group.level_id == level_id)
    return query.all()


@router.post("", response_model=GroupResponse)
def create_group(
    data: GroupCreate,
    scope: BranchScope = Depends(get_branch_scope),
    current_user: dict = Depends(require_permission("groups", Action.CREATE)),
    db: Session = Depends(get_db),
):
    scope.ensure_access(data.branch_id)
    group = Group(**data.model_dump())
    if not group.capacity:
        group.capacity = 15
    db.add(group)
    db.commit()
    db.refresh(group)
    return group


@router.get("/{id}", response_model=GroupResponse)
def get_group(
    id: int,
    scope: BranchScope = Depends(get_branch_scope),
    current_user: dict = Depends(require_permission("groups", Action.VIEW)),
    db: Session = Depends(get_db),
):
    group = db.query(Group).filter(Group.id == id, Group.is_archived.is_(False)).first()
    if not group:
        raise NotFoundError(message_key="group_not_found")
    scope.ensure_access(group.branch_id)
    return group


@router.put("/{id}", response_model=GroupResponse)
def update_group(
    id: int,
    data: GroupUpdate,
    scope: BranchScope = Depends(get_branch_scope),
    current_user: dict = Depends(require_permission("groups", Action.UPDATE)),
    db: Session = Depends(get_db),
):
    group = db.query(Group).filter(Group.id == id, Group.is_archived.is_(False)).first()
    if not group:
        raise NotFoundError(message_key="group_not_found")
    scope.ensure_access(group.branch_id)

    for field, val in data.model_dump(exclude_unset=True).items():
        setattr(group, field, val)

    db.commit()
    db.refresh(group)
    return group


@router.patch("/{id}/capacity", response_model=GroupResponse)
def update_group_capacity(
    id: int,
    data: GroupCapacityUpdate,
    scope: BranchScope = Depends(get_branch_scope),
    current_user: dict = Depends(require_permission("groups", Action.SET_CAPACITY)),
    db: Session = Depends(get_db),
):
    """Update group capacity limit. Refuses if new limit is less than active occupied spots."""
    group = db.query(Group).filter(Group.id == id, Group.is_archived.is_(False)).with_for_update().first()
    if not group:
        raise NotFoundError(message_key="group_not_found")
    scope.ensure_access(group.branch_id)

    now = datetime.now(timezone.utc)
    _, _, occupied = enrollment_service.get_occupied_spots(db, group.id, now)

    if data.capacity < occupied:
        raise ConflictError(
            message_key="group_capacity_reduction_forbidden",
            details={"requested_capacity": data.capacity, "currently_occupied": occupied},
        )

    old_capacity = group.capacity
    user_id = int(current_user["sub"])
    group.capacity = data.capacity
    group.capacity_updated_by = user_id
    group.capacity_updated_at = now

    audit_service.log(
        db=db,
        action="update_group_capacity",
        entity="Group",
        entity_id=group.id,
        user_id=user_id,
        before_json={"capacity": old_capacity},
        after_json={"capacity": data.capacity, "reason": data.reason},
    )
    db.commit()
    db.refresh(group)
    return group


@router.get("/{id}/availability", response_model=GroupAvailabilityResponse)
def get_group_availability(
    id: int,
    db: Session = Depends(get_db),
):
    group = db.query(Group).filter(Group.id == id, Group.is_archived.is_(False)).first()
    if not group:
        raise NotFoundError(message_key="group_not_found")

    cap = enrollment_service.get_effective_capacity(db, group)
    conf, res, occupied = enrollment_service.get_occupied_spots(db, group.id)
    avail = max(0, cap - occupied)

    return GroupAvailabilityResponse(
        group_id=group.id,
        group_name=group.name,
        total_capacity=cap,
        confirmed_enrollments=conf,
        active_reservations=res,
        available_spots=avail,
        is_full=(avail == 0),
    )


@router.get("/{id}/students", response_model=List[StudentResponse])
def get_group_students(
    id: int,
    scope: BranchScope = Depends(get_branch_scope),
    current_user: dict = Depends(require_permission("groups", Action.VIEW)),
    db: Session = Depends(get_db),
):
    group = db.query(Group).filter(Group.id == id, Group.is_archived.is_(False)).first()
    if not group:
        raise NotFoundError(message_key="group_not_found")
    scope.ensure_access(group.branch_id)

    enrollments = (
        db.query(Enrollment)
        .filter(Enrollment.group_id == id, Enrollment.status == "confirmed")
        .all()
    )
    return [e.student for e in enrollments if e.student and not e.student.is_archived]

