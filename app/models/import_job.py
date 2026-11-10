from sqlalchemy import Column, ForeignKey, Integer, JSON, String
from sqlalchemy.orm import relationship
from app.db.base import Base, TimestampMixin


class ImportJob(Base, TimestampMixin):
    __tablename__ = "import_jobs"

    id = Column(Integer, primary_key=True, index=True)
    type = Column(String(50), nullable=False)  # students, courses, groups, attendance, etc.
    branch_id = Column(Integer, ForeignKey("branches.id", ondelete="CASCADE"), nullable=True, index=True)
    status = Column(String(30), default="uploaded", nullable=False, index=True)  # uploaded, validated, previewed, committed, failed
    file_key = Column(String(255), nullable=False)
    report_json = Column(JSON, nullable=True)  # { total_rows: 100, valid: 95, invalid: 5, errors: [...], preview_sample: [...] }
    created_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    branch = relationship("Branch")
    creator = relationship("User", foreign_keys=[created_by])
