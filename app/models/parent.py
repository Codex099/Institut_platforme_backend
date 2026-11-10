from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import relationship
from app.db.base import Base, TimestampMixin


class Parent(Base, TimestampMixin):
    __tablename__ = "parents"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True)
    full_name = Column(String(150), nullable=False)
    phone = Column(String(50), nullable=True)
    email = Column(String(180), nullable=True)
    address = Column(String(255), nullable=True)

    user = relationship("User", back_populates="parent_profile")
    student_links = relationship("StudentParent", back_populates="parent", cascade="all, delete-orphan")


class StudentParent(Base, TimestampMixin):
    __tablename__ = "student_parents"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True)
    parent_id = Column(Integer, ForeignKey("parents.id", ondelete="CASCADE"), nullable=False, index=True)
    relationship_type = Column(String(50), nullable=False, default="guardian")  # father, mother, guardian
    is_validated = Column(Boolean, default=False, nullable=False)
    validated_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    validated_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        UniqueConstraint("student_id", "parent_id", name="uq_student_parent"),
    )

    student = relationship("Student", back_populates="parent_links")
    parent = relationship("Parent", back_populates="student_links")
    validator = relationship("User", foreign_keys=[validated_by])
