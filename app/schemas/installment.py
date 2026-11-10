from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel, condecimal


class InstallmentBase(BaseModel):
    enrollment_id: int
    due_date: date
    amount: condecimal(max_digits=12, decimal_places=2)
    status: str = "due"  # due, paid, late


class InstallmentCreate(InstallmentBase):
    pass


class InstallmentUpdate(BaseModel):
    due_date: Optional[date] = None
    amount: Optional[condecimal(max_digits=12, decimal_places=2)] = None
    status: Optional[str] = None


class InstallmentResponse(InstallmentBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

