from typing import List, Optional
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.branch_scope import BranchScope, get_branch_scope
from app.core.permissions import Action, require_permission
from app.db.session import get_db
from app.models.setting import Setting
from app.schemas.setting import SettingCreateUpdate, SettingResponse
from app.services.audit_service import audit_service

router = APIRouter(prefix="/settings", tags=["Settings"])


@router.get("", response_model=List[SettingResponse])
def list_settings(
    scope: BranchScope = Depends(get_branch_scope),
    current_user: dict = Depends(require_permission("settings", Action.VIEW)),
    db: Session = Depends(get_db),
):
    query = db.query(Setting)
    if not scope.is_global:
        query = query.filter((Setting.branch_id == scope.selected_branch_id) | (Setting.branch_id.is_(None)))
    return query.all()


@router.put("", response_model=SettingResponse)
def upsert_setting(
    data: SettingCreateUpdate,
    scope: BranchScope = Depends(get_branch_scope),
    current_user: dict = Depends(require_permission("settings", Action.UPDATE)),
    db: Session = Depends(get_db),
):
    if data.branch_id:
        scope.ensure_access(data.branch_id)

    setting = (
        db.query(Setting)
        .filter(Setting.key == data.key, Setting.branch_id == data.branch_id)
        .first()
    )
    if setting:
        setting.value = data.value
    else:
        setting = Setting(key=data.key, value=data.value, branch_id=data.branch_id)
        db.add(setting)

    audit_service.log(
        db=db,
        action="update_setting",
        entity="Setting",
        entity_id=data.key,
        user_id=int(current_user["sub"]),
        after_json={"key": data.key, "value": data.value, "branch_id": data.branch_id},
    )
    db.commit()
    db.refresh(setting)
    return setting

