from enum import Enum
from typing import Callable, Dict, List, Set, Union
from fastapi import Depends
from app.core.exceptions import PermissionDeniedError


class Role(str, Enum):
    SUPER_ADMIN = "super_admin"          # Directeur Général
    BRANCH_DIRECTOR = "branch_director"  # Directeur de Branche
    AGENT = "agent"                      # Agent Administratif
    TEACHER = "teacher"                  # Enseignant
    STUDENT = "student"                  # Étudiant
    PARENT = "parent"                    # Parent


class Action(str, Enum):
    VIEW = "view"
    CREATE = "create"
    UPDATE = "update"
    DELETE_ARCHIVE = "delete_archive"
    VALIDATE = "validate"
    EXPORT = "export"
    SET_CAPACITY = "set_capacity"


# Default base permissions for each role
ROLE_PERMISSIONS: Dict[Role, Dict[str, Set[Action]]] = {
    Role.SUPER_ADMIN: {
        # Super admin has all permissions on all resources
        "*": {Action.VIEW, Action.CREATE, Action.UPDATE, Action.DELETE_ARCHIVE, Action.VALIDATE, Action.EXPORT, Action.SET_CAPACITY}
    },
    Role.BRANCH_DIRECTOR: {
        "branches": {Action.VIEW, Action.UPDATE},
        "users": {Action.VIEW, Action.CREATE, Action.UPDATE},
        "students": {Action.VIEW, Action.CREATE, Action.UPDATE, Action.DELETE_ARCHIVE, Action.EXPORT},
        "parents": {Action.VIEW, Action.CREATE, Action.UPDATE, Action.VALIDATE},
        "teachers": {Action.VIEW, Action.CREATE, Action.UPDATE},
        "courses": {Action.VIEW, Action.CREATE, Action.UPDATE},
        "levels": {Action.VIEW, Action.CREATE, Action.UPDATE},
        "groups": {Action.VIEW, Action.CREATE, Action.UPDATE, Action.SET_CAPACITY, Action.EXPORT},
        "rooms": {Action.VIEW, Action.CREATE, Action.UPDATE},
        "schedules": {Action.VIEW, Action.CREATE, Action.UPDATE, Action.DELETE_ARCHIVE},
        "sessions": {Action.VIEW, Action.CREATE, Action.UPDATE, Action.DELETE_ARCHIVE, Action.VALIDATE},
        "closure_days": {Action.VIEW, Action.CREATE, Action.UPDATE, Action.DELETE_ARCHIVE},
        "enrollments": {Action.VIEW, Action.CREATE, Action.UPDATE, Action.VALIDATE, Action.DELETE_ARCHIVE, Action.EXPORT},
        "documents": {Action.VIEW, Action.CREATE, Action.DELETE_ARCHIVE},
        "attendance": {Action.VIEW, Action.CREATE, Action.UPDATE, Action.EXPORT},
        "payments": {Action.VIEW, Action.CREATE, Action.UPDATE, Action.VALIDATE, Action.EXPORT},
        "installments": {Action.VIEW, Action.CREATE, Action.UPDATE},
        "expenses": {Action.VIEW, Action.CREATE, Action.UPDATE},
        "cash_registers": {Action.VIEW, Action.UPDATE},
        "fund_transfers": {Action.VIEW, Action.CREATE, Action.UPDATE, Action.VALIDATE},
        "payroll": {Action.VIEW, Action.CREATE, Action.UPDATE, Action.EXPORT},
        "announcements": {Action.VIEW, Action.CREATE, Action.UPDATE, Action.DELETE_ARCHIVE},
        "notifications": {Action.VIEW, Action.UPDATE},
        "dashboard": {Action.VIEW},
        "reports": {Action.VIEW, Action.EXPORT},
        "imports": {Action.VIEW, Action.CREATE, Action.VALIDATE},
        "exports": {Action.VIEW, Action.EXPORT},
        "audit_logs": {Action.VIEW},
        "settings": {Action.VIEW, Action.UPDATE},
    },
    Role.AGENT: {
        "branches": {Action.VIEW},
        "users": {Action.VIEW},
        "students": {Action.VIEW, Action.CREATE, Action.UPDATE, Action.EXPORT},
        "parents": {Action.VIEW, Action.CREATE, Action.UPDATE},
        "teachers": {Action.VIEW},
        "courses": {Action.VIEW},
        "levels": {Action.VIEW},
        "groups": {Action.VIEW},  # NO set_capacity for agent
        "rooms": {Action.VIEW},
        "schedules": {Action.VIEW},
        "sessions": {Action.VIEW},
        "closure_days": {Action.VIEW},
        "enrollments": {Action.VIEW, Action.CREATE, Action.UPDATE, Action.EXPORT},
        "documents": {Action.VIEW, Action.CREATE},
        "attendance": {Action.VIEW, Action.CREATE, Action.UPDATE},
        "payments": {Action.VIEW, Action.CREATE, Action.EXPORT},
        "installments": {Action.VIEW, Action.CREATE, Action.UPDATE},
        "expenses": {Action.VIEW},
        "cash_registers": {Action.VIEW},
        "fund_transfers": {Action.VIEW, Action.CREATE},  # Can initiate transfer to branch director
        "announcements": {Action.VIEW},
        "notifications": {Action.VIEW, Action.UPDATE},
        "dashboard": {Action.VIEW},
        "reports": {Action.VIEW, Action.EXPORT},
        "imports": {Action.VIEW, Action.CREATE},
        "exports": {Action.VIEW, Action.EXPORT},
        "settings": {Action.VIEW},
    },
    Role.TEACHER: {
        # Strict limitation: ONLY assigned groups and attendance!
        "groups": {Action.VIEW},
        "sessions": {Action.VIEW},
        "attendance": {Action.VIEW, Action.CREATE, Action.UPDATE},
        "notifications": {Action.VIEW, Action.UPDATE},
        "announcements": {Action.VIEW},
    },
    Role.STUDENT: {
        "profile": {Action.VIEW, Action.UPDATE},
        "groups": {Action.VIEW},
        "schedules": {Action.VIEW},
        "sessions": {Action.VIEW},
        "attendance": {Action.VIEW},
        "payments": {Action.VIEW},
        "notifications": {Action.VIEW, Action.UPDATE},
        "announcements": {Action.VIEW},
        "documents": {Action.VIEW},
    },
    Role.PARENT: {
        "profile": {Action.VIEW, Action.UPDATE},
        "children": {Action.VIEW, Action.CREATE},
        "schedules": {Action.VIEW},
        "sessions": {Action.VIEW},
        "attendance": {Action.VIEW},
        "payments": {Action.VIEW},
        "notifications": {Action.VIEW, Action.UPDATE},
        "announcements": {Action.VIEW},
    },
}


