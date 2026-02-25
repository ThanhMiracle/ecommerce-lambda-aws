from pydantic import BaseModel


class PaymentCreateIn(BaseModel):
    shipping_address: str
    phone_number: str

class PaymentCreateOut(BaseModel):
    ok: bool
    payment_id: int


class PaymentOut(BaseModel):
    id: int
    order_id: int
    user_id: int
    amount: float
    status: str

    class Config:
        from_attributes = True