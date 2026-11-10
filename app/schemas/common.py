from typing import Generic, List, Optional, TypeVar
from pydantic import BaseModel, Field, conint

T = TypeVar("T")


class PaginationParams(BaseModel):
    page: conint(ge=1) = 1
    page_size: conint(ge=1, le=100) = 20


class PaginatedResponse(BaseModel, Generic[T]):
    items: List[T]
    total: int
    page: int
    page_size: int
    pages: int


class StatusResponse(BaseModel):
    code: str = "SUCCESS"
    message: str
    details: Optional[dict] = None

