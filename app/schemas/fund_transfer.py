from datetime import datetime
from typing import Optional
from pydantic import BaseModel, condecimal


class FundTransferCreate(BaseModel):
    to_user_id: int
    branch_id: int
    amount: condecimal(max_digits=12, decimal_places=2)
    reason: str
    from_register_id: Optional[int] = None
    to_register_id: Optional[int] = None


class FundTransferContestRequest(BaseModel):
    reason: str


class FundTransferResponse(BaseModel):
    id: int
    reference: str
    branch_id: int
    from_user_id: int
    from_user_name: Optional[str] = None
    to_user_id: int
    to_user_name: Optional[str] = None
    amount: condecimal(max_digits=12, decimal_places=2)
    reason: str
    status: str
    contested_reason: Optional[str] = None
    cancelled_by: Optional[int] = None
    confirmed_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True

