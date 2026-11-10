from sqlalchemy import Column, ForeignKey, Index, Integer, String
from sqlalchemy.orm import relationship
from app.db.base import Base, TimestampMixin, SoftDeleteMixin


class Document(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    owner_type = Column(String(50), nullable=False, index=True)  # student, enrollment, expense, payment
    owner_id = Column(Integer, nullable=False, index=True)
    kind = Column(String(50), nullable=False)  # id, photo, registration, proof, admin, pedagogical
    file_key = Column(String(255), unique=True, nullable=False, index=True)
    original_name = Column(String(255), nullable=False)
    mime_type = Column(String(100), nullable=False)
    file_size = Column(Integer, nullable=False)  # bytes
    uploaded_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    visibility = Column(String(30), default="internal", nullable=False)  # public, internal, confidential

    __table_args__ = (
        Index("ix_documents_owner", "owner_type", "owner_id"),
    )

    uploader = relationship("User", foreign_keys=[uploaded_by])

