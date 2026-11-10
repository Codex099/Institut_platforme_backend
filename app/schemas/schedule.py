from datetime import date, datetime, time
from typing import List, Optional
from pydantic import BaseModel, conint


class ScheduleSlotBase(BaseModel):
    group_id: int
    room_id: int
    teacher_id: int
    weekday: conint(ge=0, le=6)  # 0=Monday ... 6=Sunday
    start_time: time
    end_time: time
    valid_from: Optional[date] = None
    valid_to: Optional[date] = None


class ScheduleSlotCreate(ScheduleSlotBase):
    pass


class ScheduleSlotUpdate(BaseModel):
    room_id: Optional[int] = None
    teacher_id: Optional[int] = None
    weekday: Optional[conint(ge=0, le=6)] = None
    start_time: Optional[time] = None
    end_time: Optional[time] = None
    valid_from: Optional[date] = None
    valid_to: Optional[date] = None


class ScheduleSlotResponse(ScheduleSlotBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class CheckConflictRequest(BaseModel):
    group_id: int
    room_id: int
    teacher_id: int
    weekday: conint(ge=0, le=6)
    start_time: time
    end_time: time
    valid_from: Optional[date] = None
    valid_to: Optional[date] = None


class ConflictItem(BaseModel):
    type: str  # room, teacher, student, closure
    entity_id: Optional[int] = None
    description: str


class CheckConflictResponse(BaseModel):
    has_conflict: bool
    conflicts: List[ConflictItem]

