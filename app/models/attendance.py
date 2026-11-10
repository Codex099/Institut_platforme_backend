from datetime import datetime, timezone
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import relationship
from app.db.base import Base, TimestampMixin


class Attendance(Base, TimestampMixin):
    __tablename__ = "attendance"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    student_id = Column(Integer, ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True)
    status = Column(String(20), nullable=False)  # present / absent / late
    method = Column(String(20), default="manual", nullable=False)  # manual (reserved for future QR)
    notes = Column(Text, nullable=True)
    recorded_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    recorded_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    modified_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    modified_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        UniqueConstraint("session_id", "student_id", name="uq_attendance_session_student"),
    )

    session = relationship("ClassSession", back_populates="attendances")
    student = relationship("Student", back_populates="attendance_records")
    recorder = relationship("User", foreign_keys=[recorded_by])
    modifier = relationship("User", foreign_keys=[modified_by])
