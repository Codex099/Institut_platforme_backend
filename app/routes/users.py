from typing import List, Optional
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.branch_scope import BranchScope, get_branch_scope
from app.core.permissions import Action, require_permission
from app.db.session import get_db
from app.schemas.common import PaginatedResponse, StatusResponse
from app.schemas.user import UserCreate, UserResetPassword, UserResponse, UserSuspendRequest, UserUpdate
from app.services.user_service import user_service

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("", response_model=PaginatedResponse[UserResponse])
def list_users(
    page: int = 1,
    page_size: int = 20,
    role: Optional[str] = None,
    is_active: Optional[bool] = None,
    scope: BranchScope = Depends(get_branch_scope),
    current_user: dict = Depends(require_permission("users", Action.VIEW)),
    db: Session = Depends(get_db),
):
    skip = (page - 1) * page_size
    target_branch = scope.selected_branch_id if not scope.is_global else None
    users, total = user_service.get_users(
        db=db,
        branch_id=target_branch,
        role=role,
        is_active=is_active,
        skip=skip,
        limit=page_size,
    )
    pages = (total + page_size - 1) // page_size
    return PaginatedResponse(items=users, total=total, page=page, page_size=page_size, pages=pages)


@router.post("", response_model=UserResponse)
def create_user(
    data: UserCreate,
    scope: BranchScope = Depends(get_branch_scope),
    current_user: dict = Depends(require_permission("users", Action.CREATE)),
    db: Session = Depends(get_db),
):
    if data.branch_id:
        scope.ensure_access(data.branch_id)
    return user_service.create_user(db, data, creator_id=int(current_user["sub"]))


@router.get("/{id}", response_model=UserResponse)
def get_user(
    id: int,
    current_user: dict = Depends(require_permission("users", Action.VIEW)),
    db: Session = Depends(get_db),
):
    return user_service.get_by_id(db, id)


@router.put("/{id}", response_model=UserResponse)
def update_user(
    id: int,
    data: UserUpdate,
    scope: BranchScope = Depends(get_branch_scope),
    current_user: dict = Depends(require_permission("users", Action.UPDATE)),
    db: Session = Depends(get_db),
):
    if data.branch_id:
        scope.ensure_access(data.branch_id)
    return user_service.update_user(db, id, data, updater_id=int(current_user["sub"]))


@router.post("/{id}/reset-password", response_model=StatusResponse)
def reset_password(
    id: int,
    data: UserResetPassword,
    current_user: dict = Depends(require_permission("users", Action.UPDATE)),
    db: Session = Depends(get_db),
):
    user_service.reset_password(db, id, data.new_password, actor_id=int(current_user["sub"]))
    return StatusResponse(code="SUCCESS", message="User password reset successfully.")


@router.post("/{id}/suspend", response_model=UserResponse)
def suspend_user(
    id: int,
    data: UserSuspendRequest,
    current_user: dict = Depends(require_permission("users", Action.UPDATE)),
    db: Session = Depends(get_db),
):
    return user_service.suspend_user(db, id, data.is_active, actor_id=int(current_user["sub"]))

