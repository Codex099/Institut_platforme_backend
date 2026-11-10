from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr


class BranchBase(BaseModel):
    name: str
    code: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = "Chlef"
    phone: Optional[str] = None
    email: Optional[EmailStr] = None
    is_active: bool = True
    director_id: Optional[int] = None


class BranchCreate(BranchBase):
    pass


class BranchUpdate(BaseModel):
    name: Optional[str] = None
    code: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[EmailStr] = None
    is_active: Optional[bool] = None
    director_id: Optional[int] = None


class BranchResponse(BranchBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class BranchAccessGrantCreate(BaseModel):
    user_id: int
    branch_id: int
    expires_at: Optional[datetime] = None


class BranchAccessGrantResponse(BaseModel):
    id: int
    user_id: int
    branch_id: int
    granted_by: Optional[int] = None
    expires_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True
