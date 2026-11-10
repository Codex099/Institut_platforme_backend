from typing import List, Optional
from pydantic import BaseModel, EmailStr


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str


class UserMeResponse(BaseModel):
    id: int
    email: str
    full_name: str
    role: str
    branch_id: Optional[int] = None
    branch_name: Optional[str] = None
    is_active: bool
    preferred_lang: str
    granted_branches: List[int] = []
    permissions: List[dict] = []
