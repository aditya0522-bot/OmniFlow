import logging
from datetime import timedelta

from sqlalchemy import select

from ..database import SessionLocal
from ..models import Conversation, Customer, Message, Tenant, utcnow
from . import whatsapp

logger = logging.getLogger("omniflow.retry")
MAX_RETRIES = 3


def retry_failed() -> int:
    """Re-sends text messages that failed, up to three times within 24 hours."""
    retried = 0
    with SessionLocal() as db:
        cutoff = utcnow() - timedelta(hours=24)
        pending = db.scalars(
            select(Message)
            .where(
                Message.direction == "out",
                Message.status == "failed",
                Message.kind == "text",
                Message.retries < MAX_RETRIES,
                Message.created_at >= cutoff,
            )
            .limit(50)
        ).all()
        for message in pending:
            conversation = db.get(Conversation, message.conversation_id)
            tenant = db.get(Tenant, conversation.tenant_id)
            customer = db.get(Customer, conversation.customer_id)
            if customer.opted_out or not whatsapp.is_configured(tenant):
                continue
            message.retries += 1
            message.status, wamid = whatsapp.send_text(tenant, customer.phone, message.body)
            if wamid:
                message.external_id = wamid
            retried += 1
        db.commit()
    if retried:
        logger.info("retried %s failed message(s)", retried)
    return retried
