from typing import List, Optional
from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.core.branch_scope import BranchScope, get_branch_scope
from app.core.exceptions import NotFoundError
from app.core.permissions import Action, require_permission
from app.db.session import get_db
from app.models.enrollment import Enrollment
from app.schemas.common import PaginatedResponse, StatusResponse
from app.schemas.enrollment import (
    CancelEnrollmentRequest,
    ConfirmEnrollmentRequest,
    EnrollmentCreate,
    EnrollmentResponse,
    ExtendReservationRequest,
)
from app.services.enrollment_service import enrollment_service

router = APIRouter(prefix="/enrollments", tags=["Enrollments"])


@router.get("", response_model=PaginatedResponse[EnrollmentResponse])
def list_enrollments(
    page: int = 1,
    page_size: int = 20,
    status: Optional[str] = None,
    group_id: Optional[int] = None,
    student_id: Optional[int] = None,
    scope: BranchScope = Depends(get_branch_scope),
    current_user: dict = Depends(require_permission("enrollments", Action.VIEW)),
    db: Session = Depends(get_db),
):
    query = db.query(Enrollment)
    query = scope.apply_query_filter(query, Enrollment)
    if status:
        query = query.filter(Enrollment.status == status)
    if group_id:
        query = query.filter(Enrollment.group_id == group_id)
    if student_id:
        query = query.filter(Enrollment.student_id == student_id)

    total = query.count()
    items = query.order_by(Enrollment.id.desc()).offset((page - 1) * page_size).limit(page_size).all()
    pages = (total + page_size - 1) // page_size
    return PaginatedResponse(items=items, total=total, page=page, page_size=page_size, pages=pages)


@router.post("", response_model=EnrollmentResponse)
def create_enrollment(
    data: EnrollmentCreate,
    request: Request,
    scope: BranchScope = Depends(get_branch_scope),
    current_user: dict = Depends(require_permission("enrollments", Action.CREATE)),
    db: Session = Depends(get_db),
):
    scope.ensure_access(data.branch_id)
    ip = request.client.host if request.client else None
    return enrollment_service.create_enrollment(
        db=db,
        data=data,
        creator_id=int(current_user["sub"]),
        creator_role=current_user.get("role"),
        ip_address=ip,
    )


@router.get("/{id}", response_model=EnrollmentResponse)
def get_enrollment(
    id: int,
    scope: BranchScope = Depends(get_branch_scope),
    current_user: dict = Depends(require_permission("enrollments", Action.VIEW)),
    db: Session = Depends(get_db),
):
    enrollment = db.query(Enrollment).filter(Enrollment.id == id).first()
    if not enrollment:
        raise NotFoundError(message_key="enrollment_not_found")
    scope.ensure_access(enrollment.branch_id)
    return enrollment


@router.post("/{id}/confirm", response_model=EnrollmentResponse)
def confirm_enrollment(
    id: int,
    data: ConfirmEnrollmentRequest,
    request: Request,
    scope: BranchScope = Depends(get_branch_scope),
    current_user: dict = Depends(require_permission("enrollments", Action.VALIDATE)),
    db: Session = Depends(get_db),
):
    ip = request.client.host if request.client else None
    return enrollment_service.confirm_enrollment(
        db=db,
        enrollment_id=id,
        initial_payment_amount=data.initial_payment_amount,
        payment_method=data.payment_method,
        confirmer_id=int(current_user["sub"]),
        cash_register_id=data.cash_register_id,
        notes=data.notes,
        ip_address=ip,
    )


@router.post("/{id}/cancel", response_model=EnrollmentResponse)
def cancel_enrollment(
    id: int,
    data: CancelEnrollmentRequest,
    scope: BranchScope = Depends(get_branch_scope),
    current_user: dict = Depends(require_permission("enrollments", Action.DELETE_ARCHIVE)),
    db: Session = Depends(get_db),
):
    return enrollment_service.cancel_enrollment(
        db=db,
        enrollment_id=id,
        reason=data.reason,
        canceller_id=int(current_user["sub"]),
    )


@router.post("/{id}/extend-reservation", response_model=EnrollmentResponse)
def extend_reservation(
    id: int,
    data: ExtendReservationRequest,
    scope: BranchScope = Depends(get_branch_scope),
    current_user: dict = Depends(require_permission("enrollments", Action.UPDATE)),
    db: Session = Depends(get_db),
):
    return enrollment_service.extend_reservation(
        db=db,
        enrollment_id=id,
        additional_hours=data.additional_hours,
        actor_id=int(current_user["sub"]),
    )

