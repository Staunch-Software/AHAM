"""Reporting periods in the company's time zone (default Asia/Kolkata), returned as UTC instants."""
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import HTTPException


def tz_of(name: str | None) -> ZoneInfo:
    try:
        return ZoneInfo(name or "Asia/Kolkata")
    except (ZoneInfoNotFoundError, ValueError):
        return ZoneInfo("Asia/Kolkata")


def local_day_start_utc(d: date, tz: ZoneInfo) -> datetime:
    return datetime.combine(d, time.min, tzinfo=tz).astimezone(timezone.utc)


def day_range_utc(date_from: date | None, date_to: date | None, tz: ZoneInfo) -> tuple[datetime | None, datetime | None]:
    """Inclusive local dates -> [start, end) in UTC."""
    start = local_day_start_utc(date_from, tz) if date_from else None
    end = local_day_start_utc(date_to + timedelta(days=1), tz) if date_to else None
    return start, end


def today_local(tz: ZoneInfo, now: datetime | None = None) -> date:
    return (now or datetime.now(timezone.utc)).astimezone(tz).date()


def period_bounds(period: str, tz: ZoneInfo, date_from: date | None = None, date_to: date | None = None,
                  now: datetime | None = None) -> tuple[datetime, datetime, date, date]:
    """period: today | week (Monday-Sunday) | month | custom. Returns (start_utc, end_utc, first_day, last_day)."""
    today = today_local(tz, now)
    if period == "today":
        first = last = today
    elif period == "week":
        first = today - timedelta(days=today.weekday())
        last = first + timedelta(days=6)
    elif period == "month":
        first = today.replace(day=1)
        nxt = (first.replace(day=28) + timedelta(days=4)).replace(day=1)
        last = nxt - timedelta(days=1)
    elif period == "custom":
        if not date_from or not date_to:
            raise HTTPException(422, "Custom period needs date_from and date_to")
        if date_to < date_from:
            raise HTTPException(422, "date_to must not be before date_from")
        if (date_to - date_from).days > 366:
            raise HTTPException(422, "Custom period is limited to 366 days")
        first, last = date_from, date_to
    else:
        raise HTTPException(422, "period must be today, week, month or custom")
    return local_day_start_utc(first, tz), local_day_start_utc(last + timedelta(days=1), tz), first, last


def previous_bounds(first: date, last: date, tz: ZoneInfo, period: str) -> tuple[datetime, datetime]:
    """The equivalent period just before this one (same number of days; for a month, the previous calendar month)."""
    if period == "month":
        prev_last = first - timedelta(days=1)
        prev_first = prev_last.replace(day=1)
    else:
        days = (last - first).days + 1
        prev_last = first - timedelta(days=1)
        prev_first = prev_last - timedelta(days=days - 1)
    return local_day_start_utc(prev_first, tz), local_day_start_utc(prev_last + timedelta(days=1), tz)
