from datetime import datetime, timezone
from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.core.security import get_current_user_payload
from app.db.session import get_db
from app.models.notification import Notification
from app.schemas.common import StatusResponse
from app.schemas.notification import NotificationResponse

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.get("", response_model=List[NotificationResponse])
def get_my_notifications(
    unread_only: bool = False,
    current_user: dict = Depends(get_current_user_payload),
    db: Session = Depends(get_db),
):
    user_id = int(current_user["sub"])
    query = db.query(Notification).filter(Notification.user_id == user_id)
    if unread_only:
        query = query.filter(Notification.read_at.is_(None))
    return query.order_by(Notification.created_at.desc()).limit(50).all()


@router.post("/{id}/read", response_model=StatusResponse)
def mark_notification_read(
    id: int,
    current_user: dict = Depends(get_current_user_payload),
    db: Session = Depends(get_db),
):
    user_id = int(current_user["sub"])
    notif = db.query(Notification).filter(Notification.id == id, Notification.user_id == user_id).first()
    if not notif:
        raise NotFoundError(message_key="resource_not_found")

    notif.read_at = datetime.now(timezone.utc)
    db.commit()
    return StatusResponse(code="SUCCESS", message="Notification marked as read.")


@router.post("/read-all", response_model=StatusResponse)
def mark_all_notifications_read(
    current_user: dict = Depends(get_current_user_payload),
    db: Session = Depends(get_db),
):
    user_id = int(current_user["sub"])
    db.query(Notification).filter(Notification.user_id == user_id, Notification.read_at.is_(None)).update(
        {"read_at": datetime.now(timezone.utc)}
    )
    db.commit()
    return StatusResponse(code="SUCCESS", message="All notifications marked as read.")

