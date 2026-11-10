from sqlalchemy import Column, DateTime, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import relationship
from app.db.base import Base, TimestampMixin


class Notification(Base, TimestampMixin):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    type = Column(String(50), nullable=False)  # preregistration, payment, attendance, session_cancel, session_reschedule, reminder, alert
    title = Column(String(200), nullable=False)
    body = Column(Text, nullable=False)
    data_json = Column(JSON, nullable=True)
    read_at = Column(DateTime(timezone=True), nullable=True, index=True)

    user = relationship("User")
