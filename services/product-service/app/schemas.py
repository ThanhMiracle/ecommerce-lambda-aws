from pydantic import BaseModel

class ProductOut(BaseModel):
    id: int
    name: str
    description: str
    price: float
    published: bool
    image_url: str | None = None   # ✅ ADD

class ProductCreate(BaseModel):
    name: str
    description: str = ""
    price: float
    published: bool = False
    image_url: str | None = None   # ✅ optional (you can keep it)

class ProductUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    price: float | None = None
    published: bool | None = None
    image_url: str | None = None   # ✅ ADD
