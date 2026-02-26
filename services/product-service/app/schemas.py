from pydantic import BaseModel, Field, ConfigDict


class ProductOut(BaseModel):
    id: int
    name: str
    description: str
    price: float
    published: bool
    image_url: str | None = None

    model_config = ConfigDict(from_attributes=True)


class ProductCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str = ""
    price: float = Field(gt=0)
    published: bool = False
    image_url: str | None = None


class ProductUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    price: float | None = Field(default=None, gt=0)
    published: bool | None = None
    image_url: str | None = None