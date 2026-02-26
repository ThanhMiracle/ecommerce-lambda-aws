from pydantic import BaseModel, Field, ConfigDict


class PaymentCreateIn(BaseModel):
    shipping_address: str = Field(min_length=1)
    phone_number: str = Field(min_length=3)


class PaymentCreateOut(BaseModel):
    ok: bool
    payment_id: int


class PaymentOut(BaseModel):
    id: int
    order_id: int
    user_id: int
    amount: float
    status: str

    model_config = ConfigDict(from_attributes=True)