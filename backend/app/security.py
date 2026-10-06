import base64
import hashlib
from datetime import datetime, timedelta, timezone

import bcrypt
from cryptography.fernet import Fernet, InvalidToken
from jose import JWTError, jwt

from .config import settings

ALGORITHM = "HS256"


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode(), hashed.encode())
    except ValueError:
        return False


def _token(user, kind: str, lifetime: timedelta) -> str:
    claims = {
        "sub": str(user.id),
        "tv": user.token_version,
        "typ": kind,
        "exp": datetime.now(timezone.utc) + lifetime,
    }
    return jwt.encode(claims, settings.secret_key, algorithm=ALGORITHM)


def create_access_token(user) -> str:
    return _token(user, "access", timedelta(minutes=settings.access_token_minutes))


def create_refresh_token(user) -> str:
    return _token(user, "refresh", timedelta(days=settings.refresh_token_days))


def decode_token(token: str, kind: str) -> dict:
    payload = jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
    if payload.get("typ") != kind:
        raise JWTError("wrong token type")
    return payload


def _fernet() -> Fernet:
    key = base64.urlsafe_b64encode(hashlib.sha256(settings.secret_key.encode()).digest())
    return Fernet(key)


def encrypt_secret(value: str) -> str:
    return _fernet().encrypt(value.encode()).decode()


def decrypt_secret(value: str) -> str:
    if not value:
        return ""
    try:
        return _fernet().decrypt(value.encode()).decode()
    except InvalidToken:
        return ""
