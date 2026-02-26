import os
from contextlib import asynccontextmanager
from typing import List

import httpx
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from .db import SessionLocal
from .models import Payment
from .schemas import PaymentCreateOut, PaymentOut, PaymentCreateIn
from shared.security import require_user
from shared.events import publish

ORDER_URL_INTERNAL = os.getenv("ORDER_URL_INTERNAL", "http://order:8000").rstrip("/")
ORDER_MARK_PAID_PATH = os.getenv("ORDER_MARK_PAID_PATH", "")

_http_client: httpx.AsyncClient | None = None


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Keep cold start lightweight for Lambda.
    Run schema creation/migrations at deploy-time, not here.
    """
    global _http_client
    _http_client = httpx.AsyncClient(timeout=5.0)
    yield
    try:
        if _http_client:
            await _http_client.aclose()
    except Exception:
        pass


app = FastAPI(title="payment-service", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten in prod
    allow_methods=["*"],
    allow_headers=["*"],
)


def extract_token(claims: dict) -> str:
    return claims.get("raw_token") or claims.get("token") or claims.get("access_token") or ""


async def fetch_order(order_id: int, token: str) -> dict:
    global _http_client
    if _http_client is None:
        _http_client = httpx.AsyncClient(timeout=5.0)

    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    try:
        r = await _http_client.get(
            f"{ORDER_URL_INTERNAL}/orders/{order_id}",
            headers=headers,
        )
    except httpx.TimeoutException:
        raise HTTPException(status_code=503, detail="Order service timeout")
    except httpx.RequestError:
        raise HTTPException(status_code=503, detail="Order service unavailable")

    if r.status_code in (401, 403):
        raise HTTPException(status_code=401, detail="Unauthorized to access order")

    if r.status_code != 200:
        raise HTTPException(status_code=400, detail="Order not found")

    return r.json()


async def mark_order_paid_if_supported(order_id: int, token: str) -> None:
    if not ORDER_MARK_PAID_PATH:
        return

    global _http_client
    if _http_client is None:
        _http_client = httpx.AsyncClient(timeout=5.0)

    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    url = f"{ORDER_URL_INTERNAL}{ORDER_MARK_PAID_PATH.format(order_id=order_id)}"

    try:
        r = await _http_client.post(url, headers=headers)
        if r.status_code in (404, 405):
            await _http_client.patch(
                f"{ORDER_URL_INTERNAL}/orders/{order_id}",
                json={"status": "PAID"},
                headers=headers,
            )
    except httpx.RequestError:
        # best-effort; don't fail payment
        return


@app.post("/payments/{order_id}", response_model=PaymentCreateOut)
async def pay(
    order_id: int,
    payload: PaymentCreateIn,
    claims: dict = Depends(require_user),
    db: Session = Depends(get_db),
):
    user_id = int(claims["sub"])
    token = extract_token(claims)

    existing = (
        db.query(Payment)
        .filter(Payment.order_id == order_id, Payment.user_id == user_id)
        .first()
    )
    if existing:
        if existing.status == "SUCCESS":
            return PaymentCreateOut(ok=True, payment_id=existing.id)
        raise HTTPException(status_code=400, detail="Payment already attempted")

    order = await fetch_order(order_id, token)
    if order.get("status") != "CREATED":
        raise HTTPException(status_code=400, detail=f"Cannot pay order in status {order.get('status')}")

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
        raise HTTPException(status_code=500, detail="Failed to create payment")

    # Backend-agnostic publish (RabbitMQ locally, SQS on AWS, etc.)
    publish(
        "payment.succeeded",
        {
            "order_id": order_id,
            "user_id": user_id,
            "amount": order["total"],
            "shipping_address": payload.shipping_address,
            "phone_number": payload.phone_number,
        },
    )

    await mark_order_paid_if_supported(order_id, token)

    return PaymentCreateOut(ok=True, payment_id=payment.id)


@app.get("/payments/{payment_id}", response_model=PaymentOut)
def get_payment(
    payment_id: int,
    claims: dict = Depends(require_user),
    db: Session = Depends(get_db),
):
    user_id = int(claims["sub"])
    payment = db.query(Payment).filter(Payment.id == payment_id, Payment.user_id == user_id).first()
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    return payment


@app.get("/payments", response_model=List[PaymentOut])
def list_my_payments(
    claims: dict = Depends(require_user),
    db: Session = Depends(get_db),
):
    user_id = int(claims["sub"])
    return (
        db.query(Payment)
        .filter(Payment.user_id == user_id)
        .order_by(Payment.id.desc())
        .all()
    )


@app.get("/health")
def health():
    return {"ok": True}