from fastapi import APIRouter, Depends, HTTPException, Request, status
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import settings
from ..database import get_db
from ..deps import current_user
from ..models import Tenant, User
from ..ratelimit import login_limiter, signup_limiter
from ..schemas import LoginIn, PasswordChangeIn, RefreshIn, SignupIn, TokenOut, UserOut
from ..security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from ..services import audit

router = APIRouter(prefix="/auth", tags=["Auth"])

# Checked when the email is unknown so response time does not reveal which emails exist.
_DUMMY_HASH = hash_password("not-a-real-password")


def client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for", "").split(",")[0].strip()
    return forwarded or (request.client.host if request.client else "unknown")


def issue(user: User) -> dict:
    return {
        "access_token": create_access_token(user),
        "refresh_token": create_refresh_token(user),
        "user": user,
    }


def too_many(wait: int, message: str) -> HTTPException:
    return HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, message, headers={"Retry-After": str(wait)})


@router.post("/signup", response_model=TokenOut, status_code=status.HTTP_201_CREATED)
def signup(payload: SignupIn, request: Request, db: Session = Depends(get_db)):
    if not settings.allow_signup:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Sign-up is closed")
    ip = client_ip(request)
    wait = signup_limiter.retry_after(ip)
    if wait:
        raise too_many(wait, "Too many sign-ups from this address. Try again later.")
    signup_limiter.fail(ip)

    email = payload.email.strip().lower()
    if db.scalar(select(User.id).where(User.email == email)):
        raise HTTPException(status.HTTP_409_CONFLICT, "An account with this email already exists")

    tenant = Tenant(name=payload.company.strip())
    db.add(tenant)
    db.flush()
    user = User(
        tenant_id=tenant.id,
        name=payload.name.strip(),
        email=email,
        password_hash=hash_password(payload.password),
        role="admin",
    )
    db.add(user)
    db.flush()
    audit.record(db, tenant.id, user.id, "signup", f"Workspace {tenant.name} created")
    db.commit()
    return issue(user)


@router.post("/login", response_model=TokenOut)
def login(payload: LoginIn, request: Request, db: Session = Depends(get_db)):
    email = payload.email.strip().lower()
    key = f"{client_ip(request)}|{email}"
    wait = login_limiter.retry_after(key)
    if wait:
        raise too_many(wait, "Too many failed attempts. Try again in a few minutes.")

    user = db.scalar(select(User).where(User.email == email))
    password_ok = verify_password(payload.password, user.password_hash if user else _DUMMY_HASH)
    if user is None or not user.is_active or not password_ok:
        login_limiter.fail(key)
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Incorrect email or password")

    login_limiter.clear(key)
    audit.record(db, user.tenant_id, user.id, "login")
    db.commit()
    return issue(user)


@router.post("/refresh", response_model=TokenOut)
def refresh(payload: RefreshIn, db: Session = Depends(get_db)):
    invalid = HTTPException(status.HTTP_401_UNAUTHORIZED, "Please sign in again")
    try:
        data = decode_token(payload.refresh_token, "refresh")
        user = db.get(User, int(data["sub"]))
        version = int(data["tv"])
    except (JWTError, KeyError, ValueError):
        raise invalid
    if user is None or not user.is_active or user.token_version != version:
        raise invalid
    return issue(user)


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(current_user)):
    return user


@router.post("/change-password", response_model=TokenOut)
def change_password(payload: PasswordChangeIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    if settings.demo_mode:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Password changes are disabled in the public demo")
    if not verify_password(payload.current_password, user.password_hash):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Current password is incorrect")
    user.password_hash = hash_password(payload.new_password)
    user.token_version += 1
    audit.record(db, user.tenant_id, user.id, "password_changed")
    db.commit()
    return issue(user)
