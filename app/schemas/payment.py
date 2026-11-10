from datetime import datetime
from typing import Optional
from pydantic import BaseModel, condecimal


class PaymentCreate(BaseModel):
    enrollment_id: int
    amount: condecimal(max_digits=12, decimal_places=2)
    method: str = "cash"  # cash / transfer / check
    cash_register_id: Optional[int] = None
    notes: Optional[str] = None


class PaymentCancelRequest(BaseModel):
    reason: str


class PaymentResponse(BaseModel):
    id: int
    enrollment_id: int
    branch_id: int
    amount: condecimal(max_digits=12, decimal_places=2)
    method: str
    receipt_number: str
    received_by: int
    paid_at: datetime
    status: str
    cancelled_by: Optional[int] = None
    cancel_reason: Optional[str] = None
    cancelled_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class UnpaidBalanceItem(BaseModel):
    enrollment_id: int
    student_id: int
    student_name: str
    group_name: str
    total_fee: condecimal(max_digits=12, decimal_places=2)
    paid_amount: condecimal(max_digits=12, decimal_places=2)
    remaining_balance: condecimal(max_digits=12, decimal_places=2)
