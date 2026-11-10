from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class NotificationResponse(BaseModel):
    id: int
    user_id: int
    type: str
    title: str
    body: str
    data_json: Optional[dict] = None
    read_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True

