from typing import List, Optional
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.branch_scope import BranchScope, get_branch_scope
from app.core.exceptions import NotFoundError
from app.core.permissions import Action, require_permission
from app.db.session import get_db
from app.models.closure_day import ClosureDay
from app.schemas.closure_day import ClosureDayCreate, ClosureDayResponse, ClosureDayUpdate
from app.schemas.common import StatusResponse
from app.services.schedule_service import schedule_service

router = APIRouter(prefix="/closure-days", tags=["Closure Days"])


@router.get("", response_model=List[ClosureDayResponse])
def list_closure_days(
    scope: BranchScope = Depends(get_branch_scope),
    current_user: dict = Depends(require_permission("closure_days", Action.VIEW)),
    db: Session = Depends(get_db),
):
    query = db.query(ClosureDay)
    if not scope.is_global:
        query = query.filter((ClosureDay.branch_id == scope.selected_branch_id) | (ClosureDay.branch_id.is_(None)))
    return query.order_by(ClosureDay.start_date.asc()).all()


@router.post("", response_model=ClosureDayResponse)
def create_closure_day(
    data: ClosureDayCreate,
    scope: BranchScope = Depends(get_branch_scope),
    current_user: dict = Depends(require_permission("closure_days", Action.CREATE)),
    db: Session = Depends(get_db),
):
    if data.branch_id:
        scope.ensure_access(data.branch_id)

    closure = ClosureDay(
        branch_id=data.branch_id,
        name_ar=data.name_ar,
        name_en=data.name_en,
        start_date=data.start_date,
        end_date=data.end_date,
        reason=data.reason,
        created_by=int(current_user["sub"]),
    )
    db.add(closure)
    db.commit()
    db.refresh(closure)

    # Automatically cancel overlapping planned sessions
    schedule_service.apply_closure_day(db, closure, actor_id=int(current_user["sub"]))

    return closure


@router.delete("/{id}", response_model=StatusResponse)
def delete_closure_day(
    id: int,
    current_user: dict = Depends(require_permission("closure_days", Action.DELETE_ARCHIVE)),
    db: Session = Depends(get_db),
):
    closure = db.query(ClosureDay).filter(ClosureDay.id == id).first()
    if not closure:
        raise NotFoundError(message_key="resource_not_found")
    db.delete(closure)
    db.commit()
    return StatusResponse(code="SUCCESS", message="Closure day deleted.")

