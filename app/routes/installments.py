from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.permissions import Action, require_permission
from app.db.session import get_db
from app.models.installment import Installment
from app.schemas.installment import InstallmentCreate, InstallmentResponse

router = APIRouter(prefix="/installments", tags=["Installments"])


@router.get("", response_model=List[InstallmentResponse])
def list_installments(
    enrollment_id: int,
    current_user: dict = Depends(require_permission("installments", Action.VIEW)),
    db: Session = Depends(get_db),
):
    return db.query(Installment).filter(Installment.enrollment_id == enrollment_id).order_by(Installment.due_date.asc()).all()


@router.post("", response_model=InstallmentResponse)
def create_installment(
    data: InstallmentCreate,
    current_user: dict = Depends(require_permission("installments", Action.CREATE)),
    db: Session = Depends(get_db),
):
    inst = Installment(**data.model_dump())
    db.add(inst)
    db.commit()
    db.refresh(inst)
    return inst

