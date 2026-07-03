"""Password hashing (bcrypt) and JWT token creation/verification."""
import datetime as dt
from typing import Optional

import bcrypt
import jwt

from ..config import settings

_ALG = "HS256"


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except (ValueError, TypeError):
        return False


def create_token(user_id: str) -> str:
    now = dt.datetime.now(dt.timezone.utc)
    payload = {
        "sub": user_id,
        "iat": now,
        "exp": now + dt.timedelta(days=settings.JWT_EXPIRE_DAYS),
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=_ALG)


def decode_token(token: str) -> Optional[str]:
    """Return the user_id (sub) if the token is valid, else None."""
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[_ALG])
        return payload.get("sub")
    except jwt.PyJWTError:
        return None
