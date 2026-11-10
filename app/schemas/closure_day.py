from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel, model_validator


class ClosureDayBase(BaseModel):
    branch_id: Optional[int] = None  # None for whole network
    name_ar: str
    name_en: str
    start_date: date
    end_date: date
    reason: Optional[str] = None

    @model_validator(mode="after")
    def check_dates(self):
        if self.end_date < self.start_date:
            raise ValueError("end_date must be greater than or equal to start_date")
        return self


class ClosureDayCreate(ClosureDayBase):
    pass


class ClosureDayUpdate(BaseModel):
    name_ar: Optional[str] = None
    name_en: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    reason: Optional[str] = None


class ClosureDayResponse(ClosureDayBase):
    id: int
    created_by: Optional[int] = None
    created_at: datetime

    class Config:
        from_attributes = True

