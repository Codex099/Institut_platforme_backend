from datetime import datetime, timezone
from typing import List, Optional
from fastapi import Depends, Query
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.exceptions import PermissionDeniedError
from app.core.permissions import Role
from app.core.security import get_current_user_payload


class BranchScope:
    def __init__(
        self,
        current_user: dict,
        allowed_branch_ids: List[int],
        is_global: bool = False,
        selected_branch_id: Optional[int] = None,
    ):
        self.current_user = current_user
        self.allowed_branch_ids = allowed_branch_ids
        self.is_global = is_global
        self.selected_branch_id = selected_branch_id

    def ensure_access(self, branch_id: Optional[int]) -> None:
        """Validate if the user is allowed to access/modify data of the given branch_id."""
        if self.is_global:
            return
        if branch_id is None:
            # Non-global users cannot perform branch-agnostic actions
            raise PermissionDeniedError(message_key="branch_access_denied")
        if branch_id not in self.allowed_branch_ids:
            raise PermissionDeniedError(
                message_key="branch_access_denied",
                details={"requested_branch_id": branch_id, "allowed": self.allowed_branch_ids},
            )

    def apply_query_filter(self, query, model):
        """Automatically filter a SQLAlchemy query by branch scope."""
        if not hasattr(model, "branch_id"):
            return query

        if self.is_global:
            if self.selected_branch_id is not None:
                return query.filter(model.branch_id == self.selected_branch_id)
            return query

        if self.selected_branch_id is not None:
            if self.selected_branch_id not in self.allowed_branch_ids:
                raise PermissionDeniedError(message_key="branch_access_denied")
            return query.filter(model.branch_id == self.selected_branch_id)

        # Allow matching any granted branch
        if len(self.allowed_branch_ids) == 1:
            return query.filter(model.branch_id == self.allowed_branch_ids[0])
        elif len(self.allowed_branch_ids) > 1:
            return query.filter(model.branch_id.in_(self.allowed_branch_ids))
        else:
            # No branch access at all -> return empty result
            return query.filter(False)


def get_branch_scope(
    branch_id: Optional[int] = Query(None, description="Filter by branch ID"),
    current_user: dict = Depends(get_current_user_payload),
) -> BranchScope:
    """Dependency that computes allowed branches for the current user."""
    role = current_user.get("role")
    user_branch_id = current_user.get("branch_id")
    grants = current_user.get("granted_branches", [])

    if role == Role.SUPER_ADMIN.value:
        return BranchScope(
            current_user=current_user,
            allowed_branch_ids=[],
            is_global=True,
            selected_branch_id=branch_id,
        )

    allowed = []
    if user_branch_id is not None:
        allowed.append(user_branch_id)
    if grants:
        for g in grants:
            if g not in allowed:
                allowed.append(g)

    if branch_id is not None and branch_id not in allowed:
        raise PermissionDeniedError(
            message_key="branch_access_denied",
            details={"requested_branch_id": branch_id, "allowed": allowed},
        )

    return BranchScope(
        current_user=current_user,
        allowed_branch_ids=allowed,
        is_global=False,
        selected_branch_id=branch_id or (allowed[0] if len(allowed) == 1 else None),
    )
