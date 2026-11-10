from typing import List, Optional
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.branch_scope import BranchScope, get_branch_scope
from app.core.exceptions import NotFoundError
from app.core.permissions import Action, require_permission
from app.db.session import get_db
from app.models.teacher import Teacher
from app.models.teacher_payroll import TeacherPayroll
from app.schemas.teacher_payroll import (
    TeacherPayrollCalculateRequest,
    TeacherPayrollPayRequest,
    TeacherPayrollResponse,
)
from app.services.payroll_service import payroll_service

router = APIRouter(prefix="/payroll", tags=["Teacher Payroll"])


@router.get("", response_model=List[TeacherPayrollResponse])
def list_payrolls(
    teacher_id: Optional[int] = None,
    status: Optional[str] = None,
    scope: BranchScope = Depends(get_branch_scope),
    current_user: dict = Depends(require_permission("payroll", Action.VIEW)),
    db: Session = Depends(get_db),
):
    query = db.query(TeacherPayroll)
    query = scope.apply_query_filter(query, TeacherPayroll)
    if teacher_id:
        query = query.filter(TeacherPayroll.teacher_id == teacher_id)
    if status:
        query = query.filter(TeacherPayroll.status == status)

    records = query.order_by(TeacherPayroll.period_end.desc()).all()
    results = []
    for r in records:
        results.append(
            TeacherPayrollResponse(
                id=r.id,
                teacher_id=r.teacher_id,
                teacher_name=r.teacher.user.full_name if r.teacher and r.teacher.user else None,
                branch_id=r.branch_id,
                period_start=r.period_start,
                period_end=r.period_end,
                hours=r.hours,
                sessions_count=r.sessions_count,
                amount_due=r.amount_due,
                amount_paid=r.amount_paid,
                status=r.status,
                paid_at=r.paid_at,
                notes=r.notes,
                created_at=r.created_at,
            )
        )
    return results


@router.post("", response_model=TeacherPayrollResponse)
def calculate_teacher_payroll(
    data: TeacherPayrollCalculateRequest,
    scope: BranchScope = Depends(get_branch_scope),
    current_user: dict = Depends(require_permission("payroll", Action.CREATE)),
    db: Session = Depends(get_db),
):
    teacher = db.query(Teacher).filter(Teacher.id == data.teacher_id).first()
    if not teacher:
        raise NotFoundError(message_key="resource_not_found")
    scope.ensure_access(teacher.branch_id)

    payroll = payroll_service.calculate_teacher_payroll(
        db=db,
        teacher_id=data.teacher_id,
        period_start=data.period_start,
        period_end=data.period_end,
        actor_id=int(current_user["sub"]),
    )
    return TeacherPayrollResponse(
        id=payroll.id,
        teacher_id=payroll.teacher_id,
        teacher_name=payroll.teacher.user.full_name if payroll.teacher and payroll.teacher.user else None,
        branch_id=payroll.branch_id,
        period_start=payroll.period_start,
        period_end=payroll.period_end,
        hours=payroll.hours,
        sessions_count=payroll.sessions_count,
        amount_due=payroll.amount_due,
        amount_paid=payroll.amount_paid,
        status=payroll.status,
        paid_at=payroll.paid_at,
        notes=payroll.notes,
        created_at=payroll.created_at,
    )


@router.post("/{id}/pay", response_model=TeacherPayrollResponse)
def pay_teacher_payroll(
    id: int,
    data: TeacherPayrollPayRequest,
    scope: BranchScope = Depends(get_branch_scope),
    current_user: dict = Depends(require_permission("payroll", Action.UPDATE)),
    db: Session = Depends(get_db),
):
    payroll = db.query(TeacherPayroll).filter(TeacherPayroll.id == id).first()
    if not payroll:
        raise NotFoundError(message_key="resource_not_found")
    scope.ensure_access(payroll.branch_id)

    updated = payroll_service.pay_teacher(
        db=db,
        payroll_id=id,
        cash_register_id=data.cash_register_id,
        notes=data.notes,
        actor_id=int(current_user["sub"]),
    )
    return TeacherPayrollResponse(
        id=updated.id,
        teacher_id=updated.teacher_id,
        teacher_name=updated.teacher.user.full_name if updated.teacher and updated.teacher.user else None,
        branch_id=updated.branch_id,
        period_start=updated.period_start,
        period_end=updated.period_end,
        hours=updated.hours,
        sessions_count=updated.sessions_count,
        amount_due=updated.amount_due,
        amount_paid=updated.amount_paid,
        status=updated.status,
        paid_at=updated.paid_at,
        notes=updated.notes,
        created_at=updated.created_at,
    )

