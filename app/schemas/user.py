from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr


class UserBase(BaseModel):
    email: EmailStr
    phone: Optional[str] = None
    full_name: str
    role: str
    branch_id: Optional[int] = None
    preferred_lang: str = "en"
    is_active: bool = True


class UserCreate(UserBase):
    password: str


class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    full_name: Optional[str] = None
    role: Optional[str] = None
    branch_id: Optional[int] = None
    preferred_lang: Optional[str] = None
    is_active: Optional[bool] = None


class UserResetPassword(BaseModel):
    new_password: str


class UserSuspendRequest(BaseModel):
    is_active: bool


class UserResponse(UserBase):
    id: int
    last_login_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True

