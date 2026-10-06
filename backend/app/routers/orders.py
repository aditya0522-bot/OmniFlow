from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, joinedload

from ..database import get_db
from ..deps import current_user
from ..models import Customer, Order, User
from ..schemas import OrderIn, OrderOut, OrderPatch

router = APIRouter(prefix="/orders", tags=["Orders"])


def _get_owned(db: Session, user: User, order_id: int) -> Order:
    order = db.scalar(
        select(Order)
        .options(joinedload(Order.customer))
        .where(Order.id == order_id, Order.tenant_id == user.tenant_id)
    )
    if order is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Order not found")
    return order


@router.get("", response_model=list[OrderOut])
def list_orders(
    state: str = "all",
    q: str = "",
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    query = (
        select(Order)
        .join(Customer, Customer.id == Order.customer_id)
        .options(joinedload(Order.customer))
        .where(Order.tenant_id == user.tenant_id)
        .order_by(Order.created_at.desc())
    )
    if state != "all":
        query = query.where(Order.status == state)
    if q.strip():
        like = f"%{q.strip()}%"
        query = query.where(or_(Customer.name.ilike(like), Order.code.ilike(like), Order.items.ilike(like)))
    return db.scalars(query.limit(limit).offset(offset)).all()


@router.post("", response_model=OrderOut, status_code=status.HTTP_201_CREATED)
def create_order(payload: OrderIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    customer = db.get(Customer, payload.customer_id)
    if customer is None or customer.tenant_id != user.tenant_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Customer not found")
    existing = db.scalar(select(func.count()).select_from(Order).where(Order.tenant_id == user.tenant_id))
    order = Order(
        tenant_id=user.tenant_id,
        customer_id=customer.id,
        code=f"ORD-{1001 + existing}",
        items=payload.items.strip(),
        amount=payload.amount,
    )
    db.add(order)
    db.commit()
    return order


@router.patch("/{order_id}", response_model=OrderOut)
def update_order(
    order_id: int,
    payload: OrderPatch,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    order = _get_owned(db, user, order_id)
    order.status = payload.status
    db.commit()
    return order
