from datetime import datetime
from typing import Optional
from pydantic import ConfigDict, BaseModel, EmailStr


class ParentCreate(BaseModel):
    user_id: int
    full_name: str
    phone: Optional[str] = None
    email: Optional[EmailStr] = None
    address: Optional[str] = None


class ParentUpdate(BaseModel):
    full_name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[EmailStr] = None
    address: Optional[str] = None


class ParentResponse(BaseModel):
    id: int
    user_id: int
    full_name: str
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class StudentParentLinkCreate(BaseModel):
    student_id: int
    relationship_type: str = "guardian"  # father, mother, guardian


class StudentParentLinkResponse(BaseModel):
    id: int
    student_id: int
    parent_id: int
    relationship_type: str
    is_validated: bool
    validated_by: Optional[int] = None
    validated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

