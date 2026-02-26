from decimal import Decimal
from sqlalchemy import String, Text, Boolean, Numeric
from sqlalchemy.orm import Mapped, mapped_column
from .db import Base


class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(primary_key=True)

    name: Mapped[str] = mapped_column(String(200), index=True)

    description: Mapped[str] = mapped_column(Text, default="")

    # Use Decimal type for Numeric
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2))

    published: Mapped[bool] = mapped_column(Boolean, default=False)

    image_url: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True
    )