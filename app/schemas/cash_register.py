from datetime import datetime
from typing import Optional
from pydantic import BaseModel, condecimal


class CashRegisterCreate(BaseModel):
    branch_id: int
    owner_user_id: Optional[int] = None  # None for main branch vault
    name: str


class CashRegisterResponse(BaseModel):
    id: int
    branch_id: int
    owner_user_id: Optional[int] = None
    name: str
    balance: condecimal(max_digits=12, decimal_places=2)
    created_at: datetime

    class Config:
        from_attributes = True


class CashMovementResponse(BaseModel):
    id: int
    register_id: int
    type: str  # in / out
    amount: condecimal(max_digits=12, decimal_places=2)
    source_type: str
    source_id: Optional[int] = None
    notes: Optional[str] = None
    created_by: Optional[int] = None
    created_at: datetime

    class Config:
        from_attributes = True

