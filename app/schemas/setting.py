from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class SettingCreateUpdate(BaseModel):
    key: str
    value: str
    branch_id: Optional[int] = None  # None for network-wide


class SettingResponse(SettingCreateUpdate):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

