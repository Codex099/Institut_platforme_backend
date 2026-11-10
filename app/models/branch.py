from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
from app.db.base import Base, TimestampMixin, SoftDeleteMixin


class Branch(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "branches"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(150), nullable=False, unique=True, index=True)
    code = Column(String(20), nullable=True, unique=True)  # e.g., 'CHL' for Chlef
    address = Column(String(255), nullable=True)
    city = Column(String(100), nullable=True, default="Chlef")
    phone = Column(String(50), nullable=True)
    email = Column(String(120), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    director_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Relationships
    director = relationship("User", foreign_keys=[director_id], backref="directed_branch")
    access_grants = relationship("BranchAccessGrant", back_populates="branch", cascade="all, delete-orphan")


class BranchAccessGrant(Base, TimestampMixin):
    __tablename__ = "branch_access_grants"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    branch_id = Column(Integer, ForeignKey("branches.id", ondelete="CASCADE"), nullable=False, index=True)
    granted_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)

    user = relationship("User", foreign_keys=[user_id], back_populates="branch_grants")
    branch = relationship("Branch", back_populates="access_grants")
