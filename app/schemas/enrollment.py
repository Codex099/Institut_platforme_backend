from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, condecimal, conint


class EnrollmentBase(BaseModel):
    student_id: int
    group_id: int
    branch_id: int
    source: str = "onsite"  # online / onsite
    total_fee: condecimal(max_digits=12, decimal_places=2)
    discount_amount: condecimal(max_digits=12, decimal_places=2) = 0.00
    discount_reason: Optional[str] = None
    allow_over_capacity: bool = False
    over_capacity_reason: Optional[str] = None
    allow_overlap: bool = False  # If true, Director forces enrollment despite schedule overlap


class EnrollmentCreate(EnrollmentBase):
    pass


class ConfirmEnrollmentRequest(BaseModel):
    initial_payment_amount: condecimal(max_digits=12, decimal_places=2)
    payment_method: str = "cash"  # cash, check, transfer
    cash_register_id: Optional[int] = None
    notes: Optional[str] = None


class CancelEnrollmentRequest(BaseModel):
    reason: str


class ExtendReservationRequest(BaseModel):
    additional_hours: conint(ge=1, le=168) = 48  # default +48 hours


class PublicPreregistrationRequest(BaseModel):
    branch_id: int
    group_id: int
    first_name: str
    last_name: str
    birth_date: Optional[date] = None
    gender: Optional[str] = None
    phone: str
    email: Optional[EmailStr] = None
    address: Optional[str] = None
    # Parent details if minor
    parent_full_name: Optional[str] = None
    parent_phone: Optional[str] = None
    parent_relationship: Optional[str] = "guardian"


class EnrollmentResponse(BaseModel):
    id: int
    reference: str
    student_id: int
    group_id: int
    branch_id: int
    source: str
    status: str
    reserved_until: Optional[datetime] = None
    total_fee: condecimal(max_digits=12, decimal_places=2)
    discount_amount: condecimal(max_digits=12, decimal_places=2)
    discount_reason: Optional[str] = None
    created_by: Optional[int] = None
    confirmed_by: Optional[int] = None
    confirmed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

