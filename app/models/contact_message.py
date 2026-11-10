from sqlalchemy import Column, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from app.db.base import Base, TimestampMixin


class ContactMessage(Base, TimestampMixin):
    __tablename__ = "contact_messages"

    id = Column(Integer, primary_key=True, index=True)
    branch_id = Column(Integer, ForeignKey("branches.id", ondelete="SET NULL"), nullable=True, index=True)
    name = Column(String(100), nullable=False)
    email = Column(String(180), nullable=False)
    phone = Column(String(50), nullable=True)
    message = Column(Text, nullable=False)
    status = Column(String(30), default="new", nullable=False, index=True)  # new, read, resolved

    branch = relationship("Branch")
