from datetime import datetime, timezone
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from app.db.base import Base, TimestampMixin, SoftDeleteMixin


class Announcement(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "announcements"

    id = Column(Integer, primary_key=True, index=True)
    branch_id = Column(Integer, ForeignKey("branches.id", ondelete="CASCADE"), nullable=True, index=True)  # Null = whole network
    title_ar = Column(String(200), nullable=False)
    title_en = Column(String(200), nullable=False)
    body_ar = Column(Text, nullable=False)
    body_en = Column(Text, nullable=False)
    audience = Column(String(50), default="all", nullable=False)  # all, students, parents, teachers
    is_public = Column(Boolean, default=False, nullable=False, index=True)
    published_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    branch = relationship("Branch")
