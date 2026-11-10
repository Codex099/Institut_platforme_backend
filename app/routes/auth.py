from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.orm import Session

from app.core.security import get_current_user_payload
from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import (
    ChangePasswordRequest,
    LoginRequest,
    RefreshTokenRequest,
    TokenResponse,
    UserMeResponse,
)
from app.schemas.common import StatusResponse
from app.services.auth_service import auth_service

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/login", response_model=TokenResponse)
def login(data: LoginRequest, request: Request, db: Session = Depends(get_db)):
    ip = request.client.host if request.client else None
    user = auth_service.authenticate_user(db, data.email, data.password, ip_address=ip)
    return auth_service.generate_tokens(db, user)


@router.post("/refresh", response_model=TokenResponse)
def refresh_token(data: RefreshTokenRequest, db: Session = Depends(get_db)):
    return auth_service.refresh_access_token(db, data.refresh_token)


@router.post("/logout", response_model=StatusResponse)
def logout(data: RefreshTokenRequest):
    auth_service.logout(data.refresh_token)
    return StatusResponse(code="SUCCESS", message="Logged out successfully.")


@router.get("/me", response_model=UserMeResponse)
def get_me(current_user: dict = Depends(get_current_user_payload), db: Session = Depends(get_db)):
    user_id = int(current_user["sub"])
    user = db.query(User).filter(User.id == user_id).first()
    granted_branches, custom_perms = auth_service.get_user_grants_and_perms(db, user)

    return UserMeResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        branch_id=user.branch_id,
        branch_name=user.branch.name if user.branch else None,
        is_active=user.is_active,
        preferred_lang=user.preferred_lang,
        granted_branches=granted_branches,
        permissions=custom_perms,
    )


@router.post("/change-password", response_model=StatusResponse)
def change_password(
    data: ChangePasswordRequest,
    current_user: dict = Depends(get_current_user_payload),
    db: Session = Depends(get_db),
):
    user_id = int(current_user["sub"])
    auth_service.change_password(db, user_id, data.old_password, data.new_password)
    return StatusResponse(code="SUCCESS", message="Password updated successfully.")

