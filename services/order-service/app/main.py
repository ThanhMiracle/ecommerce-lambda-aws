import os
from contextlib import asynccontextmanager
from typing import Any, Dict

import httpx
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from .db import SessionLocal
from .models import Order, OrderItem
from .schemas import OrderCreateIn, OrderOut, OrderItemOut
from shared.security import require_user
from shared.events import publish

# In Lambda this should point to your deployed product API URL (Lambda URL/API GW/ALB)
PRODUCT_URL_INTERNAL = os.getenv("PRODUCT_URL_INTERNAL", "http://product:8000").rstrip("/")

# Reuse client across invocations
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
    Do schema creation/migrations at deploy-time, not here.
    """
    global _http_client
    _http_client = httpx.AsyncClient(timeout=5.0)
    yield
    try:
        if _http_client:
            await _http_client.aclose()
    except Exception:
        pass


app = FastAPI(title="order-service", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten in prod
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


async def fetch_product_price(product_id: int) -> float:
    global _http_client
    if _http_client is None:
        # fallback in case lifespan didn't run (tests)
        _http_client = httpx.AsyncClient(timeout=5.0)

    try:
        r = await _http_client.get(f"{PRODUCT_URL_INTERNAL}/products/{product_id}")
    except httpx.TimeoutException:
        raise HTTPException(status_code=503, detail="Product service timeout")
    except httpx.RequestError:
        raise HTTPException(status_code=503, detail="Product service unavailable")

    if r.status_code != 200:
        raise HTTPException(status_code=400, detail=f"Product {product_id} not available")

    data = r.json()
    return float(data["price"])


@app.post("/orders", response_model=OrderOut)
async def create_order(
    payload: OrderCreateIn,
    claims: dict = Depends(require_user),
    db: Session = Depends(get_db),
):
    user_id = int(claims["sub"])
    user_email = claims["email"]

    if not payload.items:
        raise HTTPException(status_code=400, detail="Empty cart")

    merged: Dict[int, int] = {}
    for it in payload.items:
        pid = int(it.product_id)
        qty = int(it.qty)
        if qty <= 0:
            raise HTTPException(status_code=400, detail="Invalid qty")
        merged[pid] = merged.get(pid, 0) + qty

    prices: Dict[int, float] = {}
    for pid in merged.keys():
        prices[pid] = await fetch_product_price(pid)

    total = 0.0
    for pid, qty in merged.items():
        total += prices[pid] * qty

    try:
        with db.begin():
            order = Order(
                user_id=user_id,
                user_email=user_email,
                status="CREATED",
                total=total,
            )
            db.add(order)
            db.flush()  # get order.id

            items_out: list[OrderItemOut] = []
            for pid, qty in merged.items():
                unit_price = prices[pid]
                db.add(
                    OrderItem(
                        order_id=order.id,
                        product_id=pid,
                        qty=qty,
                        unit_price=unit_price,
                    )
                )
                items_out.append(
                    OrderItemOut(product_id=pid, qty=qty, unit_price=float(unit_price))
                )

        db.refresh(order)
        return OrderOut(
            id=order.id,
            status=order.status,
            total=float(order.total),
            items=items_out,
        )

    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to create order")


@app.get("/orders/{order_id}", response_model=OrderOut)
def get_order(order_id: int, claims: dict = Depends(require_user), db: Session = Depends(get_db)):
    user_id = int(claims["sub"])
    order = db.query(Order).filter(Order.id == order_id, Order.user_id == user_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Not found")

    items = [
        OrderItemOut(product_id=i.product_id, qty=i.qty, unit_price=float(i.unit_price))
        for i in order.items
    ]
    return OrderOut(id=order.id, status=order.status, total=float(order.total), items=items)


@app.post("/orders/{order_id}/pay")
def pay_order(order_id: int, claims: dict = Depends(require_user), db: Session = Depends(get_db)):
    user_id = int(claims["sub"])
    order = db.query(Order).filter(Order.id == order_id, Order.user_id == user_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Not found")

    if order.status == "PAID":
        return {"ok": True, "status": "PAID"}
    if order.status != "CREATED":
        raise HTTPException(status_code=400, detail=f"Cannot pay in status {order.status}")

    order.status = "PAID"
    db.commit()
    db.refresh(order)

    # Backend-agnostic event publish (RabbitMQ locally, SQS on AWS, etc.)
    try:
        publish(
        "payment.succeeded",
        {"email": order.user_email, "order_id": order.id, "total": float(order.total)},)
    except Exception as e:
    # Don't break payment if the event system is temporarily unavailable
        print("event publish failed:", repr(e))

    return {"ok": True, "status": "PAID"}


@app.get("/health")
def health():
    return {"ok": True}