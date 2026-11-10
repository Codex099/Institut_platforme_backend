from decimal import Decimal
from typing import List, Optional
from fastapi import APIRouter, Depends, Request
from fastapi.responses import Response
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.branch_scope import BranchScope, get_branch_scope
from app.core.exceptions import NotFoundError
from app.core.permissions import Action, require_permission
from app.db.session import get_db
from app.models.enrollment import Enrollment
from app.models.payment import Payment
from app.models.user import User
from app.schemas.common import PaginatedResponse
from app.schemas.payment import (
    PaymentCancelRequest,
    PaymentCreate,
    PaymentResponse,
    UnpaidBalanceItem,
)
from app.services.payment_service import payment_service
from app.services.receipt_service import receipt_service

router = APIRouter(prefix="/payments", tags=["Payments"])


@router.get("", response_model=PaginatedResponse[PaymentResponse])
def list_payments(
    page: int = 1,
    page_size: int = 20,
    enrollment_id: Optional[int] = None,
    status: Optional[str] = None,
    scope: BranchScope = Depends(get_branch_scope),
    current_user: dict = Depends(require_permission("payments", Action.VIEW)),
    db: Session = Depends(get_db),
):
    query = db.query(Payment)
    query = scope.apply_query_filter(query, Payment)
    if enrollment_id:
        query = query.filter(Payment.enrollment_id == enrollment_id)
    if status:
        query = query.filter(Payment.status == status)

    total = query.count()
    items = query.order_by(Payment.id.desc()).offset((page - 1) * page_size).limit(page_size).all()
    pages = (total + page_size - 1) // page_size
    return PaginatedResponse(items=items, total=total, page=page, page_size=page_size, pages=pages)


@router.post("", response_model=PaymentResponse)
def record_payment(
    data: PaymentCreate,
    request: Request,
    scope: BranchScope = Depends(get_branch_scope),
    current_user: dict = Depends(require_permission("payments", Action.CREATE)),
    db: Session = Depends(get_db),
):
    enr = db.query(Enrollment).filter(Enrollment.id == data.enrollment_id).first()
    if not enr:
        raise NotFoundError(message_key="enrollment_not_found")
    scope.ensure_access(enr.branch_id)

    user_id = int(current_user["sub"])
    user = db.query(User).filter(User.id == user_id).first()
    ip = request.client.host if request.client else None

    return payment_service.record_payment(
        db=db,
        data=data,
        receiver_id=user_id,
        receiver_name=user.full_name if user else "Agent",
        ip_address=ip,
    )


@router.post("/{id}/cancel", response_model=PaymentResponse)
def cancel_payment(
    id: int,
    data: PaymentCancelRequest,
    request: Request,
    scope: BranchScope = Depends(get_branch_scope),
    current_user: dict = Depends(require_permission("payments", Action.VALIDATE)),
    db: Session = Depends(get_db),
):
    payment = db.query(Payment).filter(Payment.id == id).first()
    if not payment:
        raise NotFoundError(message_key="payment_not_found")
    scope.ensure_access(payment.branch_id)

    ip = request.client.host if request.client else None
    return payment_service.cancel_payment(
        db=db,
        payment_id=id,
        reason=data.reason,
        canceller_id=int(current_user["sub"]),
        ip_address=ip,
    )


@router.get("/{id}/receipt")
def get_payment_receipt_pdf(
    id: int,
    scope: BranchScope = Depends(get_branch_scope),
    current_user: dict = Depends(require_permission("payments", Action.VIEW)),
    db: Session = Depends(get_db),
):
    payment = db.query(Payment).filter(Payment.id == id).first()
    if not payment:
        raise NotFoundError(message_key="payment_not_found")
    scope.ensure_access(payment.branch_id)

    enr = payment.enrollment
    student_name = f"{enr.student.first_name} {enr.student.last_name}" if enr.student else "Étudiant"
    group_name = enr.group.name if enr.group else "Groupe"
    course_name = enr.group.level.course.name_en if enr.group and enr.group.level and enr.group.level.course else "Formation"
    branch_name = payment.branch.name if payment.branch else "Établissement"

    total_fee, total_paid, remaining = payment_service.get_enrollment_balance(db, enr.id)

    pdf_buffer = receipt_service.generate_payment_receipt_pdf(
        payment=payment,
        student_name=student_name,
        group_name=group_name,
        course_name=course_name,
        total_fee=total_fee,
        total_paid=total_paid,
        remaining_balance=remaining,
        branch_name=branch_name,
    )

    return Response(
        content=pdf_buffer.getvalue(),
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="receipt_{payment.receipt_number}.pdf"'},
    )


@router.get("/unpaid", response_model=List[UnpaidBalanceItem])
def get_unpaid_balances(
    scope: BranchScope = Depends(get_branch_scope),
    current_user: dict = Depends(require_permission("payments", Action.VIEW)),
    db: Session = Depends(get_db),
):
    query = db.query(Enrollment).filter(Enrollment.status == "confirmed")
    query = scope.apply_query_filter(query, Enrollment)
    enrollments = query.all()

    unpaid_list = []
    for enr in enrollments:
        net_fee, paid, remaining = payment_service.get_enrollment_balance(db, enr.id)
        if remaining > 0:
            student_name = f"{enr.student.first_name} {enr.student.last_name}" if enr.student else "Inconnu"
            group_name = enr.group.name if enr.group else "Inconnu"
            unpaid_list.append(
                UnpaidBalanceItem(
                    enrollment_id=enr.id,
                    student_id=enr.student_id,
                    student_name=student_name,
                    group_name=group_name,
                    total_fee=net_fee,
                    paid_amount=paid,
                    remaining_balance=remaining,
                )
            )
    return unpaid_list

