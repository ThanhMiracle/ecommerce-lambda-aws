from pydantic import BaseModel, EmailStr, field_validator, Field

MAX_PASSWORD_BYTES = 4096  # match main.py

def _validate_password(pw: str) -> str:
    if pw is None or pw == "":
        raise ValueError("Password is required")
    if len(pw.encode("utf-8")) > MAX_PASSWORD_BYTES:
        raise ValueError(f"Password too long (max {MAX_PASSWORD_BYTES} bytes)")
    return pw


class RegisterIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1)

    @field_validator("password")
    @classmethod
    def password_ok(cls, v: str) -> str:
        return _validate_password(v)


class LoginIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1)

    @field_validator("password")
    @classmethod
    def password_ok(cls, v: str) -> str:
        return _validate_password(v)


class TokenOut(BaseModel):
    access_token: str


class MeOut(BaseModel):
    id: int
    email: EmailStr
    is_admin: bool
    is_verified: bool