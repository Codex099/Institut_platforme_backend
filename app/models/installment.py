from sqlalchemy import Column, Date, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import relationship
from app.db.base import Base, TimestampMixin


class Installment(Base, TimestampMixin):
    __tablename__ = "installments"

    id = Column(Integer, primary_key=True, index=True)
    enrollment_id = Column(Integer, ForeignKey("enrollments.id", ondelete="CASCADE"), nullable=False, index=True)
    due_date = Column(Date, nullable=False, index=True)
    amount = Column(Numeric(12, 2), nullable=False)
    status = Column(String(30), default="due", nullable=False, index=True)  # due, paid, late

    enrollment = relationship("Enrollment", back_populates="installments")

