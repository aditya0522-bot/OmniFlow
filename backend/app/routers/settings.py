from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import settings as app_settings
from ..database import get_db
from ..deps import require_admin
from ..models import AuditLog, Tenant, User
from ..schemas import AuditOut, WhatsAppSettingsIn
from ..security import encrypt_secret
from ..services import audit, whatsapp

router = APIRouter(prefix="/settings", tags=["Settings"])


def _whatsapp_state(tenant: Tenant) -> dict:
    return {
        "connected": whatsapp.is_configured(tenant),
        "phone_number_id": tenant.whatsapp_phone_id,
        "token_set": bool(tenant.whatsapp_token_enc),
        "webhook_path": "/webhooks/whatsapp",
        "verify_token": app_settings.whatsapp_verify_token,
    }


@router.get("/whatsapp")
def get_whatsapp(admin: User = Depends(require_admin)):
    return _whatsapp_state(admin.tenant)


@router.put("/whatsapp")
def save_whatsapp(payload: WhatsAppSettingsIn, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    tenant = admin.tenant
    phone_id = payload.phone_number_id.strip()
    if phone_id:
        taken = db.scalar(select(Tenant.id).where(Tenant.whatsapp_phone_id == phone_id, Tenant.id != tenant.id))
        if taken:
            raise HTTPException(status.HTTP_409_CONFLICT, "This phone number ID is already used by another workspace")
    tenant.whatsapp_phone_id = phone_id
    if payload.clear_token:
        tenant.whatsapp_token_enc = ""
    elif payload.access_token and payload.access_token.strip():
        tenant.whatsapp_token_enc = encrypt_secret(payload.access_token.strip())
    audit.record(db, tenant.id, admin.id, "whatsapp_updated", f"phone number id {phone_id or 'cleared'}")
    db.commit()
    return _whatsapp_state(tenant)


@router.get("/audit", response_model=list[AuditOut])
def audit_log(admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    rows = db.execute(
        select(AuditLog, User.name)
        .outerjoin(User, User.id == AuditLog.user_id)
        .where(AuditLog.tenant_id == admin.tenant_id)
        .order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
        .limit(100)
    ).all()
    return [
        {"id": r.id, "action": r.action, "detail": r.detail, "user_name": name or "System", "created_at": r.created_at}
        for r, name in rows
    ]
