from datetime import datetime, timezone
from typing import Dict, Optional
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import AuthenticationError, BadRequestError
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    revoke_token,
    verify_password,
)
from app.models.branch import BranchAccessGrant
from app.models.permission import UserPermission
from app.models.user import User
from app.services.audit_service import audit_service


class AuthService:
    @staticmethod
    def authenticate_user(db: Session, email: str, password: str, ip_address: Optional[str] = None) -> User:
        """Authenticate user credentials and update last login."""
        user = db.query(User).filter(User.email == email.lower().strip(), User.is_archived.is_(False)).first()
        if not user or not verify_password(password, user.password_hash):
            raise AuthenticationError(message_key="auth_invalid_credentials")

        if not user.is_active:
            raise AuthenticationError(message_key="auth_inactive_account")

        user.last_login_at = datetime.now(timezone.utc)
        audit_service.log(
            db=db,
            action="login",
            entity="User",
            entity_id=user.id,
            user_id=user.id,
            ip_address=ip_address,
        )
        db.commit()
        db.refresh(user)
        return user

    @staticmethod
    def get_user_grants_and_perms(db: Session, user: User) -> tuple:
        """Fetch active branch grants and permissions for user."""
        now = datetime.now(timezone.utc)
        grants = (
            db.query(BranchAccessGrant.branch_id)
            .filter(
                BranchAccessGrant.user_id == user.id,
                (BranchAccessGrant.expires_at.is_(None) | (BranchAccessGrant.expires_at > now)),
            )
            .all()
        )
        granted_branches = [g[0] for g in grants]

        perms = db.query(UserPermission).filter(UserPermission.user_id == user.id).all()
        custom_perms = [{"resource": p.resource, "action": p.action} for p in perms]

        return granted_branches, custom_perms

    @classmethod
    def generate_tokens(cls, db: Session, user: User) -> Dict[str, str]:
        """Create access and refresh tokens embedding branch and grant claims."""
        granted_branches, custom_perms = cls.get_user_grants_and_perms(db, user)
        extra = {
            "granted_branches": granted_branches,
            "custom_permissions": custom_perms,
        }
        access_token = create_access_token(
            subject=str(user.id),
            role=user.role,
            branch_id=user.branch_id,
            extra_claims=extra,
        )
        refresh_token = create_refresh_token(subject=str(user.id))
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        }

    @classmethod
    def refresh_access_token(cls, db: Session, refresh_token: str) -> Dict[str, str]:
        """Validate refresh token and issue new token pair."""
        payload = decode_token(refresh_token, is_refresh=True)
        user_id = int(payload.get("sub"))
        user = db.query(User).filter(User.id == user_id, User.is_archived.is_(False)).first()
        if not user or not user.is_active:
            raise AuthenticationError(message_key="auth_inactive_account")

        # Rotate refresh token
        revoke_token(refresh_token)
        return cls.generate_tokens(db, user)

    @staticmethod
    def logout(refresh_token: str) -> None:
        """Revoke refresh token on logout."""
        revoke_token(refresh_token)

    @staticmethod
    def change_password(db: Session, user_id: int, old_password: str, new_password: str) -> None:
        """Change user password after verifying old password."""
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise BadRequestError(message_key="resource_not_found")
        if not verify_password(old_password, user.password_hash):
            raise BadRequestError(message_key="auth_invalid_credentials")
        if len(new_password) < 6:
            raise BadRequestError(message_key="validation_error", details="Password too short")

        user.password_hash = hash_password(new_password)
        audit_service.log(
            db=db,
            action="change_password",
            entity="User",
            entity_id=user.id,
            user_id=user.id,
        )
        db.commit()


auth_service = AuthService()

