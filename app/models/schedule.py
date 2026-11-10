from sqlalchemy import Column, Date, ForeignKey, Integer, Time
from sqlalchemy.orm import relationship
from app.db.base import Base, TimestampMixin


class ScheduleSlot(Base, TimestampMixin):
    __tablename__ = "schedule_slots"

    id = Column(Integer, primary_key=True, index=True)
    group_id = Column(Integer, ForeignKey("groups.id", ondelete="CASCADE"), nullable=False, index=True)
    room_id = Column(Integer, ForeignKey("rooms.id", ondelete="RESTRICT"), nullable=False, index=True)
    teacher_id = Column(Integer, ForeignKey("teachers.id", ondelete="RESTRICT"), nullable=False, index=True)
    weekday = Column(Integer, nullable=False, index=True)  # 0=Monday ... 6=Sunday
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)
    valid_from = Column(Date, nullable=True)
    valid_to = Column(Date, nullable=True)

    group = relationship("Group", back_populates="schedule_slots")
    room = relationship("Room", back_populates="schedule_slots")
    teacher = relationship("Teacher", back_populates="schedule_slots")
