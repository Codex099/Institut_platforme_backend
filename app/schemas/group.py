from datetime import date, datetime
from typing import Optional
from pydantic import ConfigDict, BaseModel, conint


class GroupBase(BaseModel):
    level_id: int
    branch_id: int
    name: str
    capacity: Optional[conint(ge=1)] = None  # If omitted, cascades from Level or Branch default
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    status: str = "active"  # upcoming, active, completed, closed


class GroupCreate(GroupBase):
    pass


class GroupUpdate(BaseModel):
    name: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    status: Optional[str] = None


class GroupCapacityUpdate(BaseModel):
    capacity: conint(ge=1)
    reason: Optional[str] = None  # Mandatory if setting over-capacity or special context


class GroupAvailabilityResponse(BaseModel):
    group_id: int
    group_name: str
    total_capacity: int
    confirmed_enrollments: int
    active_reservations: int
    available_spots: int
    is_full: bool


class GroupResponse(GroupBase):
    id: int
    capacity: int
    capacity_updated_by: Optional[int] = None
    capacity_updated_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

