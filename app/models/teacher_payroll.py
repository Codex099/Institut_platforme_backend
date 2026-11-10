from sqlalchemy import Column, Date, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import relationship
from app.db.base import Base, TimestampMixin


class TeacherPayroll(Base, TimestampMixin):
    __tablename__ = "teacher_payroll"

    id = Column(Integer, primary_key=True, index=True)
    teacher_id = Column(Integer, ForeignKey("teachers.id", ondelete="RESTRICT"), nullable=False, index=True)
    branch_id = Column(Integer, ForeignKey("branches.id", ondelete="RESTRICT"), nullable=False, index=True)
    period_start = Column(Date, nullable=False, index=True)
    period_end = Column(Date, nullable=False, index=True)
    hours = Column(Numeric(6, 2), nullable=False, default=0.00)
    sessions_count = Column(Integer, nullable=False, default=0)
    amount_due = Column(Numeric(12, 2), nullable=False, default=0.00)
    amount_paid = Column(Numeric(12, 2), nullable=False, default=0.00)
    status = Column(String(30), default="draft", nullable=False, index=True)  # draft, approved, paid
    paid_at = Column(DateTime(timezone=True), nullable=True)
    notes = Column(Text, nullable=True)

    teacher = relationship("Teacher", back_populates="payroll_records")
    branch = relationship("Branch")
