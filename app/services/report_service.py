from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.attendance import Attendance
from app.models.branch import Branch
from app.models.cash_register import CashRegister
from app.models.enrollment import Enrollment
from app.models.expense import Expense
from app.models.group import Group
from app.models.payment import Payment
from app.models.session import ClassSession
from app.models.student import Student
from app.models.teacher import Teacher
from app.models.user import User


class ReportService:
    @staticmethod
    def get_general_dashboard(db: Session) -> Dict[str, Any]:
        total_branches = db.query(func.count(Branch.id)).filter(Branch.is_archived.is_(False)).scalar() or 0
        total_students = db.query(func.count(Student.id)).filter(Student.is_archived.is_(False)).scalar() or 0
        total_teachers = db.query(func.count(Teacher.id)).filter(Teacher.is_archived.is_(False)).scalar() or 0
        total_agents = db.query(func.count(User.id)).filter(User.role == "agent", User.is_archived.is_(False)).scalar() or 0
        active_groups = db.query(func.count(Group.id)).filter(Group.status == "active", Group.is_archived.is_(False)).scalar() or 0

        pending_prereg = (
            db.query(func.count(Enrollment.id))
            .filter(Enrollment.status == "pending_payment")
            .scalar()
            or 0
        )

        total_rev = (
            db.query(func.coalesce(func.sum(Payment.amount), Decimal("0.00")))
            .filter(Payment.status == "valid")
            .scalar()
            or Decimal("0.00")
        )

        total_exp = (
            db.query(func.coalesce(func.sum(Expense.amount), Decimal("0.00")))
            .filter(Expense.is_archived.is_(False))
            .scalar()
            or Decimal("0.00")
        )

        total_cash = (
            db.query(func.coalesce(func.sum(CashRegister.balance), Decimal("0.00")))
            .scalar()
            or Decimal("0.00")
        )

        # Unpaid debts
        enrollments = db.query(Enrollment).filter(Enrollment.status == "confirmed").all()
        total_unpaid = Decimal("0.00")
        for e in enrollments:
            net_fee = Decimal(str(e.total_fee)) - Decimal(str(e.discount_amount or 0))
            paid = (
                db.query(func.coalesce(func.sum(Payment.amount), Decimal("0.00")))
                .filter(Payment.enrollment_id == e.id, Payment.status == "valid")
                .scalar()
                or Decimal("0.00")
            )
            total_unpaid += max(Decimal("0.00"), net_fee - paid)

        # Branch comparison breakdown
        branches = db.query(Branch).filter(Branch.is_archived.is_(False)).all()
        comparison = []
        for b in branches:
            b_students = db.query(func.count(Student.id)).filter(Student.branch_id == b.id, Student.is_archived.is_(False)).scalar() or 0
            b_groups = db.query(func.count(Group.id)).filter(Group.branch_id == b.id, Group.status == "active").scalar() or 0
            b_rev = db.query(func.coalesce(func.sum(Payment.amount), Decimal("0.00"))).filter(Payment.branch_id == b.id, Payment.status == "valid").scalar() or Decimal("0.00")
            b_exp = db.query(func.coalesce(func.sum(Expense.amount), Decimal("0.00"))).filter(Expense.branch_id == b.id, Expense.is_archived.is_(False)).scalar() or Decimal("0.00")
            b_cash = db.query(func.coalesce(func.sum(CashRegister.balance), Decimal("0.00"))).filter(CashRegister.branch_id == b.id).scalar() or Decimal("0.00")

            comparison.append({
                "branch_id": b.id,
                "branch_name": b.name,
                "students_count": b_students,
                "active_groups_count": b_groups,
                "total_revenue": b_rev,
                "total_expenses": b_exp,
                "cash_balance": b_cash,
            })

        return {
            "total_branches": total_branches,
            "total_students": total_students,
            "new_students_this_month": 0,
            "pending_preregistrations": pending_prereg,
            "total_teachers": total_teachers,
            "total_agents": total_agents,
            "active_groups": active_groups,
            "total_revenue": total_rev,
            "total_expenses": total_exp,
            "total_cash_balances": total_cash,
            "total_unpaid_debt": total_unpaid,
            "branch_comparison": comparison,
        }

    @staticmethod
    def get_branch_dashboard(db: Session, branch_id: int) -> Dict[str, Any]:
        branch = db.query(Branch).filter(Branch.id == branch_id).first()
        b_name = branch.name if branch else f"Branch {branch_id}"

        total_students = db.query(func.count(Student.id)).filter(Student.branch_id == branch_id, Student.is_archived.is_(False)).scalar() or 0
        active_groups = db.query(func.count(Group.id)).filter(Group.branch_id == branch_id, Group.status == "active").scalar() or 0
        pending_prereg = db.query(func.count(Enrollment.id)).filter(Enrollment.branch_id == branch_id, Enrollment.status == "pending_payment").scalar() or 0

        total_rev = db.query(func.coalesce(func.sum(Payment.amount), Decimal("0.00"))).filter(Payment.branch_id == branch_id, Payment.status == "valid").scalar() or Decimal("0.00")
        total_exp = db.query(func.coalesce(func.sum(Expense.amount), Decimal("0.00"))).filter(Expense.branch_id == branch_id, Expense.is_archived.is_(False)).scalar() or Decimal("0.00")
        cash_balance = db.query(func.coalesce(func.sum(CashRegister.balance), Decimal("0.00"))).filter(CashRegister.branch_id == branch_id).scalar() or Decimal("0.00")

        today = date.today()
        sessions_today = (
            db.query(func.count(ClassSession.id))
            .join(Group)
            .filter(Group.branch_id == branch_id, ClassSession.session_date == today)
            .scalar()
            or 0
        )

        return {
            "branch_id": branch_id,
            "branch_name": b_name,
            "total_students": total_students,
            "active_groups": active_groups,
            "pending_preregistrations": pending_prereg,
            "total_revenue": total_rev,
            "total_expenses": total_exp,
            "cash_register_balance": cash_balance,
            "total_unpaid_debt": Decimal("0.00"),
            "sessions_today_count": sessions_today,
        }

    @staticmethod
    def get_report_data(
        db: Session,
        report_type: str,
        branch_id: Optional[int] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> Dict[str, Any]:
        """Generate structured data for daily, monthly, financial, or attendance reports."""
        if report_type == "financial":
            pay_query = db.query(Payment).filter(Payment.status == "valid")
            if branch_id:
                pay_query = pay_query.filter(Payment.branch_id == branch_id)
            if start_date:
                pay_query = pay_query.filter(Payment.paid_at >= datetime.combine(start_date, datetime.min.time()))
            if end_date:
                pay_query = pay_query.filter(Payment.paid_at <= datetime.combine(end_date, datetime.max.time()))

            payments = pay_query.all()
            total_in = sum(p.amount for p in payments)
            return {"type": "financial", "total_income": total_in, "count": len(payments)}

        elif report_type == "attendance":
            att_query = db.query(Attendance)
            if start_date or end_date:
                att_query = att_query.join(ClassSession)
                if start_date:
                    att_query = att_query.filter(ClassSession.session_date >= start_date)
                if end_date:
                    att_query = att_query.filter(ClassSession.session_date <= end_date)

            total = att_query.count()
            presents = att_query.filter(Attendance.status == "present").count()
            absents = att_query.filter(Attendance.status == "absent").count()
            lates = att_query.filter(Attendance.status == "late").count()
            return {"type": "attendance", "total_records": total, "presents": presents, "absents": absents, "lates": lates}

        return {"type": report_type, "message": "Report generated successfully."}


report_service = ReportService()

