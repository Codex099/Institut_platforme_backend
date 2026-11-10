from sqlalchemy import Column, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import relationship
from app.db.base import Base, TimestampMixin


class CashRegister(Base, TimestampMixin):
    __tablename__ = "cash_registers"

    id = Column(Integer, primary_key=True, index=True)
    branch_id = Column(Integer, ForeignKey("branches.id", ondelete="RESTRICT"), nullable=False, index=True)
    owner_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)  # Null = Branch main vault
    name = Column(String(100), nullable=False)
    balance = Column(Numeric(12, 2), nullable=False, default=0.00)

    branch = relationship("Branch")
    owner = relationship("User", foreign_keys=[owner_user_id])
    movements = relationship("CashMovement", back_populates="register", cascade="all, delete-orphan")


class CashMovement(Base, TimestampMixin):
    __tablename__ = "cash_movements"

    id = Column(Integer, primary_key=True, index=True)
    register_id = Column(Integer, ForeignKey("cash_registers.id", ondelete="CASCADE"), nullable=False, index=True)
    type = Column(String(10), nullable=False)  # in / out
    amount = Column(Numeric(12, 2), nullable=False)
    source_type = Column(String(50), nullable=False)  # payment, transfer, expense, manual_adjustment
    source_id = Column(Integer, nullable=True)
    notes = Column(Text, nullable=True)
    created_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    register = relationship("CashRegister", back_populates="movements")
    creator = relationship("User", foreign_keys=[created_by])

