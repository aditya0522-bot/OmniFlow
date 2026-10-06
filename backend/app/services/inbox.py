import re
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import BotRule, Conversation, Customer, Message, Tenant, utcnow
from . import whatsapp

STOP_WORDS = {"stop", "unsubscribe"}
START_WORDS = {"start", "subscribe"}
STATUS_RANK = {"queued": 0, "sent": 1, "delivered": 2, "read": 3}


def window_open(conversation: Conversation, configured: bool) -> bool:
    """WhatsApp only allows free-text replies for 24 hours after the customer's last message."""
    if not configured:
        return True
    if conversation.last_inbound_at is None:
        return False
    return utcnow() - conversation.last_inbound_at < timedelta(hours=24)


def find_bot_reply(db: Session, tenant_id: int, text: str) -> str | None:
    rules = db.scalars(
        select(BotRule).where(BotRule.tenant_id == tenant_id, BotRule.active.is_(True)).order_by(BotRule.id)
    )
    for rule in rules:
        pattern = rf"(?<!\w){re.escape(rule.keyword.strip())}(?!\w)"
        if re.search(pattern, text, flags=re.IGNORECASE):
            return rule.reply
    return None


def store_inbound(
    db: Session,
    tenant: Tenant,
    phone: str,
    name: str | None,
    body: str,
    external_id: str | None = None,
) -> Conversation | None:
    """Saves a customer message and sends the bot reply if a rule matches.

    Returns None when the message was already stored (WhatsApp retries deliveries).
    """
    if external_id and db.scalar(select(Message.id).where(Message.external_id == external_id)):
        return None

    customer = db.scalar(select(Customer).where(Customer.tenant_id == tenant.id, Customer.phone == phone))
    if customer is None:
        customer = Customer(tenant_id=tenant.id, name=name or phone, phone=phone)
        db.add(customer)
        db.flush()

    conversation = db.scalar(
        select(Conversation)
        .where(Conversation.customer_id == customer.id, Conversation.channel == "whatsapp")
        .order_by(Conversation.last_message_at.desc())
    )
    if conversation is None:
        conversation = Conversation(tenant_id=tenant.id, customer_id=customer.id, channel="whatsapp")
        db.add(conversation)
        db.flush()

    now = utcnow()
    db.add(
        Message(
            conversation_id=conversation.id,
            direction="in",
            body=body,
            status="received",
            source="customer",
            external_id=external_id,
            created_at=now,
        )
    )
    conversation.preview = body[:255]
    conversation.last_message_at = now
    conversation.last_inbound_at = now
    conversation.unread = (conversation.unread or 0) + 1
    conversation.status = "open"

    keyword = body.strip().lower()
    if keyword in STOP_WORDS:
        customer.opted_out = True
        return conversation
    if keyword in START_WORDS:
        customer.opted_out = False

    reply = None if customer.opted_out else find_bot_reply(db, tenant.id, body)
    if reply:
        delivery, wamid = whatsapp.send_text(tenant, phone, reply)
        reply_time = utcnow()
        db.add(
            Message(
                conversation_id=conversation.id,
                direction="out",
                body=reply,
                status=delivery,
                source="bot",
                external_id=wamid,
                created_at=reply_time,
            )
        )
        conversation.preview = reply[:255]
        conversation.last_message_at = reply_time

    return conversation


def apply_status(db: Session, tenant: Tenant, item: dict) -> None:
    """Handles WhatsApp delivery receipts (sent, delivered, read, failed)."""
    message = db.scalar(
        select(Message)
        .join(Conversation, Conversation.id == Message.conversation_id)
        .where(Message.external_id == item.get("id"), Conversation.tenant_id == tenant.id)
    )
    if message is None:
        return
    new = item.get("status")
    if new == "failed":
        message.status = "failed"
    elif new in STATUS_RANK and STATUS_RANK[new] > STATUS_RANK.get(message.status, 0):
        message.status = new
