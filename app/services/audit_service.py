from typing import Any, Optional
from sqlalchemy.orm import Session
from app.models.audit_log import AuditLog


class AuditService:
    @staticmethod
    def log(
        db: Session,
        action: str,
        entity: str,
        entity_id: Optional[Any] = None,
        user_id: Optional[int] = None,
        before_json: Optional[dict] = None,
        after_json: Optional[dict] = None,
        ip_address: Optional[str] = None,
    ) -> AuditLog:
        """Create an immutable audit log entry."""
        log_entry = AuditLog(
            user_id=user_id,
            action=action,
            entity=entity,
            entity_id=str(entity_id) if entity_id is not None else None,
            before_json=before_json,
            after_json=after_json,
            ip_address=ip_address,
        )
        db.add(log_entry)
        # We don't commit immediately to allow grouping within the caller transaction
        return log_entry


audit_service = AuditService()

