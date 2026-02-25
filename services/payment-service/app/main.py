import os
import httpx
from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from fastapi.middleware.cors import CORSMiddleware
from typing import List

from .db import Base, engine, SessionLocal, init_schema
from .models import Payment
from .schemas import PaymentCreateOut, PaymentOut, PaymentCreateIn
from shared.security import require_user
from shared.events import publish


RABBITMQ_URL = os.getenv("RABBITMQ_URL", "")
ORDER_URL_INTERNAL = os.getenv("ORDER_URL_INTERNAL", "http://order:8000")
ORDER_MARK_PAID_PATH = os.getenv("ORDER_MARK_PAID_PATH", "")

app = FastAPI(title="payment-service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# -------------------------
# DB dependency
# -------------------------
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# -------------------------
# Startup
# -------------------------
@app.on_event("startup")
def startup():
    init_schema()
    Base.metadata.create_all(bind=engine)


# -------------------------
# Helper: safely extract token
# -------------------------
def extract_token(claims: dict) -> str:
    # try multiple common keys
    return (
        claims.get("raw_token")
        or claims.get("token")
        or claims.get("access_token")
        or ""
    )


# -------------------------
# Helper: fetch order
# -------------------------
async def fetch_order(order_id: int, token: str) -> dict:
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.get(
                f"{ORDER_URL_INTERNAL}/orders/{order_id}",
                headers=headers,
            )
    except httpx.RequestError as e:
        # log real error
        print("Order fetch RequestError:", repr(e))
        raise HTTPException(503, "Order service unavailable")

    if r.status_code in (401, 403):
        raise HTTPException(401, "Unauthorized to access order")

    if r.status_code != 200:
        raise HTTPException(400, "Order not found")

    return r.json()


# -------------------------
# Helper: mark order paid (optional)
# -------------------------
async def mark_order_paid_if_supported(order_id: int, token: str) -> None:
    if not ORDER_MARK_PAID_PATH:
        return

    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    url = f"{ORDER_URL_INTERNAL}{ORDER_MARK_PAID_PATH.format(order_id=order_id)}"

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.post(url, headers=headers)

            # fallback to PATCH if needed
            if r.status_code in (404, 405):
                await client.patch(
                    f"{ORDER_URL_INTERNAL}/orders/{order_id}",
                    json={"status": "PAID"},
                    headers=headers,
                )
    except httpx.RequestError as e:
        print("Mark order paid failed:", repr(e))
        # do not fail payment


# -------------------------
# Create payment
# -------------------------
@app.post("/payments/{order_id}", response_model=PaymentCreateOut)
async def pay(
    order_id: int,
    payload: PaymentCreateIn,
    claims: dict = Depends(require_user),
    db: Session = Depends(get_db),
):
    user_id = int(claims["sub"])
    token = extract_token(claims)

    # Idempotency check
    existing = (
        db.query(Payment)
        .filter(Payment.order_id == order_id, Payment.user_id == user_id)
        .first()
    )

    if existing:
        if existing.status == "SUCCESS":
            return PaymentCreateOut(ok=True, payment_id=existing.id)
        raise HTTPException(400, "Payment already attempted")

    # Validate order
    order = await fetch_order(order_id, token)

    if order.get("status") != "CREATED":
        raise HTTPException(
            400, f"Cannot pay order in status {order.get('status')}"
        )

    # Create payment
    try:
        payment = Payment(
            order_id=order_id,
            user_id=user_id,
            amount=order["total"],
            status="SUCCESS",
        )
        db.add(payment)
        db.commit()
        db.refresh(payment)

    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(500, "Failed to create payment")

    # Publish event
    if RABBITMQ_URL:
        publish(
            RABBITMQ_URL,
            "payment.succeeded",
            {
                "order_id": order_id,
                "user_id": user_id,
                "amount": order["total"],
                "shipping_address": payload.shipping_address,
                "phone_number": payload.phone_number,
            },
        )

    # Best-effort mark order as paid
    await mark_order_paid_if_supported(order_id, token)

    return PaymentCreateOut(ok=True, payment_id=payment.id)


# -------------------------
# Get payment
# -------------------------
@app.get("/payments/{payment_id}", response_model=PaymentOut)
def get_payment(
    payment_id: int,
    claims: dict = Depends(require_user),
    db: Session = Depends(get_db),
):
    user_id = int(claims["sub"])

    payment = (
        db.query(Payment)
        .filter(Payment.id == payment_id, Payment.user_id == user_id)
        .first()
    )

    if not payment:
        raise HTTPException(404, "Payment not found")

    return payment


# -------------------------
# List payments
# -------------------------
@app.get("/payments", response_model=List[PaymentOut])
def list_my_payments(
    claims: dict = Depends(require_user),
    db: Session = Depends(get_db),
):
    user_id = int(claims["sub"])

    payments = (
        db.query(Payment)
        .filter(Payment.user_id == user_id)
        .order_by(Payment.id.desc())
        .all()
    )

    return payments


# -------------------------
# Health
# -------------------------
@app.get("/health")
def health():
    return {"ok": True}