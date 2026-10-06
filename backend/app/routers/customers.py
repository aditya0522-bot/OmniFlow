from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import delete, func, or_, select
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import current_user, require_admin
from ..models import Conversation, Customer, Message, Order, User
from ..schemas import ConversationOut, CustomerIn, CustomerOut
from ..services import audit
from ..utils import clean_phone

router = APIRouter(prefix="/customers", tags=["Customers"])


def _with_counts(db: Session, tenant_id: int, customers: list[Customer]) -> list[dict]:
    counts = dict(
        db.execute(
            select(Order.customer_id, func.count()).where(Order.tenant_id == tenant_id).group_by(Order.customer_id)
        ).all()
    )
    return [
        {
            "id": c.id,
            "name": c.name,
            "phone": c.phone,
            "opted_out": c.opted_out,
            "status": c.status,
            "created_at": c.created_at,
            "order_count": counts.get(c.id, 0),
        }
        for c in customers
    ]


def _get_owned(db: Session, user: User, customer_id: int) -> Customer:
    customer = db.get(Customer, customer_id)
    if customer is None or customer.tenant_id != user.tenant_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Customer not found")
    return customer


@router.get("", response_model=list[CustomerOut])
def list_customers(
    q: str = "",
    limit: int = Query(200, ge=1, le=500),
    offset: int = Query(0, ge=0),
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    query = select(Customer).where(Customer.tenant_id == user.tenant_id).order_by(Customer.name)
    if q.strip():
        like = f"%{q.strip()}%"
        query = query.where(or_(Customer.name.ilike(like), Customer.phone.ilike(like)))
    return _with_counts(db, user.tenant_id, db.scalars(query.limit(limit).offset(offset)).all())


@router.post("", response_model=CustomerOut, status_code=status.HTTP_201_CREATED)
def create_customer(payload: CustomerIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    if not payload.consent:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY, "Confirm that the customer agreed to receive messages"
        )
    phone = clean_phone(payload.phone)
    exists = db.scalar(select(Customer.id).where(Customer.tenant_id == user.tenant_id, Customer.phone == phone))
    if exists:
        raise HTTPException(status.HTTP_409_CONFLICT, "A customer with this phone number already exists")
    customer = Customer(tenant_id=user.tenant_id, name=payload.name.strip(), phone=phone)
    db.add(customer)
    db.commit()
    return _with_counts(db, user.tenant_id, [customer])[0]


@router.post("/{customer_id}/conversation", response_model=ConversationOut)
def open_conversation(customer_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    customer = _get_owned(db, user, customer_id)
    conversation = db.scalar(
        select(Conversation)
        .where(Conversation.customer_id == customer.id)
        .order_by(Conversation.last_message_at.desc())
    )
    if conversation is None:
        conversation = Conversation(tenant_id=user.tenant_id, customer_id=customer.id)
        db.add(conversation)
        db.commit()
    return conversation


@router.delete("/{customer_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_customer(customer_id: int, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    """Removes the customer and everything stored about them (messages, chats, orders)."""
    customer = _get_owned(db, admin, customer_id)
    conversation_ids = select(Conversation.id).where(Conversation.customer_id == customer.id)
    db.execute(delete(Message).where(Message.conversation_id.in_(conversation_ids)))
    db.execute(delete(Conversation).where(Conversation.customer_id == customer.id))
    db.execute(delete(Order).where(Order.customer_id == customer.id))
    audit.record(db, admin.tenant_id, admin.id, "customer_deleted", customer.phone)
    db.delete(customer)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
