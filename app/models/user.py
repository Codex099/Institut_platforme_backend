from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
from app.core.permissions import Role
from app.db.base import Base, TimestampMixin, SoftDeleteMixin


class User(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(180), unique=True, index=True, nullable=False)
    phone = Column(String(50), nullable=True, index=True)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(150), nullable=False)
    role = Column(String(50), nullable=False, default=Role.STUDENT.value, index=True)
    branch_id = Column(Integer, ForeignKey("branches.id", ondelete="SET NULL"), nullable=True, index=True)
    is_active = Column(Boolean, default=True, nullable=False)
    preferred_lang = Column(String(10), default="en", nullable=False)
    last_login_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    branch = relationship("Branch", foreign_keys=[branch_id])
    permissions = relationship("UserPermission", back_populates="user", cascade="all, delete-orphan")
    branch_grants = relationship("BranchAccessGrant", foreign_keys="[BranchAccessGrant.user_id]", back_populates="user", cascade="all, delete-orphan")
    teacher_profile = relationship("Teacher", back_populates="user", uselist=False, cascade="all, delete-orphan")
    student_profile = relationship("Student", back_populates="user", uselist=False)
    parent_profile = relationship("Parent", back_populates="user", uselist=False, cascade="all, delete-orphan")
