from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session, joinedload

from ..database import get_db
from ..deps import current_user
from ..models import Conversation, Customer, Message, Template, User, utcnow
from ..schemas import (
    ConversationDetail,
    ConversationOut,
    ConversationPatch,
    MessageIn,
    MessageOut,
    TemplateSendIn,
)
from ..services import whatsapp
from ..services.inbox import window_open
from ..services.templates import placeholder_count, render

router = APIRouter(prefix="/conversations", tags=["Conversations"])

WINDOW_CLOSED = (
    "WhatsApp only allows free-text replies within 24 hours of the customer's last message. "
    "Send a template instead."
)


def _get_owned(db: Session, user: User, conversation_id: int) -> Conversation:
    conversation = db.scalar(
        select(Conversation)
        .options(joinedload(Conversation.customer))
        .where(Conversation.id == conversation_id, Conversation.tenant_id == user.tenant_id)
    )
    if conversation is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Conversation not found")
    return conversation


def _check_can_message(conversation: Conversation) -> None:
    if conversation.customer.opted_out:
        raise HTTPException(status.HTTP_409_CONFLICT, "This customer opted out of messages")


def _save_outgoing(db: Session, conversation: Conversation, body: str, delivery: str, wamid: str | None, kind: str) -> Message:
    now = utcnow()
    message = Message(
        conversation_id=conversation.id,
        direction="out",
        body=body,
        status=delivery,
        source="agent",
        kind=kind,
        external_id=wamid,
        created_at=now,
    )
    db.add(message)
    conversation.preview = body[:255]
    conversation.last_message_at = now
    conversation.status = "open"
    db.commit()
    return message


@router.get("", response_model=list[ConversationOut])
def list_conversations(
    q: str = "",
    state: str = "all",
    limit: int = Query(100, ge=1, le=300),
    offset: int = Query(0, ge=0),
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    query = (
        select(Conversation)
        .join(Customer, Customer.id == Conversation.customer_id)
        .options(joinedload(Conversation.customer))
        .where(Conversation.tenant_id == user.tenant_id)
        .order_by(Conversation.last_message_at.desc())
    )
    if state in ("open", "resolved"):
        query = query.where(Conversation.status == state)
    if q.strip():
        like = f"%{q.strip()}%"
        query = query.where(or_(Customer.name.ilike(like), Customer.phone.ilike(like)))
    return db.scalars(query.limit(limit).offset(offset)).all()


@router.get("/{conversation_id}", response_model=ConversationDetail)
def get_conversation(conversation_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    conversation = _get_owned(db, user, conversation_id)
    if conversation.unread:
        conversation.unread = 0
        db.commit()
    detail = ConversationDetail.model_validate(conversation)
    detail.window_open = window_open(conversation, whatsapp.is_configured(user.tenant))
    return detail


@router.post("/{conversation_id}/messages", response_model=MessageOut, status_code=status.HTTP_201_CREATED)
def send_message(
    conversation_id: int,
    payload: MessageIn,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    conversation = _get_owned(db, user, conversation_id)
    _check_can_message(conversation)
    body = payload.body.strip()
    if not body:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Message is empty")

    configured = whatsapp.is_configured(user.tenant)
    if not window_open(conversation, configured):
        raise HTTPException(status.HTTP_409_CONFLICT, WINDOW_CLOSED)

    delivery, wamid = whatsapp.send_text(user.tenant, conversation.customer.phone, body)
    return _save_outgoing(db, conversation, body, delivery, wamid, "text")


@router.post("/{conversation_id}/template", response_model=MessageOut, status_code=status.HTTP_201_CREATED)
def send_template_message(
    conversation_id: int,
    payload: TemplateSendIn,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    conversation = _get_owned(db, user, conversation_id)
    _check_can_message(conversation)
    template = db.get(Template, payload.template_id)
    if template is None or template.tenant_id != user.tenant_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Template not found")
    needed = placeholder_count(template.body)
    variables = [v.strip() for v in payload.variables]
    if len(variables) < needed or any(not v for v in variables[:needed]):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, f"This template needs {needed} value(s)")

    delivery, wamid = whatsapp.send_template(
        user.tenant, conversation.customer.phone, template.name, template.language, variables[:needed]
    )
    return _save_outgoing(db, conversation, render(template.body, variables), delivery, wamid, "template")


@router.patch("/{conversation_id}", response_model=ConversationOut)
def update_conversation(
    conversation_id: int,
    payload: ConversationPatch,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    conversation = _get_owned(db, user, conversation_id)
    conversation.status = payload.status
    db.commit()
    return conversation
