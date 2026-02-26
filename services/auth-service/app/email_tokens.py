import os, time
from jose import jwt, JWTError

ALGO = "HS256"

ACCESS_JWT_SECRET = os.environ["JWT_SECRET"]
VERIFY_JWT_SECRET = os.getenv("VERIFY_TOKEN_SECRET", ACCESS_JWT_SECRET)

JWT_ISSUER = os.getenv("JWT_ISSUER")       # optional
JWT_AUDIENCE = os.getenv("JWT_AUDIENCE")   # optional


def make_verify_token(user_id: int, email: str, ttl_seconds: int = 3600) -> str:
    now = int(time.time())
    payload = {
        "sub": str(user_id),
        "email": email,
        "iat": now,
        "exp": now + ttl_seconds,
        "typ": "verify",
    }
    if JWT_ISSUER:
        payload["iss"] = JWT_ISSUER
    if JWT_AUDIENCE:
        payload["aud"] = JWT_AUDIENCE

    return jwt.encode(payload, VERIFY_JWT_SECRET, algorithm=ALGO)


def decode_verify_token(token: str) -> dict:
    try:
        options = {"verify_aud": bool(JWT_AUDIENCE)}
        data = jwt.decode(
            token,
            VERIFY_JWT_SECRET,
            algorithms=[ALGO],
            audience=JWT_AUDIENCE,
            issuer=JWT_ISSUER,
            options=options,
        )
    except JWTError as e:
        raise ValueError("Invalid or expired token") from e

    if data.get("typ") != "verify":
        raise ValueError("Invalid token type")
    return data