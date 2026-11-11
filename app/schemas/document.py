from datetime import datetime
from typing import Optional
from pydantic import ConfigDict, BaseModel


class DocumentResponse(BaseModel):
    id: int
    owner_type: str
    owner_id: int
    kind: str
    file_key: str
    original_name: str
    mime_type: str
    file_size: int
    uploaded_by: Optional[int] = None
    visibility: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

