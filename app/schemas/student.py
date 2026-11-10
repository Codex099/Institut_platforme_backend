from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel


class StudentBase(BaseModel):
    branch_id: int
    first_name: str
    last_name: str
    birth_date: Optional[date] = None
    gender: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    status: str = "candidate"


class StudentCreate(StudentBase):
    user_id: Optional[int] = None
    student_number: Optional[str] = None  # auto-generated if omitted


class StudentUpdate(BaseModel):
    branch_id: Optional[int] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    birth_date: Optional[date] = None
    gender: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    status: Optional[str] = None
    photo_document_id: Optional[int] = None


class StudentResponse(StudentBase):
    id: int
    student_number: str
    user_id: Optional[int] = None
    photo_document_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

