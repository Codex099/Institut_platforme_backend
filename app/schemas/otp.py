from typing import Optional
from pydantic import BaseModel, EmailStr, Field


class SendOtpRequest(BaseModel):
    email: EmailStr
    purpose: Optional[str] = Field(default="preregistration", description="Objectif du code (ex: preregistration)")


class VerifyOtpRequest(BaseModel):
    email: EmailStr
    otp_code: str = Field(min_length=4, max_length=10, description="Code OTP à 6 chiffres reçu par email")
    purpose: Optional[str] = Field(default="preregistration", description="Objectif du code")


class OtpStatusResponse(BaseModel):
    code: str
    message: str
    email: EmailStr
    is_verified: bool