def check_role_permission(user_role: str, resource: str, action: Union[Action, str], custom_permissions: List[Dict[str, str]] = None) -> bool:
    """Check if a user role and/or custom user permissions permit the action on the resource."""
    if user_role == Role.SUPER_ADMIN.value:
        return True

    # 1. Check custom explicit user_permissions overrides
    if custom_permissions:
        for perm in custom_permissions:
            perm_res = perm.get("resource")
            perm_act = perm.get("action")
            if (perm_res == resource or perm_res == "*") and (perm_act == action or perm_act == "*"):
                return True

    # 2. Check default role permissions
    try:
        role_enum = Role(user_role)
    except ValueError:
        return False

    role_perms = ROLE_PERMISSIONS.get(role_enum, {})
    if "*" in role_perms:
        return True

    resource_actions = role_perms.get(resource, set())
    act_enum = Action(action) if isinstance(action, str) else action
    return act_enum in resource_actions


def require_permission(resource: str, action: Union[Action, str]):
    """FastAPI Dependency factory to enforce resource and action permissions."""
    from app.core.security import get_current_user_payload

    async def permission_dependency(current_user: dict = Depends(get_current_user_payload)) -> dict:
        user_role = current_user.get("role")
        
        # Enforce strict teacher barrier
        if user_role == Role.TEACHER.value and resource not in ("attendance", "groups", "sessions", "announcements", "notifications"):
            raise PermissionDeniedError(message_key="teacher_forbidden_resource")

        custom_perms = current_user.get("custom_permissions", [])
        has_perm = check_role_permission(user_role, resource, action, custom_perms)
        if not has_perm:
            raise PermissionDeniedError(
                message_key="permission_denied",
                details={"resource": resource, "action": action if isinstance(action, str) else action.value},
            )
        return current_user

    return permission_dependency
