from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr


class ContactMessageCreate(BaseModel):
    branch_id: Optional[int] = None
    name: str
    email: EmailStr
    phone: Optional[str] = None
    message: str


class ContactMessageResponse(ContactMessageCreate):
    id: int
    status: str
    created_at: datetime

    class Config:
        from_attributes = True

