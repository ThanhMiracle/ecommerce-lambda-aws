from sqlalchemy import String, Float, Integer
from sqlalchemy.orm import Mapped, mapped_column
from .db import Base

class Payment(Base):
    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(index=True)
    user_id: Mapped[int] = mapped_column(index=True)
    amount: Mapped[float] = mapped_column(Float)
    status: Mapped[str] = mapped_column(String(50))  # PENDING | SUCCESS | FAILED