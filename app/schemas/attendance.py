from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel


class AttendanceRecordItem(BaseModel):
    student_id: int
    status: str  # present / absent / late
    notes: Optional[str] = None


class AttendanceBatchRequest(BaseModel):
    session_id: int
    records: List[AttendanceRecordItem]


class AttendanceUpdate(BaseModel):
    status: str  # present / absent / late
    notes: Optional[str] = None
    reason: Optional[str] = None  # Reason for modification trace


class AttendanceResponse(BaseModel):
    id: int
    session_id: int
    student_id: int
    student_name: Optional[str] = None
    student_number: Optional[str] = None
    status: str
    method: str
    notes: Optional[str] = None
    recorded_by: Optional[int] = None
    recorded_at: datetime
    modified_by: Optional[int] = None
    modified_at: Optional[datetime] = None

    class Config:
        from_attributes = True
