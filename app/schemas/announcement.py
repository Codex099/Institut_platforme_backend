from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class AnnouncementBase(BaseModel):
    branch_id: Optional[int] = None  # None = network-wide
    title_ar: str
    title_en: str
    body_ar: str
    body_en: str
    audience: str = "all"  # all, students, parents, teachers
    is_public: bool = False


class AnnouncementCreate(AnnouncementBase):
    pass


class AnnouncementUpdate(BaseModel):
    title_ar: Optional[str] = None
    title_en: Optional[str] = None
    body_ar: Optional[str] = None
    body_en: Optional[str] = None
    audience: Optional[str] = None
    is_public: Optional[bool] = None


class AnnouncementResponse(AnnouncementBase):
    id: int
    published_at: datetime
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

