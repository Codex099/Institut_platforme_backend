from typing import List, Optional
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.branch_scope import BranchScope, get_branch_scope
from app.core.exceptions import NotFoundError
from app.core.permissions import Action, require_permission
from app.db.session import get_db
from app.models.group import Group
from app.models.schedule import ScheduleSlot
from app.schemas.common import StatusResponse
from app.schemas.schedule import (
    CheckConflictRequest,
    CheckConflictResponse,
    ScheduleSlotCreate,
    ScheduleSlotResponse,
    ScheduleSlotUpdate,
)
from app.services.schedule_service import schedule_service

router = APIRouter(prefix="/schedules", tags=["Schedules"])


@router.get("", response_model=List[ScheduleSlotResponse])
def list_schedules(
    group_id: Optional[int] = None,
    room_id: Optional[int] = None,
    teacher_id: Optional[int] = None,
    scope: BranchScope = Depends(get_branch_scope),
    current_user: dict = Depends(require_permission("schedules", Action.VIEW)),
    db: Session = Depends(get_db),
):
    query = db.query(ScheduleSlot).join(Group)
    query = scope.apply_query_filter(query, Group)
    if group_id:
        query = query.filter(ScheduleSlot.group_id == group_id)
    if room_id:
        query = query.filter(ScheduleSlot.room_id == room_id)
    if teacher_id:
        query = query.filter(ScheduleSlot.teacher_id == teacher_id)
    return query.all()


@router.post("", response_model=ScheduleSlotResponse)
def create_schedule(
    data: ScheduleSlotCreate,
    scope: BranchScope = Depends(get_branch_scope),
    current_user: dict = Depends(require_permission("schedules", Action.CREATE)),
    db: Session = Depends(get_db),
):
    group = db.query(Group).filter(Group.id == data.group_id).first()
    if not group:
        raise NotFoundError(message_key="group_not_found")
    scope.ensure_access(group.branch_id)
    return schedule_service.create_slot(db, data, creator_id=int(current_user["sub"]))


@router.post("/check-conflicts", response_model=CheckConflictResponse)
def check_conflicts(
    data: CheckConflictRequest,
    current_user: dict = Depends(require_permission("schedules", Action.VIEW)),
    db: Session = Depends(get_db),
):
    conflicts = schedule_service.check_slot_conflicts(
        db=db,
        group_id=data.group_id,
        room_id=data.room_id,
        teacher_id=data.teacher_id,
        weekday=data.weekday,
        start_time=data.start_time,
        end_time=data.end_time,
    )
    return CheckConflictResponse(has_conflict=bool(conflicts), conflicts=conflicts)


@router.delete("/{id}", response_model=StatusResponse)
def delete_schedule(
    id: int,
    current_user: dict = Depends(require_permission("schedules", Action.DELETE_ARCHIVE)),
    db: Session = Depends(get_db),
):
    slot = db.query(ScheduleSlot).filter(ScheduleSlot.id == id).first()
    if not slot:
        raise NotFoundError(message_key="resource_not_found")
    db.delete(slot)
    db.commit()
    return StatusResponse(code="SUCCESS", message="Schedule slot deleted.")

