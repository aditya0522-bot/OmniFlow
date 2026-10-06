from datetime import datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from ..database import get_db
from ..deps import current_user
from ..models import Conversation, Customer, Message, Order, User
from ..schemas import DashboardOut
from ..utils import local_day_start_utc, local_zone, to_local_date

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])

STATUSES = ["received", "preparing", "out_for_delivery", "delivered", "cancelled"]


@router.get("", response_model=DashboardOut)
def summary(user: User = Depends(current_user), db: Session = Depends(get_db)):
    tid = user.tenant_id

    open_conversations = db.scalar(
        select(func.count()).select_from(Conversation).where(
            Conversation.tenant_id == tid, Conversation.status == "open"
        )
    )
    unread = db.scalar(
        select(func.coalesce(func.sum(Conversation.unread), 0)).where(Conversation.tenant_id == tid)
    )
    total_customers = db.scalar(
        select(func.count()).select_from(Customer).where(Customer.tenant_id == tid)
    )
    orders_today, revenue_today = db.execute(
        select(func.count(), func.coalesce(func.sum(Order.amount), 0)).where(
            Order.tenant_id == tid,
            Order.created_at >= local_day_start_utc(),
            Order.status != "cancelled",
        )
    ).one()

    today = datetime.now(local_zone()).date()
    week = {
        today - timedelta(days=n): {"date": (today - timedelta(days=n)).isoformat(), "incoming": 0, "outgoing": 0}
        for n in range(6, -1, -1)
    }
    rows = db.execute(
        select(Message.direction, Message.created_at)
        .join(Conversation, Conversation.id == Message.conversation_id)
        .where(Conversation.tenant_id == tid, Message.created_at >= local_day_start_utc(6))
    ).all()
    for direction, created_at in rows:
        point = week.get(to_local_date(created_at))
        if point:
            point["incoming" if direction == "in" else "outgoing"] += 1

    by_status = dict(
        db.execute(
            select(Order.status, func.count()).where(Order.tenant_id == tid).group_by(Order.status)
        ).all()
    )
    recent = db.scalars(
        select(Order)
        .options(joinedload(Order.customer))
        .where(Order.tenant_id == tid)
        .order_by(Order.created_at.desc())
        .limit(5)
    ).all()

    return {
        "open_conversations": open_conversations,
        "unread_messages": unread,
        "orders_today": orders_today,
        "revenue_today": revenue_today,
        "total_customers": total_customers,
        "week": list(week.values()),
        "order_status": {s: by_status.get(s, 0) for s in STATUSES},
        "recent_orders": recent,
    }
