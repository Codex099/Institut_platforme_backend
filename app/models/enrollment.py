from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Index, Integer, Numeric, String, Text
from sqlalchemy.orm import relationship
from app.db.base import Base, TimestampMixin, SoftDeleteMixin


class Enrollment(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "enrollments"

    id = Column(Integer, primary_key=True, index=True)
    reference = Column(String(50), unique=True, index=True, nullable=False)
    student_id = Column(Integer, ForeignKey("students.id", ondelete="RESTRICT"), nullable=False, index=True)
    group_id = Column(Integer, ForeignKey("groups.id", ondelete="RESTRICT"), nullable=False, index=True)
    branch_id = Column(Integer, ForeignKey("branches.id", ondelete="RESTRICT"), nullable=False, index=True)
    source = Column(String(20), default="onsite", nullable=False)  # online / onsite
    status = Column(String(30), default="pending_payment", nullable=False, index=True)  # pending_payment, confirmed, expired, cancelled
    reserved_until = Column(DateTime(timezone=True), nullable=True, index=True)
    total_fee = Column(Numeric(12, 2), nullable=False, default=0.00)
    discount_amount = Column(Numeric(12, 2), nullable=False, default=0.00)
    discount_reason = Column(Text, nullable=True)
    allow_over_capacity = Column(Boolean, default=False, nullable=False)
    over_capacity_reason = Column(Text, nullable=True)
    created_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    confirmed_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    confirmed_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("ix_enrollments_group_status", "group_id", "status"),
    )

    student = relationship("Student", back_populates="enrollments")
    group = relationship("Group", back_populates="enrollments")
    branch = relationship("Branch")
    creator = relationship("User", foreign_keys=[created_by])
    confirmer = relationship("User", foreign_keys=[confirmed_by])
    payments = relationship("Payment", back_populates="enrollment", cascade="all, delete-orphan")
    installments = relationship("Installment", back_populates="enrollment", cascade="all, delete-orphan")
