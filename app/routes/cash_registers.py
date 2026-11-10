from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.branch_scope import BranchScope, get_branch_scope
from app.core.exceptions import NotFoundError
from app.core.permissions import Action, require_permission
from app.db.session import get_db
from app.models.cash_register import CashMovement, CashRegister
from app.schemas.cash_register import CashMovementResponse, CashRegisterCreate, CashRegisterResponse

router = APIRouter(prefix="/cash-registers", tags=["Cash Registers"])


@router.get("", response_model=List[CashRegisterResponse])
def list_cash_registers(
    scope: BranchScope = Depends(get_branch_scope),
    current_user: dict = Depends(require_permission("cash_registers", Action.VIEW)),
    db: Session = Depends(get_db),
):
    query = db.query(CashRegister)
    query = scope.apply_query_filter(query, CashRegister)
    return query.all()


@router.get("/{id}/movements", response_model=List[CashMovementResponse])
def list_cash_movements(
    id: int,
    scope: BranchScope = Depends(get_branch_scope),
    current_user: dict = Depends(require_permission("cash_registers", Action.VIEW)),
    db: Session = Depends(get_db),
):
    reg = db.query(CashRegister).filter(CashRegister.id == id).first()
    if not reg:
        raise NotFoundError(message_key="resource_not_found")
    scope.ensure_access(reg.branch_id)
    return db.query(CashMovement).filter(CashMovement.register_id == id).order_by(CashMovement.created_at.desc()).all()

