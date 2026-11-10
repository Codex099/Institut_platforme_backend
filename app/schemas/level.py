from datetime import datetime
from typing import Optional
from pydantic import BaseModel, condecimal


class LevelBase(BaseModel):
    course_id: int
    name_ar: str
    name_en: str
    price: condecimal(max_digits=12, decimal_places=2)
    registration_fee: condecimal(max_digits=12, decimal_places=2) = 0.00
    program_description_ar: Optional[str] = None
    program_description_en: Optional[str] = None
    default_capacity: Optional[int] = None


class LevelCreate(LevelBase):
    pass


class LevelUpdate(BaseModel):
    name_ar: Optional[str] = None
    name_en: Optional[str] = None
    price: Optional[condecimal(max_digits=12, decimal_places=2)] = None
    registration_fee: Optional[condecimal(max_digits=12, decimal_places=2)] = None
    program_description_ar: Optional[str] = None
    program_description_en: Optional[str] = None
    default_capacity: Optional[int] = None


class LevelResponse(LevelBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

