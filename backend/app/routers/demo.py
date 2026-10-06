from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from ..config import settings
from ..database import get_db
from ..deps import current_user, require_admin
from ..models import BotRule, Conversation, Customer, Message, Order, Template, User
from ..schemas import SimulateIn
from ..seed import seed_tenant_data
from ..services.inbox import store_inbound

router = APIRouter(tags=["Demo"])


def _sandbox_enabled() -> bool:
    return settings.demo_mode or settings.environment != "production"


@router.get("/public/config")
def public_config():
    """Lets the login page offer a one-click demo. Credentials are only exposed in demo mode."""
    config = {"demo_mode": settings.demo_mode, "allow_signup": settings.allow_signup}
    if settings.demo_mode:
        config.update(demo_email=settings.seed_admin_email, demo_password=settings.seed_admin_password)
    return config


@router.post("/demo/simulate")
def simulate_message(payload: SimulateIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    if not _sandbox_enabled():
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Not available")
    customer = db.get(Customer, payload.customer_id)
    if customer is None or customer.tenant_id != user.tenant_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Customer not found")
    conversation = store_inbound(db, user.tenant, customer.phone, customer.name, payload.text.strip())
    db.commit()
    return {"conversation_id": conversation.id}


@router.post("/demo/reset")
def reset_demo(admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    if not settings.demo_mode:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Not available")
    tid = admin.tenant_id
    own_conversations = select(Conversation.id).where(Conversation.tenant_id == tid)
    db.execute(delete(Message).where(Message.conversation_id.in_(own_conversations)))
    for model in (Conversation, Order, Customer, BotRule, Template):
        db.execute(delete(model).where(model.tenant_id == tid))
    seed_tenant_data(db, admin.tenant)
    db.commit()
    return {"reset": True}
