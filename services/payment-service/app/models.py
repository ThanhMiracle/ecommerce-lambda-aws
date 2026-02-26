from decimal import Decimal
from sqlalchemy import String, Numeric
from sqlalchemy.orm import Mapped, mapped_column
from .db import Base

class Payment(Base):
    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(index=True)
    user_id: Mapped[int] = mapped_column(index=True)

    # money => NUMERIC, not FLOAT
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0.00"))

    status: Mapped[str] = mapped_column(String(50), default="PENDING")  # PENDING | SUCCESS | FAILED