import re
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from .config import settings


def clean_phone(raw: str) -> str:
    digits = re.sub(r"\D", "", raw)
    if len(digits) == 10:
        digits = settings.default_country_code + digits
    return "+" + digits


def local_zone() -> ZoneInfo:
    return ZoneInfo(settings.timezone)


def local_day_start_utc(days_ago: int = 0) -> datetime:
    """Start of a local calendar day, as naive UTC (matches how timestamps are stored)."""
    day = datetime.now(local_zone()).date() - timedelta(days=days_ago)
    start = datetime.combine(day, time.min, tzinfo=local_zone())
    return start.astimezone(timezone.utc).replace(tzinfo=None)


def to_local_date(naive_utc: datetime) -> date:
    return naive_utc.replace(tzinfo=timezone.utc).astimezone(local_zone()).date()
