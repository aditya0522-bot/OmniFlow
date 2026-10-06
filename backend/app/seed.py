from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from .config import settings
from .models import BotRule, Conversation, Customer, Message, Order, Template, Tenant, User, utcnow
from .security import hash_password

CUSTOMERS = [
    ("Rahul Sharma", "+919876543210"),
    ("Priya Singh", "+919123456789"),
    ("Amit Verma", "+919811122233"),
    ("Neha Kapoor", "+919899900011"),
    ("Sandeep Joshi", "+919700011122"),
    ("Kavita Rao", "+919845012345"),
    ("Imran Khan", "+919930045678"),
    ("Anjali Mehta", "+919765432100"),
]

# customer index -> list of (direction, text, minutes ago)
CHATS = {
    0: [
        ("in", "Hello, I need help with my order.", 190),
        ("out", "Sure, tell me what you need.", 185),
        ("in", "I need two lunch boxes tomorrow, 1 PM at the office.", 12),
    ],
    1: [
        ("in", "Good morning! Is today's tiffin on the way?", 140),
        ("out", "Yes, it left the kitchen 10 minutes ago.", 135),
        ("in", "Can I change my delivery address for tomorrow?", 41),
    ],
    2: [
        ("in", "Aaj ka menu kya hai?", 300),
        ("out", "Dal, jeera rice, mix veg, 4 roti and salad.", 296),
        ("in", "Theek hai. Ek monthly plan chahiye, rate bata do.", 95),
    ],
    3: [
        ("in", "Order mila, thank you. Khana bahut accha tha.", 1500),
        ("out", "Thank you Neha! Glad you liked it.", 1490),
    ],
    4: [
        ("in", "Please skip tomorrow, I am travelling.", 2000),
        ("out", "Done, tomorrow's delivery is paused.", 1995),
        ("in", "Thanks!", 1990),
    ],
    5: [
        ("in", "Do you have a no-onion no-garlic option?", 60),
    ],
}

# customer index, items, amount, status, hours ago
ORDERS = [
    (0, "2 Lunch Boxes", 240, "out_for_delivery", 2),
    (1, "1 Lunch Box", 120, "preparing", 3),
    (2, "1 Lunch Box, 1 Sweet", 150, "received", 1),
    (3, "Weekly Plan (6 days)", 650, "delivered", 30),
    (4, "1 Lunch Box", 120, "delivered", 52),
    (6, "3 Lunch Boxes", 360, "delivered", 70),
    (7, "1 Lunch Box", 120, "cancelled", 26),
    (0, "2 Lunch Boxes", 240, "delivered", 28),
]


BOT_RULES = [
    ("hello", "Hello! Welcome to Annapurna Tiffin Service. Type MENU, PRICE or TIMING, or wait and a team member will reply."),
    ("menu", "Today's menu: dal, jeera rice, mix veg, 4 roti and salad. Reply with the number of boxes to order."),
    ("price", "One lunch box is Rs 120. The weekly plan (6 days) is Rs 650."),
    ("timing", "We deliver between 12:00 and 2:00 PM, Monday to Saturday."),
]


def seed(db: Session) -> None:
    if db.scalar(select(Tenant.id)):
        return

    tenant = Tenant(name="Annapurna Tiffin Service")
    db.add(tenant)
    db.flush()

    db.add(
        User(
            tenant_id=tenant.id,
            name="Admin",
            email=settings.seed_admin_email.lower(),
            password_hash=hash_password(settings.seed_admin_password),
        )
    )
    seed_tenant_data(db, tenant)
    db.commit()


def seed_tenant_data(db: Session, tenant: Tenant) -> None:
    now = utcnow()
    customers = []
    for name, phone in CUSTOMERS:
        customer = Customer(tenant_id=tenant.id, name=name, phone=phone, created_at=now - timedelta(days=20))
        db.add(customer)
        customers.append(customer)
    db.flush()

    for keyword, reply in BOT_RULES:
        db.add(BotRule(tenant_id=tenant.id, keyword=keyword, reply=reply))
    db.add(
        Template(
            tenant_id=tenant.id,
            name="order_update",
            language="en",
            body="Hi {{1}}, your order {{2}} is on its way. Thank you for choosing us!",
        )
    )

    for index, messages in CHATS.items():
        last_text, last_at = messages[-1][1], now - timedelta(minutes=messages[-1][2])
        unread = 1 if messages[-1][0] == "in" and messages[-1][2] < 120 else 0
        inbound_ages = [m[2] for m in messages if m[0] == "in"]
        conversation = Conversation(
            tenant_id=tenant.id,
            customer_id=customers[index].id,
            preview=last_text,
            last_message_at=last_at,
            last_inbound_at=now - timedelta(minutes=min(inbound_ages)) if inbound_ages else None,
            unread=unread,
            status="resolved" if index in (3, 4) else "open",
        )
        db.add(conversation)
        db.flush()
        for direction, text, minutes in messages:
            db.add(
                Message(
                    conversation_id=conversation.id,
                    direction=direction,
                    body=text,
                    status="received" if direction == "in" else "sent",
                    source="customer" if direction == "in" else "agent",
                    created_at=now - timedelta(minutes=minutes),
                )
            )

    for number, (index, items, amount, status, hours) in enumerate(ORDERS, start=1):
        db.add(
            Order(
                tenant_id=tenant.id,
                customer_id=customers[index].id,
                code=f"ORD-{1000 + number}",
                items=items,
                amount=amount,
                status=status,
                created_at=now - timedelta(hours=hours),
            )
        )
