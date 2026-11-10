from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel, condecimal


class TeacherPayrollCalculateRequest(BaseModel):
    teacher_id: int
    period_start: date
    period_end: date


class TeacherPayrollPayRequest(BaseModel):
    cash_register_id: Optional[int] = None
    notes: Optional[str] = None


class TeacherPayrollResponse(BaseModel):
    id: int
    teacher_id: int
    teacher_name: Optional[str] = None
    branch_id: int
    period_start: date
    period_end: date
    hours: condecimal(max_digits=6, decimal_places=2)
    sessions_count: int
    amount_due: condecimal(max_digits=12, decimal_places=2)
    amount_paid: condecimal(max_digits=12, decimal_places=2)
    status: str
    paid_at: Optional[datetime] = None
    notes: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True

