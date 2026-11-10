from sqlalchemy import Column, Date, DateTime, ForeignKey, Integer, String, Text, Time
from sqlalchemy.orm import relationship
from app.db.base import Base, TimestampMixin


class ClassSession(Base, TimestampMixin):
    __tablename__ = "sessions"

    id = Column(Integer, primary_key=True, index=True)
    group_id = Column(Integer, ForeignKey("groups.id", ondelete="CASCADE"), nullable=False, index=True)
    room_id = Column(Integer, ForeignKey("rooms.id", ondelete="RESTRICT"), nullable=False, index=True)
    teacher_id = Column(Integer, ForeignKey("teachers.id", ondelete="RESTRICT"), nullable=False, index=True)
    session_date = Column(Date, nullable=False, index=True)
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)
    status = Column(String(30), default="planned", nullable=False, index=True)  # planned, held, cancelled, rescheduled
    cancel_reason = Column(Text, nullable=True)
    cancelled_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    cancelled_at = Column(DateTime(timezone=True), nullable=True)
    rescheduled_from_session_id = Column(Integer, ForeignKey("sessions.id", ondelete="SET NULL"), nullable=True)

    group = relationship("Group", back_populates="sessions")
    room = relationship("Room", back_populates="sessions")
    teacher = relationship("Teacher", back_populates="sessions")
    cancelled_by_user = relationship("User", foreign_keys=[cancelled_by])
    rescheduled_from = relationship("ClassSession", remote_side=[id], backref="rescheduled_to")
    attendances = relationship("Attendance", back_populates="session", cascade="all, delete-orphan")
