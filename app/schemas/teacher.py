from datetime import datetime
from typing import Optional
from pydantic import ConfigDict, BaseModel, condecimal


class TeacherBase(BaseModel):
    branch_id: int
    phone: Optional[str] = None
    specialties: Optional[str] = None
    pay_mode: str = "hourly"  # hourly / per_session / fixed
    pay_rate: condecimal(max_digits=12, decimal_places=2) = 0.00
    contract_notes: Optional[str] = None


class TeacherCreate(TeacherBase):
    user_id: int


class TeacherUpdate(BaseModel):
    branch_id: Optional[int] = None
    phone: Optional[str] = None
    specialties: Optional[str] = None
    pay_mode: Optional[str] = None
    pay_rate: Optional[condecimal(max_digits=12, decimal_places=2)] = None
    contract_notes: Optional[str] = None


class TeacherResponse(TeacherBase):
    id: int
    user_id: int
    user_full_name: Optional[str] = None
    user_email: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

