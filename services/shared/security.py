import os
from fastapi import Header, HTTPException, Depends
from jose import jwt, JWTError, ExpiredSignatureError

JWT_SECRET = os.getenv("JWT_SECRET")
if not JWT_SECRET:
    raise RuntimeError("JWT_SECRET is not set")
ALGO = "HS256"

# Optional future-proofing
JWT_ISSUER = os.getenv("JWT_ISSUER")
JWT_AUDIENCE = os.getenv("JWT_AUDIENCE")


def require_user(authorization: str = Header(default=None)) -> dict:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")

    token = authorization.split(" ", 1)[1].strip()
    if not token:
        raise HTTPException(status_code=401, detail="Missing bearer token")

    try:
        options = {"verify_aud": bool(JWT_AUDIENCE)}
        claims = jwt.decode(
            token,
            JWT_SECRET,
            algorithms=[ALGO],
            audience=JWT_AUDIENCE,
            issuer=JWT_ISSUER,
            options=options,
        )

        # Attach raw token so downstream services can forward it
        claims["raw_token"] = token
        return claims

    except ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")


def require_admin(claims: dict = Depends(require_user)) -> dict:
    if not claims.get("is_admin"):
        raise HTTPException(status_code=403, detail="Admin only")
    return claims