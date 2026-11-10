from sqlalchemy import Column, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import relationship
from app.db.base import Base, TimestampMixin


class UserPermission(Base, TimestampMixin):
    __tablename__ = "user_permissions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    resource = Column(String(50), nullable=False)
    action = Column(String(50), nullable=False)

    __table_args__ = (
        UniqueConstraint("user_id", "resource", "action", name="uq_user_permission"),
    )

    user = relationship("User", back_populates="permissions")
