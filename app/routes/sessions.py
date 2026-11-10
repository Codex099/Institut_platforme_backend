from datetime import date
from typing import List, Optional
from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.core.branch_scope import BranchScope, get_branch_scope
from app.core.exceptions import NotFoundError
from app.core.permissions import Action, require_permission
from app.db.session import get_db
from app.models.group import Group
from app.models.session import ClassSession
from app.schemas.session import (
    CancelSessionRequest,
    ClassSessionCreate,
    ClassSessionResponse,
    ClassSessionUpdate,
    GenerateSessionsRequest,
    GenerateSessionsResponse,
    RescheduleSessionRequest,
)
from app.services.schedule_service import schedule_service

router = APIRouter(prefix="/sessions", tags=["Sessions"])


@router.get("", response_model=List[ClassSessionResponse])
def list_sessions(
    group_id: Optional[int] = None,
    teacher_id: Optional[int] = None,
    room_id: Optional[int] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    scope: BranchScope = Depends(get_branch_scope),
    current_user: dict = Depends(require_permission("sessions", Action.VIEW)),
    db: Session = Depends(get_db),
):
    query = db.query(ClassSession).join(Group)
    query = scope.apply_query_filter(query, Group)
    if group_id:
        query = query.filter(ClassSession.group_id == group_id)
    if teacher_id:
        query = query.filter(ClassSession.teacher_id == teacher_id)
    if room_id:
        query = query.filter(ClassSession.room_id == room_id)
    if start_date:
        query = query.filter(ClassSession.session_date >= start_date)
    if end_date:
        query = query.filter(ClassSession.session_date <= end_date)

    return query.order_by(ClassSession.session_date.asc(), ClassSession.start_time.asc()).all()


@router.post("/generate", response_model=GenerateSessionsResponse)
def generate_sessions(
    data: GenerateSessionsRequest,
    scope: BranchScope = Depends(get_branch_scope),
    current_user: dict = Depends(require_permission("sessions", Action.CREATE)),
    db: Session = Depends(get_db),
):
    group = db.query(Group).filter(Group.id == data.group_id).first()
    if not group:
        raise NotFoundError(message_key="group_not_found")
    scope.ensure_access(group.branch_id)
    return schedule_service.generate_sessions(
        db, data.group_id, data.start_date, data.end_date, creator_id=int(current_user["sub"])
    )


@router.post("/{id}/cancel", response_model=ClassSessionResponse)
def cancel_session(
    id: int,
    data: CancelSessionRequest,
    request: Request,
    current_user: dict = Depends(require_permission("sessions", Action.VALIDATE)),
    db: Session = Depends(get_db),
):
    ip = request.client.host if request.client else None
    return schedule_service.cancel_session(
        db=db,
        session_id=id,
        reason=data.reason,
        canceller_id=int(current_user["sub"]),
        ip_address=ip,
    )


@router.post("/{id}/reschedule", response_model=ClassSessionResponse)
def reschedule_session(
    id: int,
    data: RescheduleSessionRequest,
    request: Request,
    current_user: dict = Depends(require_permission("sessions", Action.UPDATE)),
    db: Session = Depends(get_db),
):
    ip = request.client.host if request.client else None
    return schedule_service.reschedule_session(
        db=db,
        session_id=id,
        data=data,
        actor_id=int(current_user["sub"]),
        ip_address=ip,
    )


@router.get("/{id}", response_model=ClassSessionResponse)
def get_session(
    id: int,
    current_user: dict = Depends(require_permission("sessions", Action.VIEW)),
    db: Session = Depends(get_db),
):
    session = db.query(ClassSession).filter(ClassSession.id == id).first()
    if not session:
        raise NotFoundError(message_key="resource_not_found")
    return session

