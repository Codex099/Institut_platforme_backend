from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Optional
from sqlalchemy.orm import Session

from app.core.exceptions import BadRequestError, NotFoundError
from app.models.cash_register import CashRegister
from app.models.session import ClassSession
from app.models.teacher import Teacher
from app.models.teacher_payroll import TeacherPayroll
from app.services.audit_service import audit_service
from app.services.cash_service import cash_service


class PayrollService:
    @classmethod
    def calculate_teacher_payroll(
        cls,
        db: Session,
        teacher_id: int,
        period_start: date,
        period_end: date,
        actor_id: Optional[int] = None,
    ) -> TeacherPayroll:
        teacher = db.query(Teacher).filter(Teacher.id == teacher_id).first()
        if not teacher:
            raise NotFoundError(message_key="resource_not_found", details="Teacher not found")

        # Fetch strictly held sessions within period (CANCELLED SESSIONS ARE NEVER COUNTED)
        sessions = (
            db.query(ClassSession)
            .filter(
                ClassSession.teacher_id == teacher_id,
                ClassSession.session_date >= period_start,
                ClassSession.session_date <= period_end,
                ClassSession.status == "held",
            )
            .all()
        )

        sessions_count = len(sessions)
        total_hours = Decimal("0.00")

        for s in sessions:
            start_dt = datetime.combine(date.today(), s.start_time)
            end_dt = datetime.combine(date.today(), s.end_time)
            duration_hours = Decimal(str((end_dt - start_dt).total_seconds() / 3600.0))
            total_hours += duration_hours

        rate = Decimal(str(teacher.pay_rate or 0))
        amount_due = Decimal("0.00")

        if teacher.pay_mode == "hourly":
            amount_due = total_hours * rate
        elif teacher.pay_mode == "per_session":
            amount_due = Decimal(sessions_count) * rate
        elif teacher.pay_mode == "fixed":
            amount_due = rate
        else:
            amount_due = total_hours * rate

        payroll = TeacherPayroll(
            teacher_id=teacher.id,
            branch_id=teacher.branch_id,
            period_start=period_start,
            period_end=period_end,
            hours=round(total_hours, 2),
            sessions_count=sessions_count,
            amount_due=round(amount_due, 2),
            amount_paid=Decimal("0.00"),
            status="draft",
        )
        db.add(payroll)
        db.flush()

        audit_service.log(
            db=db,
            action="calculate_teacher_payroll",
            entity="TeacherPayroll",
            entity_id=payroll.id,
            user_id=actor_id,
            after_json={"amount_due": str(payroll.amount_due), "sessions_count": sessions_count, "hours": str(payroll.hours)},
        )

        db.commit()
        db.refresh(payroll)
        return payroll

    @classmethod
    def pay_teacher(
        cls,
        db: Session,
        payroll_id: int,
        cash_register_id: Optional[int] = None,
        notes: Optional[str] = None,
        actor_id: Optional[int] = None,
    ) -> TeacherPayroll:
        now = datetime.now(timezone.utc)
        payroll = db.query(TeacherPayroll).filter(TeacherPayroll.id == payroll_id).first()
        if not payroll:
            raise NotFoundError(message_key="resource_not_found")

        if payroll.status == "paid":
            raise BadRequestError(message_key="validation_error", details="Payroll record is already marked as paid.")

        reg = None
        if cash_register_id:
            reg = db.query(CashRegister).filter(CashRegister.id == cash_register_id).first()
        if not reg:
            reg = cash_service.get_branch_main_register(db, payroll.branch_id)

        # Deduct salary from cash register
        cash_service.record_movement(
            db=db,
            register_id=reg.id,
            movement_type="out",
            amount=Decimal(str(payroll.amount_due)),
            source_type="payroll",
            source_id=payroll.id,
            notes=f"Rémunération enseignant {payroll.teacher.user.full_name} ({payroll.period_start} à {payroll.period_end})",
            created_by=actor_id,
        )

        payroll.amount_paid = payroll.amount_due
        payroll.status = "paid"
        payroll.paid_at = now
        payroll.notes = notes

        audit_service.log(
            db=db,
            action="pay_teacher_payroll",
            entity="TeacherPayroll",
            entity_id=payroll.id,
            user_id=actor_id,
            after_json={"status": "paid", "amount_paid": str(payroll.amount_paid)},
        )

        db.commit()
        db.refresh(payroll)
        return payroll


payroll_service = PayrollService()

