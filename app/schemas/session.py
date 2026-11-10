from datetime import date, datetime, time
from typing import List, Optional
from pydantic import BaseModel


class ClassSessionBase(BaseModel):
    group_id: int
    room_id: int
    teacher_id: int
    session_date: date
    start_time: time
    end_time: time
    status: str = "planned"  # planned, held, cancelled, rescheduled


class ClassSessionCreate(ClassSessionBase):
    pass


class ClassSessionUpdate(BaseModel):
    room_id: Optional[int] = None
    teacher_id: Optional[int] = None
    session_date: Optional[date] = None
    start_time: Optional[time] = None
    end_time: Optional[time] = None
    status: Optional[str] = None


class GenerateSessionsRequest(BaseModel):
    group_id: int
    start_date: date
    end_date: date


class GenerateSessionsResponse(BaseModel):
    generated_count: int
    skipped_dates: List[date]
    skipped_reason: str = "Closure days or holidays"


class CancelSessionRequest(BaseModel):
    reason: str


class RescheduleSessionRequest(BaseModel):
    new_date: date
    new_start_time: time
    new_end_time: time
    new_room_id: Optional[int] = None
    new_teacher_id: Optional[int] = None
    reason: str


class ClassSessionResponse(ClassSessionBase):
    id: int
    cancel_reason: Optional[str] = None
    cancelled_by: Optional[int] = None
    cancelled_at: Optional[datetime] = None
    rescheduled_from_session_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

