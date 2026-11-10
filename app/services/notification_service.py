from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session
from app.models.notification import Notification


class NotificationService:
    @staticmethod
    def notify_user(
        db: Session,
        user_id: int,
        notif_type: str,
        title: str,
        body: str,
        data: Optional[Dict[str, Any]] = None,
    ) -> Notification:
        """Send notification to a specific user."""
        notif = Notification(
            user_id=user_id,
            type=notif_type,
            title=title,
            body=body,
            data_json=data or {},
        )
        db.add(notif)
        return notif

    @staticmethod
    def notify_multiple_users(
        db: Session,
        user_ids: List[int],
        notif_type: str,
        title: str,
        body: str,
        data: Optional[Dict[str, Any]] = None,
    ) -> List[Notification]:
        """Send notification to multiple users simultaneously."""
        notifications = []
        for uid in set(user_ids):
            if uid:
                notif = Notification(
                    user_id=uid,
                    type=notif_type,
                    title=title,
                    body=body,
                    data_json=data or {},
                )
                db.add(notif)
                notifications.append(notif)
        return notifications


notification_service = NotificationService()

