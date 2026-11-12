from sqlalchemy import Column, Date, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
from app.db.base import Base, TimestampMixin, SoftDeleteMixin


class Student(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "students"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, unique=True)
    branch_id = Column(Integer, ForeignKey("branches.id", ondelete="RESTRICT"), nullable=False, index=True)
    student_number = Column(String(50), unique=True, index=True, nullable=False)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    birth_date = Column(Date, nullable=True)
    gender = Column(String(20), nullable=True)
    phone = Column(String(50), nullable=True)
    email = Column(String(180), nullable=True, index=True)
    address = Column(String(255), nullable=True)
    photo_document_id = Column(Integer, ForeignKey("documents.id", ondelete="SET NULL"), nullable=True)
    status = Column(String(30), default="candidate", nullable=False, index=True)  # candidate / active / archived

    # Relationships
    user = relationship("User", back_populates="student_profile")
    branch = relationship("Branch")
    enrollments = relationship("Enrollment", back_populates="student", cascade="all, delete-orphan")
    parent_links = relationship("StudentParent", back_populates="student", cascade="all, delete-orphan")
    attendance_records = relationship("Attendance", back_populates="student")

