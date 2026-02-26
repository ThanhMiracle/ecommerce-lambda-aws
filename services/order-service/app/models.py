from decimal import Decimal
from sqlalchemy import String, Numeric, ForeignKey, Integer, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .db import Base


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(index=True)
    user_email: Mapped[str] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(50), default="CREATED")
    total: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0.00"))

    items: Mapped[list["OrderItem"]] = relationship(
        back_populates="order",
        cascade="all, delete-orphan",
    )


class OrderItem(Base):
    __tablename__ = "order_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), index=True)
    product_id: Mapped[int] = mapped_column(Integer)
    qty: Mapped[int] = mapped_column(Integer, default=1)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0.00"))

    order: Mapped["Order"] = relationship(back_populates="items")