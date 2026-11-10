from sqlalchemy import Column, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import relationship
from app.db.base import Base, TimestampMixin, SoftDeleteMixin


class Teacher(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "teachers"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True)
    branch_id = Column(Integer, ForeignKey("branches.id", ondelete="RESTRICT"), nullable=False, index=True)
    phone = Column(String(50), nullable=True)
    specialties = Column(String(255), nullable=True)
    pay_mode = Column(String(30), nullable=False, default="hourly")  # hourly / per_session / fixed
    pay_rate = Column(Numeric(12, 2), nullable=False, default=0.00)
    contract_notes = Column(Text, nullable=True)

    user = relationship("User", back_populates="teacher_profile")
    branch = relationship("Branch")
    schedule_slots = relationship("ScheduleSlot", back_populates="teacher")
    sessions = relationship("ClassSession", back_populates="teacher")
    payroll_records = relationship("TeacherPayroll", back_populates="teacher", cascade="all, delete-orphan")

