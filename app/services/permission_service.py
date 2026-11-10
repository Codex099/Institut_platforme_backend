from typing import List, Optional
from sqlalchemy.orm import Session
from app.core.exceptions import NotFoundError
from app.models.branch import BranchAccessGrant
from app.models.permission import UserPermission
from app.models.user import User
from app.schemas.branch import BranchAccessGrantCreate
from app.schemas.permission import UserPermissionItem
from app.services.audit_service import audit_service


class PermissionService:
    @staticmethod
    def get_user_permissions(db: Session, user_id: int) -> List[UserPermission]:
        return db.query(UserPermission).filter(UserPermission.user_id == user_id).all()

    @staticmethod
    def update_user_permissions(
        db: Session, user_id: int, permissions: List[UserPermissionItem], admin_id: Optional[int] = None
    ) -> List[UserPermission]:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise NotFoundError(message_key="resource_not_found")

        # Delete existing
        db.query(UserPermission).filter(UserPermission.user_id == user_id).delete()

        new_perms = []
        for p in permissions:
            perm = UserPermission(user_id=user_id, resource=p.resource, action=p.action)
            db.add(perm)
            new_perms.append(perm)

        audit_service.log(
            db=db,
            action="update_permissions",
            entity="User",
            entity_id=user_id,
            user_id=admin_id,
            after_json={"permissions": [{"resource": p.resource, "action": p.action} for p in permissions]},
        )
        db.commit()
        return new_perms

    @staticmethod
    def grant_branch_access(db: Session, grant_data: BranchAccessGrantCreate, admin_id: Optional[int] = None) -> BranchAccessGrant:
        grant = BranchAccessGrant(
            user_id=grant_data.user_id,
            branch_id=grant_data.branch_id,
            granted_by=admin_id,
            expires_at=grant_data.expires_at,
        )
        db.add(grant)
        db.flush()
        audit_service.log(
            db=db,
            action="grant_branch_access",
            entity="BranchAccessGrant",
            entity_id=grant.id,
            user_id=admin_id,
            after_json={"user_id": grant.user_id, "branch_id": grant.branch_id, "expires_at": str(grant.expires_at)},
        )
        db.commit()
        db.refresh(grant)
        return grant

    @staticmethod
    def revoke_branch_access(db: Session, grant_id: int, admin_id: Optional[int] = None) -> None:
        grant = db.query(BranchAccessGrant).filter(BranchAccessGrant.id == grant_id).first()
        if not grant:
            raise NotFoundError(message_key="resource_not_found")

        db.delete(grant)
        audit_service.log(
            db=db,
            action="revoke_branch_access",
            entity="BranchAccessGrant",
            entity_id=grant_id,
            user_id=admin_id,
        )
        db.commit()


permission_service = PermissionService()

