from sqlalchemy import Column, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import relationship
from app.db.base import Base, TimestampMixin, SoftDeleteMixin


class Level(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "levels"

    id = Column(Integer, primary_key=True, index=True)
    course_id = Column(Integer, ForeignKey("courses.id", ondelete="CASCADE"), nullable=False, index=True)
    name_ar = Column(String(100), nullable=False)
    name_en = Column(String(100), nullable=False)
    price = Column(Numeric(12, 2), nullable=False, default=0.00)
    registration_fee = Column(Numeric(12, 2), nullable=False, default=0.00)
    program_description_ar = Column(Text, nullable=True)
    program_description_en = Column(Text, nullable=True)
    default_capacity = Column(Integer, nullable=True)

    course = relationship("Course", back_populates="levels")
    groups = relationship("Group", back_populates="level", cascade="all, delete-orphan")
