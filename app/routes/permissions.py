from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.permissions import Action, require_permission
from app.db.session import get_db
from app.schemas.branch import BranchAccessGrantCreate, BranchAccessGrantResponse
from app.schemas.common import StatusResponse
from app.schemas.permission import UserPermissionResponse, UserPermissionsUpdate
from app.services.permission_service import permission_service

router = APIRouter(tags=["Permissions & Grants"])


@router.get("/users/{id}/permissions", response_model=List[UserPermissionResponse])
def get_user_permissions(
    id: int,
    current_user: dict = Depends(require_permission("permissions", Action.VIEW)),
    db: Session = Depends(get_db),
):
    return permission_service.get_user_permissions(db, id)


@router.put("/users/{id}/permissions", response_model=List[UserPermissionResponse])
def update_user_permissions(
    id: int,
    data: UserPermissionsUpdate,
    current_user: dict = Depends(require_permission("permissions", Action.UPDATE)),
    db: Session = Depends(get_db),
):
    return permission_service.update_user_permissions(
        db, id, data.permissions, admin_id=int(current_user["sub"])
    )


@router.post("/branch-access-grants", response_model=BranchAccessGrantResponse)
def grant_branch_access(
    data: BranchAccessGrantCreate,
    current_user: dict = Depends(require_permission("branches", Action.VALIDATE)),
    db: Session = Depends(get_db),
):
    return permission_service.grant_branch_access(db, data, admin_id=int(current_user["sub"]))


@router.delete("/branch-access-grants/{id}", response_model=StatusResponse)
def revoke_branch_access(
    id: int,
    current_user: dict = Depends(require_permission("branches", Action.DELETE_ARCHIVE)),
    db: Session = Depends(get_db),
):
    permission_service.revoke_branch_access(db, id, admin_id=int(current_user["sub"]))
    return StatusResponse(code="SUCCESS", message="Branch access grant revoked successfully.")

