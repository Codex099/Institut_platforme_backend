from typing import List
from pydantic import BaseModel


class UserPermissionItem(BaseModel):
    resource: str
    action: str


class UserPermissionsUpdate(BaseModel):
    permissions: List[UserPermissionItem]


class UserPermissionResponse(UserPermissionItem):
    id: int
    user_id: int

    class Config:
        from_attributes = True

