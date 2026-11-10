from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from app.db.base import Base, TimestampMixin, SoftDeleteMixin


class Course(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "courses"

    id = Column(Integer, primary_key=True, index=True)
    branch_id = Column(Integer, ForeignKey("branches.id", ondelete="RESTRICT"), nullable=False, index=True)
    type = Column(String(50), nullable=False, default="language")  # language / tutoring
    name_ar = Column(String(150), nullable=False)
    name_en = Column(String(150), nullable=False)
    subject = Column(String(100), nullable=True)  # e.g., English, Mathematics, Physics
    description_ar = Column(Text, nullable=True)
    description_en = Column(Text, nullable=True)
    is_published = Column(Boolean, default=True, nullable=False, index=True)

    branch = relationship("Branch")
    levels = relationship("Level", back_populates="course", cascade="all, delete-orphan")

