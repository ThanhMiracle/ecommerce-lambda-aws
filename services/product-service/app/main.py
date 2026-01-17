from pathlib import Path
import uuid

from fastapi import FastAPI, Depends, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

from .db import Base, engine, SessionLocal, init_schema
from .models import Product
from .schemas import ProductOut, ProductCreate, ProductUpdate
from shared.security import require_user, require_admin

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

ALLOWED_EXT = {".png", ".jpg", ".jpeg", ".webp"}

app = FastAPI(title="product-service")

# Serve uploaded images
app.mount("/static", StaticFiles(directory=str(UPLOAD_DIR)), name="static")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.on_event("startup")
def startup():
    init_schema()
    Base.metadata.create_all(bind=engine)

def to_out(p: Product) -> ProductOut:
    return ProductOut(
        id=p.id,
        name=p.name,
        description=p.description,
        price=float(p.price),
        published=p.published,
        image_url=p.image_url,
    )

# Public homepage products
@app.get("/products", response_model=list[ProductOut])
def list_published(db: Session = Depends(get_db)):
    rows = db.query(Product).filter(Product.published == True).order_by(Product.id.desc()).all()
    return [to_out(r) for r in rows]

@app.get("/products/{product_id}", response_model=ProductOut)
def get_product(product_id: int, db: Session = Depends(get_db)):
    r = db.query(Product).filter(Product.id == product_id, Product.published == True).first()
    if not r:
        raise HTTPException(404, "Not found")
    return to_out(r)

# Admin endpoints
@app.get("/admin/products", response_model=list[ProductOut])
def admin_list(claims: dict = Depends(require_user), db: Session = Depends(get_db)):
    require_admin(claims)
    rows = db.query(Product).order_by(Product.id.desc()).all()
    return [to_out(r) for r in rows]

@app.post("/admin/products", response_model=ProductOut)
def admin_create(payload: ProductCreate, claims: dict = Depends(require_user), db: Session = Depends(get_db)):
    require_admin(claims)
    p = Product(
        name=payload.name,
        description=payload.description,
        price=payload.price,
        published=payload.published,
        image_url=payload.image_url,
    )
    db.add(p); db.commit(); db.refresh(p)
    return to_out(p)

@app.patch("/admin/products/{product_id}", response_model=ProductOut)
def admin_update(product_id: int, payload: ProductUpdate, claims: dict = Depends(require_user), db: Session = Depends(get_db)):
    require_admin(claims)
    p = db.query(Product).filter(Product.id == product_id).first()
    if not p:
        raise HTTPException(404, "Not found")

    if payload.name is not None: p.name = payload.name
    if payload.description is not None: p.description = payload.description
    if payload.price is not None: p.price = payload.price
    if payload.published is not None: p.published = payload.published
    if payload.image_url is not None: p.image_url = payload.image_url

    db.commit(); db.refresh(p)
    return to_out(p)

@app.delete("/admin/products/{product_id}")
def admin_delete(product_id: int, claims: dict = Depends(require_user), db: Session = Depends(get_db)):
    require_admin(claims)
    p = db.query(Product).filter(Product.id == product_id).first()
    if not p:
        raise HTTPException(404, "Not found")
    db.delete(p); db.commit()
    return {"ok": True}

# ✅ Upload image for a specific product (admin-only)
@app.post("/admin/products/{product_id}/image", response_model=ProductOut)
def upload_product_image(
    product_id: int,
    file: UploadFile = File(...),
    claims: dict = Depends(require_user),
    db: Session = Depends(get_db),
):
    require_admin(claims)

    p = db.query(Product).filter(Product.id == product_id).first()
    if not p:
        raise HTTPException(404, "Product not found")

    filename = file.filename or "upload"
    ext = Path(filename).suffix.lower()

    if ext not in ALLOWED_EXT:
        raise HTTPException(400, "Only .png, .jpg, .jpeg, .webp allowed")

    # Save file
    out_name = f"prod_{product_id}_{uuid.uuid4().hex}{ext}"
    dest = UPLOAD_DIR / out_name

    data = file.file.read()
    if not data:
        raise HTTPException(400, "Empty file")

    dest.write_bytes(data)

    # Store relative URL so it works in any environment
    p.image_url = f"/static/{out_name}"
    db.commit()
    db.refresh(p)
    return to_out(p)
