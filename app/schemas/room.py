from datetime import datetime
from typing import Optional
from pydantic import ConfigDict, BaseModel, conint


class RoomBase(BaseModel):
    branch_id: int
    name: str
    capacity: conint(ge=1) = 20


class RoomCreate(RoomBase):
    pass


class RoomUpdate(BaseModel):
    name: Optional[str] = None
    capacity: Optional[conint(ge=1)] = None


class RoomResponse(RoomBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

