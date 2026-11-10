from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel


class ImportJobResponse(BaseModel):
    id: int
    type: str
    branch_id: Optional[int] = None
    status: str
    file_key: str
    report_json: Optional[dict] = None
    created_by: Optional[int] = None
    created_at: datetime

    class Config:
        from_attributes = True


class ImportPreviewResponse(BaseModel):
    job_id: int
    total_rows: int
    valid_rows_count: int
    invalid_rows_count: int
    errors: List[dict]
    preview_data: List[dict]

