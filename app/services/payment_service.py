from datetime import datetime, timezone
from decimal import Decimal
from typing import List, Optional, Tuple
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.exceptions import BadRequestError, ConflictError, NotFoundError
from app.models.cash_register import CashRegister
from app.models.enrollment import Enrollment
from app.models.installment import Installment
from app.models.payment import Payment
from app.schemas.payment import PaymentCreate
from app.services.audit_service import audit_service
from app.services.cash_service import cash_service
from app.services.notification_service import notification_service
from app.services.receipt_service import receipt_service


class PaymentService:
    @classmethod
    def get_enrollment_balance(cls, db: Session, enrollment_id: int) -> Tuple[Decimal, Decimal, Decimal]:
        """Returns (net_total_fee, total_paid, remaining_balance)."""
        enrollment = db.query(Enrollment).filter(Enrollment.id == enrollment_id).first()
        if not enrollment:
            raise NotFoundError(message_key="enrollment_not_found")

        net_fee = Decimal(str(enrollment.total_fee)) - Decimal(str(enrollment.discount_amount or 0))

        valid_paid = (
            db.query(func.coalesce(func.sum(Payment.amount), Decimal("0.00")))
            .filter(Payment.enrollment_id == enrollment_id, Payment.status == "valid")
            .scalar()
            or Decimal("0.00")
        )

        remaining = max(Decimal("0.00"), net_fee - valid_paid)
        return net_fee, valid_paid, remaining

    @classmethod
    def record_payment(
        cls,
        db: Session,
        data: PaymentCreate,
        receiver_id: int,
        receiver_name: str,
        ip_address: Optional[str] = None,
    ) -> Payment:
        now = datetime.now(timezone.utc)
        enrollment = db.query(Enrollment).filter(Enrollment.id == data.enrollment_id).first()
        if not enrollment:
            raise NotFoundError(message_key="enrollment_not_found")

        if enrollment.status == "cancelled":
            raise BadRequestError(message_key="validation_error", details="Cannot record payment on a cancelled enrollment.")

        amount = Decimal(str(data.amount))
        if amount <= 0:
            raise BadRequestError(message_key="validation_error", details="Payment amount must be greater than zero.")

        # Generate sequential branch receipt number
        receipt_num = receipt_service.generate_next_receipt_number(db, enrollment.branch_id)

        payment = Payment(
            enrollment_id=enrollment.id,
            branch_id=enrollment.branch_id,
            amount=amount,
            method=data.method,
            receipt_number=receipt_num,
            received_by=receiver_id,
            paid_at=now,
            status="valid",
        )
        db.add(payment)
        db.flush()

        # Update cash register
        register = None
        if data.cash_register_id:
            register = db.query(CashRegister).filter(CashRegister.id == data.cash_register_id).first()
        if not register:
            register = cash_service.get_or_create_user_register(db, enrollment.branch_id, receiver_id, receiver_name)

        cash_service.record_movement(
            db=db,
            register_id=register.id,
            movement_type="in",
            amount=amount,
            source_type="payment",
            source_id=payment.id,
            notes=f"Paiement reçu {receipt_num} pour dossier {enrollment.reference}",
            created_by=receiver_id,
        )

        # Update pending installments
        cls._reconcile_installments(db, enrollment.id)

        # Audit log
        audit_service.log(
            db=db,
            action="record_payment",
            entity="Payment",
            entity_id=payment.id,
            user_id=receiver_id,
            after_json={"receipt_number": receipt_num, "amount": str(amount), "method": data.method},
            ip_address=ip_address,
        )

        # Notification to student
        if enrollment.student and enrollment.student.user_id:
            notification_service.notify_user(
                db=db,
                user_id=enrollment.student.user_id,
                notif_type="payment_recorded",
                title="Payment Received",
                body=f"Payment of {amount:,.2f} DA received. Receipt: {receipt_num}",
                data={"receipt_number": receipt_num, "amount": str(amount)},
            )

        db.commit()
        db.refresh(payment)
        return payment

    @classmethod
    def cancel_payment(
        cls,
        db: Session,
        payment_id: int,
        reason: str,
        canceller_id: int,
        ip_address: Optional[str] = None,
    ) -> Payment:
        now = datetime.now(timezone.utc)
        payment = db.query(Payment).filter(Payment.id == payment_id).first()
        if not payment:
            raise NotFoundError(message_key="payment_not_found")

        if payment.status == "cancelled":
            raise ConflictError(message_key="payment_already_cancelled")

        payment.status = "cancelled"
        payment.cancelled_by = canceller_id
        payment.cancel_reason = reason
        payment.cancelled_at = now

        # Counter-entry in branch cash register to deduct the cancelled amount
        main_reg = cash_service.get_branch_main_register(db, payment.branch_id)
        cash_service.record_movement(
            db=db,
            register_id=main_reg.id,
            movement_type="out",
            amount=Decimal(str(payment.amount)),
            source_type="payment_cancellation",
            source_id=payment.id,
            notes=f"Contre-passation annulation reçu {payment.receipt_number}: {reason}",
            created_by=canceller_id,
        )

        # Re-reconcile installments
        cls._reconcile_installments(db, payment.enrollment_id)

        audit_service.log(
            db=db,
            action="cancel_payment",
            entity="Payment",
            entity_id=payment.id,
            user_id=canceller_id,
            after_json={"status": "cancelled", "reason": reason},
            ip_address=ip_address,
        )

        db.commit()
        db.refresh(payment)
        return payment

    @classmethod
    def _reconcile_installments(cls, db: Session, enrollment_id: int):
        """Update installment statuses based on cumulative paid amount."""
        _, total_paid, _ = cls.get_enrollment_balance(db, enrollment_id)
        installments = (
            db.query(Installment)
            .filter(Installment.enrollment_id == enrollment_id)
            .order_by(Installment.due_date.asc())
            .all()
        )

        running_paid = total_paid
        for inst in installments:
            inst_amount = Decimal(str(inst.amount))
            if running_paid >= inst_amount:
                inst.status = "paid"
                running_paid -= inst_amount
            else:
                inst.status = "due"


payment_service = PaymentService()

