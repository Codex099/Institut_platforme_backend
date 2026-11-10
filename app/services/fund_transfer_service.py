from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.exceptions import BadRequestError, ConflictError, NotFoundError, PermissionDeniedError
from app.models.branch import Branch
from app.models.cash_register import CashRegister
from app.models.fund_transfer import FundTransfer
from app.models.user import User
from app.schemas.fund_transfer import FundTransferCreate
from app.services.audit_service import audit_service
from app.services.cash_service import cash_service
from app.services.notification_service import notification_service


class FundTransferService:
    @staticmethod
    def generate_transfer_reference(db: Session, branch_id: int) -> str:
        now = datetime.now(timezone.utc)
        year = now.year
        branch = db.query(Branch).filter(Branch.id == branch_id).first()
        b_code = (branch.code or f"BR{branch_id}").upper()

        prefix = f"TRF-{b_code}-{year}-"
        count = (
            db.query(func.count(FundTransfer.id))
            .filter(FundTransfer.branch_id == branch_id, FundTransfer.reference.like(f"{prefix}%"))
            .scalar()
            or 0
        )
        return f"{prefix}{count + 1:04d}"

    @classmethod
    def create_transfer(
        cls,
        db: Session,
        data: FundTransferCreate,
        sender_id: int,
        ip_address: Optional[str] = None,
    ) -> FundTransfer:
        amount = Decimal(str(data.amount))
        if amount <= 0:
            raise BadRequestError(message_key="validation_error", details="Transfer amount must be positive.")

        recipient = db.query(User).filter(User.id == data.to_user_id).first()
        if not recipient:
            raise NotFoundError(message_key="resource_not_found", details="Recipient user not found.")

        ref = cls.generate_transfer_reference(db, data.branch_id)
        transfer = FundTransfer(
            reference=ref,
            branch_id=data.branch_id,
            from_user_id=sender_id,
            to_user_id=data.to_user_id,
            amount=amount,
            reason=data.reason,
            status="pending",
        )
        db.add(transfer)
        db.flush()

        # Notify recipient
        notification_service.notify_user(
            db=db,
            user_id=data.to_user_id,
            notif_type="fund_transfer_pending",
            title="Incoming Fund Transfer",
            body=f"You have a pending fund transfer of {amount:,.2f} DA (Ref: {ref}) awaiting confirmation.",
            data={"transfer_id": transfer.id, "reference": ref},
        )

        audit_service.log(
            db=db,
            action="create_fund_transfer",
            entity="FundTransfer",
            entity_id=transfer.id,
            user_id=sender_id,
            after_json={"reference": ref, "amount": str(amount), "to_user_id": data.to_user_id},
            ip_address=ip_address,
        )

        db.commit()
        db.refresh(transfer)
        return transfer

    @classmethod
    def confirm_transfer(
        cls,
        db: Session,
        transfer_id: int,
        recipient_id: int,
        from_register_id: Optional[int] = None,
        to_register_id: Optional[int] = None,
        ip_address: Optional[str] = None,
    ) -> FundTransfer:
        """Confirm receipt of funds and synchronously adjust cash registers."""
        now = datetime.now(timezone.utc)
        transfer = db.query(FundTransfer).filter(FundTransfer.id == transfer_id).with_for_update().first()
        if not transfer:
            raise NotFoundError(message_key="transfer_not_found")

        if transfer.status != "pending":
            raise ConflictError(message_key="transfer_status_invalid")

        if transfer.to_user_id != recipient_id:
            raise PermissionDeniedError(message_key="permission_denied", details="Only the designated recipient can confirm this transfer.")

        # Update cash registers
        sender = transfer.sender
        recipient = transfer.recipient
        amount = Decimal(str(transfer.amount))

        sender_reg = (
            db.query(CashRegister).filter(CashRegister.id == from_register_id).first()
            if from_register_id
            else cash_service.get_or_create_user_register(db, transfer.branch_id, sender.id, sender.full_name)
        )
        recipient_reg = (
            db.query(CashRegister).filter(CashRegister.id == to_register_id).first()
            if to_register_id
            else cash_service.get_or_create_user_register(db, transfer.branch_id, recipient.id, recipient.full_name)
        )

        # Money out from sender register
        cash_service.record_movement(
            db=db,
            register_id=sender_reg.id,
            movement_type="out",
            amount=amount,
            source_type="fund_transfer",
            source_id=transfer.id,
            notes=f"Remise de fonds {transfer.reference} vers {recipient.full_name}",
            created_by=recipient_id,
        )

        # Money in to recipient register
        cash_service.record_movement(
            db=db,
            register_id=recipient_reg.id,
            movement_type="in",
            amount=amount,
            source_type="fund_transfer",
            source_id=transfer.id,
            notes=f"Réception de fonds {transfer.reference} de {sender.full_name}",
            created_by=recipient_id,
        )

        transfer.status = "confirmed"
        transfer.confirmed_at = now

        audit_service.log(
            db=db,
            action="confirm_fund_transfer",
            entity="FundTransfer",
            entity_id=transfer.id,
            user_id=recipient_id,
            after_json={"status": "confirmed", "confirmed_at": str(now)},
            ip_address=ip_address,
        )

        notification_service.notify_user(
            db=db,
            user_id=transfer.from_user_id,
            notif_type="fund_transfer_confirmed",
            title="Fund Transfer Confirmed",
            body=f"Your transfer of {amount:,.2f} DA (Ref: {transfer.reference}) has been confirmed.",
            data={"transfer_id": transfer.id, "reference": transfer.reference},
        )

        db.commit()
        db.refresh(transfer)
        return transfer

    @classmethod
    def contest_transfer(
        cls,
        db: Session,
        transfer_id: int,
        reason: str,
        recipient_id: int,
        ip_address: Optional[str] = None,
    ) -> FundTransfer:
        transfer = db.query(FundTransfer).filter(FundTransfer.id == transfer_id).first()
        if not transfer:
            raise NotFoundError(message_key="transfer_not_found")

        if transfer.status != "pending":
            raise ConflictError(message_key="transfer_status_invalid")

        if transfer.to_user_id != recipient_id:
            raise PermissionDeniedError(message_key="permission_denied")

        transfer.status = "contested"
        transfer.contested_reason = reason

        audit_service.log(
            db=db,
            action="contest_fund_transfer",
            entity="FundTransfer",
            entity_id=transfer.id,
            user_id=recipient_id,
            after_json={"status": "contested", "reason": reason},
            ip_address=ip_address,
        )

        notification_service.notify_user(
            db=db,
            user_id=transfer.from_user_id,
            notif_type="fund_transfer_contested",
            title="Fund Transfer Contested",
            body=f"Your transfer {transfer.reference} was contested: {reason}",
            data={"transfer_id": transfer.id, "reason": reason},
        )

        db.commit()
        db.refresh(transfer)
        return transfer

    @classmethod
    def cancel_transfer(
        cls,
        db: Session,
        transfer_id: int,
        canceller_id: int,
        ip_address: Optional[str] = None,
    ) -> FundTransfer:
        now = datetime.now(timezone.utc)
        transfer = db.query(FundTransfer).filter(FundTransfer.id == transfer_id).first()
        if not transfer:
            raise NotFoundError(message_key="transfer_not_found")

        if transfer.status == "confirmed":
            raise BadRequestError(message_key="validation_error", details="Confirmed transfers cannot be deleted or directly cancelled. A counter-transfer is required.")

        transfer.status = "cancelled"
        transfer.cancelled_by = canceller_id
        transfer.cancelled_at = now

        audit_service.log(
            db=db,
            action="cancel_fund_transfer",
            entity="FundTransfer",
            entity_id=transfer.id,
            user_id=canceller_id,
            after_json={"status": "cancelled"},
            ip_address=ip_address,
        )

        db.commit()
        db.refresh(transfer)
        return transfer


fund_transfer_service = FundTransferService()
