from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
from app.db.base import Base, TimestampMixin, SoftDeleteMixin


class Room(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "rooms"

    id = Column(Integer, primary_key=True, index=True)
    branch_id = Column(Integer, ForeignKey("branches.id", ondelete="RESTRICT"), nullable=False, index=True)
    name = Column(String(100), nullable=False)
    capacity = Column(Integer, nullable=False, default=20)

    branch = relationship("Branch")
    schedule_slots = relationship("ScheduleSlot", back_populates="room")
    sessions = relationship("ClassSession", back_populates="room")

