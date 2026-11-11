from typing import List
from pydantic import ConfigDict, BaseModel


class UserPermissionItem(BaseModel):
    resource: str
    action: str


class UserPermissionsUpdate(BaseModel):
    permissions: List[UserPermissionItem]


class UserPermissionResponse(UserPermissionItem):
    id: int
    user_id: int

    model_config = ConfigDict(from_attributes=True)

