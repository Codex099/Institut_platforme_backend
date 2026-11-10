from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel, condecimal


class ExpenseBase(BaseModel):
    branch_id: int
    category: str
    amount: condecimal(max_digits=12, decimal_places=2)
    expense_date: date
    description: str
    receipt_document_id: Optional[int] = None


class ExpenseCreate(ExpenseBase):
    pass


class ExpenseUpdate(BaseModel):
    category: Optional[str] = None
    amount: Optional[condecimal(max_digits=12, decimal_places=2)] = None
    expense_date: Optional[date] = None
    description: Optional[str] = None
    receipt_document_id: Optional[int] = None


class ExpenseResponse(ExpenseBase):
    id: int
    created_by: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
