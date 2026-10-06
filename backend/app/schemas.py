import re
from datetime import datetime, timezone
from typing import Annotated, Literal

from pydantic import AfterValidator, BaseModel, ConfigDict, EmailStr, Field


def _as_utc(value: datetime) -> datetime:
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


UTCDateTime = Annotated[datetime, AfterValidator(_as_utc)]
OrderStatus = Literal["received", "preparing", "out_for_delivery", "delivered", "cancelled"]
Password = Annotated[str, Field(min_length=8, max_length=128)]


class ORM(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# ---- auth
class LoginIn(BaseModel):
    email: str
    password: str


class SignupIn(BaseModel):
    company: str = Field(min_length=2, max_length=120)
    name: str = Field(min_length=1, max_length=120)
    email: EmailStr
    password: Password


class RefreshIn(BaseModel):
    refresh_token: str


class PasswordChangeIn(BaseModel):
    current_password: str
    new_password: Password


class TenantOut(ORM):
    id: int
    name: str


class UserOut(ORM):
    id: int
    name: str
    email: str
    role: str
    tenant: TenantOut


class TokenOut(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserOut


# ---- team
class MemberIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    email: EmailStr
    password: Password
    role: Literal["admin", "agent"] = "agent"


class MemberPatch(BaseModel):
    role: Literal["admin", "agent"] | None = None
    is_active: bool | None = None
    password: Password | None = None


class MemberOut(ORM):
    id: int
    name: str
    email: str
    role: str
    is_active: bool
    created_at: UTCDateTime


# ---- customers
class CustomerIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    phone: str = Field(min_length=6, max_length=32)
    consent: bool


class CustomerBrief(ORM):
    id: int
    name: str
    phone: str
    opted_out: bool = False


class CustomerOut(CustomerBrief):
    status: str
    created_at: UTCDateTime
    order_count: int = 0


# ---- conversations
class MessageOut(ORM):
    id: int
    direction: str
    body: str
    status: str
    source: str
    kind: str
    created_at: UTCDateTime


class MessageIn(BaseModel):
    body: str = Field(min_length=1, max_length=4096)


class TemplateSendIn(BaseModel):
    template_id: int
    variables: list[str] = Field(default_factory=list, max_length=10)


class ConversationOut(ORM):
    id: int
    customer: CustomerBrief
    channel: str
    status: str
    unread: int
    preview: str
    last_message_at: UTCDateTime


class ConversationDetail(ConversationOut):
    messages: list[MessageOut]
    window_open: bool = True


class ConversationPatch(BaseModel):
    status: Literal["open", "resolved"]


# ---- orders
class OrderIn(BaseModel):
    customer_id: int
    items: str = Field(min_length=1, max_length=255)
    amount: int = Field(ge=0, le=10_000_000)


class OrderPatch(BaseModel):
    status: OrderStatus


class OrderOut(ORM):
    id: int
    code: str
    customer: CustomerBrief
    items: str
    amount: int
    status: str
    created_at: UTCDateTime


# ---- dashboard
class DayPoint(BaseModel):
    date: str
    incoming: int
    outgoing: int


class DashboardOut(BaseModel):
    open_conversations: int
    unread_messages: int
    orders_today: int
    revenue_today: int
    total_customers: int
    week: list[DayPoint]
    order_status: dict[str, int]
    recent_orders: list[OrderOut]


# ---- bot, templates, settings, demo
class BotRuleIn(BaseModel):
    keyword: str = Field(min_length=1, max_length=80)
    reply: str = Field(min_length=1, max_length=1000)


class BotRulePatch(BaseModel):
    active: bool


class BotRuleOut(ORM):
    id: int
    keyword: str
    reply: str
    active: bool


class TemplateIn(BaseModel):
    name: str = Field(min_length=1, max_length=80, pattern=r"^[a-z0-9_]+$")
    language: str = Field(default="en", min_length=2, max_length=10, pattern=r"^[a-z]{2}(_[A-Z]{2})?$")
    body: str = Field(min_length=1, max_length=1000)


class TemplateOut(ORM):
    id: int
    name: str
    language: str
    body: str
    variables: int = 0


class WhatsAppSettingsIn(BaseModel):
    phone_number_id: str = Field(max_length=64)
    access_token: str | None = Field(default=None, max_length=1000)
    clear_token: bool = False


class AuditOut(BaseModel):
    id: int
    action: str
    detail: str
    user_name: str
    created_at: UTCDateTime


class SimulateIn(BaseModel):
    customer_id: int
    text: str = Field(min_length=1, max_length=1000)
