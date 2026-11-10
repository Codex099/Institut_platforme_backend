from sqlalchemy import Column, Date, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
from app.db.base import Base, TimestampMixin, SoftDeleteMixin


class Group(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "groups"

    id = Column(Integer, primary_key=True, index=True)
    level_id = Column(Integer, ForeignKey("levels.id", ondelete="RESTRICT"), nullable=False, index=True)
    branch_id = Column(Integer, ForeignKey("branches.id", ondelete="RESTRICT"), nullable=False, index=True)
    name = Column(String(100), nullable=False)
    capacity = Column(Integer, nullable=False, default=15)
    capacity_updated_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    capacity_updated_at = Column(DateTime(timezone=True), nullable=True)
    start_date = Column(Date, nullable=True)
    end_date = Column(Date, nullable=True)
    status = Column(String(30), default="active", nullable=False, index=True)  # upcoming, active, completed, closed

    level = relationship("Level", back_populates="groups")
    branch = relationship("Branch")
    capacity_updater = relationship("User", foreign_keys=[capacity_updated_by])
    enrollments = relationship("Enrollment", back_populates="group", cascade="all, delete-orphan")
    schedule_slots = relationship("ScheduleSlot", back_populates="group", cascade="all, delete-orphan")
    sessions = relationship("ClassSession", back_populates="group", cascade="all, delete-orphan")
