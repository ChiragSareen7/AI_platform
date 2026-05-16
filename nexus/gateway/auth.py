from datetime import datetime, timedelta, timezone

from fastapi import Header, HTTPException
from jose import jwt, JWTError

from shared.config import settings


def create_jwt(sub: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {"sub": sub, "exp": now + timedelta(minutes=settings.jwt_expire_minutes)}
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def verify_jwt(authorization: str | None = Header(default=None)) -> str:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")
    token = authorization.split(" ", 1)[1]
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        return str(payload.get("sub"))
    except JWTError as exc:
        raise HTTPException(status_code=401, detail="Invalid token") from exc

