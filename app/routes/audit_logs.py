from typing import List, Optional
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.permissions import Action, require_permission
from app.db.session import get_db
from app.models.audit_log import AuditLog
from app.schemas.audit_log import AuditLogResponse
from app.schemas.common import PaginatedResponse

router = APIRouter(prefix="/audit-logs", tags=["Audit Logs"])


@router.get("", response_model=PaginatedResponse[AuditLogResponse])
def list_audit_logs(
    page: int = 1,
    page_size: int = 50,
    action: Optional[str] = None,
    entity: Optional[str] = None,
    user_id: Optional[int] = None,
    current_user: dict = Depends(require_permission("audit_logs", Action.VIEW)),
    db: Session = Depends(get_db),
):
    query = db.query(AuditLog)
    if action:
        query = query.filter(AuditLog.action == action)
    if entity:
        query = query.filter(AuditLog.entity == entity)
    if user_id:
        query = query.filter(AuditLog.user_id == user_id)

    total = query.count()
    items = query.order_by(AuditLog.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
    pages = (total + page_size - 1) // page_size

    results = []
    for item in items:
        results.append(
            AuditLogResponse(
                id=item.id,
                user_id=item.user_id,
                user_name=item.user.full_name if item.user else None,
                action=item.action,
                entity=item.entity,
                entity_id=item.entity_id,
                before_json=item.before_json,
                after_json=item.after_json,
                ip_address=item.ip_address,
                created_at=item.created_at,
            )
        )

    return PaginatedResponse(items=results, total=total, page=page, page_size=page_size, pages=pages)

