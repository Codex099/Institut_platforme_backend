from decimal import Decimal
from typing import Optional
from sqlalchemy.orm import Session
from app.core.exceptions import BadRequestError, NotFoundError
from app.models.cash_register import CashMovement, CashRegister


class CashService:
    @staticmethod
    def get_or_create_user_register(db: Session, branch_id: int, user_id: int, user_name: str) -> CashRegister:
        register = (
            db.query(CashRegister)
            .filter(CashRegister.branch_id == branch_id, CashRegister.owner_user_id == user_id)
            .first()
        )
        if not register:
            register = CashRegister(
                branch_id=branch_id,
                owner_user_id=user_id,
                name=f"Caisse - {user_name}",
                balance=Decimal("0.00"),
            )
            db.add(register)
            db.flush()
        return register

    @staticmethod
    def get_branch_main_register(db: Session, branch_id: int) -> CashRegister:
        register = (
            db.query(CashRegister)
            .filter(CashRegister.branch_id == branch_id, CashRegister.owner_user_id.is_(None))
            .first()
        )
        if not register:
            register = CashRegister(
                branch_id=branch_id,
                owner_user_id=None,
                name="Caisse Principale de Branche",
                balance=Decimal("0.00"),
            )
            db.add(register)
            db.flush()
        return register

    @classmethod
    def record_movement(
        cls,
        db: Session,
        register_id: int,
        movement_type: str,  # in / out
        amount: Decimal,
        source_type: str,
        source_id: Optional[int] = None,
        notes: Optional[str] = None,
        created_by: Optional[int] = None,
    ) -> CashMovement:
        register = db.query(CashRegister).filter(CashRegister.id == register_id).with_for_update().first()
        if not register:
            raise NotFoundError(message_key="resource_not_found")

        amount = Decimal(str(amount))
        if amount <= 0:
            raise BadRequestError(message_key="validation_error", details="Amount must be positive")

        if movement_type == "out":
            if register.balance < amount:
                raise BadRequestError(
                    message_key="cash_register_insufficient_funds",
                    details={"available_balance": float(register.balance), "requested": float(amount)},
                )
            register.balance -= amount
        elif movement_type == "in":
            register.balance += amount
        else:
            raise BadRequestError(message_key="validation_error", details="Invalid movement type")

        movement = CashMovement(
            register_id=register.id,
            type=movement_type,
            amount=amount,
            source_type=source_type,
            source_id=source_id,
            notes=notes,
            created_by=created_by,
        )
        db.add(movement)
        return movement


cash_service = CashService()

