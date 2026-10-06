from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..config import settings
from ..database import get_db
from ..deps import require_admin
from ..models import User
from ..schemas import MemberIn, MemberOut, MemberPatch
from ..security import hash_password
from ..services import audit

router = APIRouter(prefix="/team", tags=["Team"])


@router.get("", response_model=list[MemberOut])
def list_members(admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    return db.scalars(select(User).where(User.tenant_id == admin.tenant_id).order_by(User.created_at, User.id)).all()


@router.post("", response_model=MemberOut, status_code=status.HTTP_201_CREATED)
def add_member(payload: MemberIn, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    email = payload.email.strip().lower()
    if db.scalar(select(User.id).where(User.email == email)):
        raise HTTPException(status.HTTP_409_CONFLICT, "An account with this email already exists")
    member = User(
        tenant_id=admin.tenant_id,
        name=payload.name.strip(),
        email=email,
        password_hash=hash_password(payload.password),
        role=payload.role,
    )
    db.add(member)
    audit.record(db, admin.tenant_id, admin.id, "member_added", f"{email} as {payload.role}")
    db.commit()
    return member


@router.patch("/{member_id}", response_model=MemberOut)
def update_member(
    member_id: int,
    payload: MemberPatch,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    member = db.get(User, member_id)
    if member is None or member.tenant_id != admin.tenant_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Team member not found")

    new_role = payload.role or member.role
    new_active = member.is_active if payload.is_active is None else payload.is_active
    loses_admin = member.role == "admin" and member.is_active and (new_role != "admin" or not new_active)
    if loses_admin:
        other_admins = db.scalar(
            select(func.count())
            .select_from(User)
            .where(
                User.tenant_id == admin.tenant_id,
                User.role == "admin",
                User.is_active.is_(True),
                User.id != member.id,
            )
        )
        if other_admins == 0:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "The workspace needs at least one active admin")

    if payload.password and settings.demo_mode:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Password changes are disabled in the public demo")

    changes = []
    if new_role != member.role:
        member.role = new_role
        changes.append(f"role {new_role}")
    if new_active != member.is_active:
        member.is_active = new_active
        changes.append("activated" if new_active else "deactivated")
    if payload.password:
        member.password_hash = hash_password(payload.password)
        changes.append("password reset")
    if changes:
        member.token_version += 1  # signs the member out everywhere
        audit.record(db, admin.tenant_id, admin.id, "member_updated", f"{member.email}: {', '.join(changes)}")
    db.commit()
    return member
