from datetime import datetime, timezone
from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import relationship
from app.db.base import Base, TimestampMixin


class Payment(Base, TimestampMixin):
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, index=True)
    enrollment_id = Column(Integer, ForeignKey("enrollments.id", ondelete="RESTRICT"), nullable=False, index=True)
    branch_id = Column(Integer, ForeignKey("branches.id", ondelete="RESTRICT"), nullable=False, index=True)
    amount = Column(Numeric(12, 2), nullable=False)
    method = Column(String(30), default="cash", nullable=False)  # cash / transfer / check
    receipt_number = Column(String(50), nullable=False)
    received_by = Column(Integer, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    paid_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    status = Column(String(30), default="valid", nullable=False, index=True)  # valid / cancelled
    cancelled_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    cancel_reason = Column(Text, nullable=True)
    cancelled_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        UniqueConstraint("branch_id", "receipt_number", name="uq_payment_branch_receipt"),
    )

    enrollment = relationship("Enrollment", back_populates="payments")
    branch = relationship("Branch")
    receiver = relationship("User", foreign_keys=[received_by])
    canceller = relationship("User", foreign_keys=[cancelled_by])
