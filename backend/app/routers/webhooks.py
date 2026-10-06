import hashlib
import hmac
import json

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import PlainTextResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..config import settings
from ..database import get_db
from ..models import Tenant
from ..services.inbox import apply_status, store_inbound

router = APIRouter(tags=["Webhooks"])


@router.get("/whatsapp")
def verify_webhook(
    mode: str | None = Query(None, alias="hub.mode"),
    token: str | None = Query(None, alias="hub.verify_token"),
    challenge: str | None = Query(None, alias="hub.challenge"),
):
    if mode == "subscribe" and challenge and hmac.compare_digest(token or "", settings.whatsapp_verify_token):
        return PlainTextResponse(challenge)
    raise HTTPException(status.HTTP_403_FORBIDDEN, "Verification failed")


@router.post("/whatsapp")
async def receive_webhook(request: Request, db: Session = Depends(get_db)):
    raw = await request.body()

    if settings.whatsapp_app_secret:
        expected = "sha256=" + hmac.new(settings.whatsapp_app_secret.encode(), raw, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected, request.headers.get("x-hub-signature-256", "")):
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Bad signature")

    try:
        data = json.loads(raw)
    except ValueError:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Body is not valid JSON")

    stored = await run_in_threadpool(_process, db, data)
    # Meta retries anything that is not a 200, so always acknowledge.
    return {"received": True, "stored": stored}


def _process(db: Session, data: dict) -> int:
    stored = 0
    for entry in data.get("entry", []):
        for change in entry.get("changes", []):
            value = change.get("value", {})
            tenant = _find_tenant(db, value.get("metadata", {}).get("phone_number_id", ""))
            if tenant is None:
                continue
            for item in value.get("statuses", []):
                apply_status(db, tenant, item)
            names = {c.get("wa_id"): c.get("profile", {}).get("name") for c in value.get("contacts", [])}
            for item in value.get("messages", []):
                sender = item.get("from", "")
                kind = item.get("type", "text")
                body = item.get("text", {}).get("body", "") if kind == "text" else f"[{kind} message]"
                if store_inbound(db, tenant, "+" + sender, names.get(sender), body, item.get("id")):
                    stored += 1
    db.commit()
    return stored


def _find_tenant(db: Session, phone_id: str) -> Tenant | None:
    if phone_id:
        tenant = db.scalar(select(Tenant).where(Tenant.whatsapp_phone_id == phone_id))
        if tenant:
            return tenant
    # Only the public demo may fall back to the single workspace; real deployments route by phone number ID.
    if settings.demo_mode and db.scalar(select(func.count()).select_from(Tenant)) == 1:
        return db.scalar(select(Tenant))
    return None
