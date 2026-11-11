from datetime import datetime
from typing import Optional
from pydantic import ConfigDict, BaseModel


class CourseBase(BaseModel):
    branch_id: int
    type: str = "language"  # language / tutoring
    name_ar: str
    name_en: str
    subject: Optional[str] = None
    description_ar: Optional[str] = None
    description_en: Optional[str] = None
    is_published: bool = True


class CourseCreate(CourseBase):
    pass


class CourseUpdate(BaseModel):
    type: Optional[str] = None
    name_ar: Optional[str] = None
    name_en: Optional[str] = None
    subject: Optional[str] = None
    description_ar: Optional[str] = None
    description_en: Optional[str] = None
    is_published: Optional[bool] = None


class CourseResponse(CourseBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

