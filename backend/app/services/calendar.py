"""Entry IDs, entry dates and working days (sections 4.2 and 4.4)."""
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo


def entry_code(emp_code: str, submitted_at: datetime, tz: ZoneInfo) -> str:
    """<EmpID>-<YYYYMMDD>-<HHMMSS> from the Submit time in the company time zone, truncated (not rounded) to the second."""
    local = submitted_at.astimezone(tz)
    return f"{emp_code}-{local:%Y%m%d}-{local:%H%M%S}"


def entry_date(submitted_at: datetime, tz: ZoneInfo) -> date:
    return submitted_at.astimezone(tz).date()


def is_working_day(d: date, holidays: set[date]) -> bool:
    return d.weekday() != 6 and d not in holidays  # 6 = Sunday


def next_date_problem(d: date, today: date, holidays: set[date], max_working_days: int = 30) -> str | None:
    """A call's Next date (the Takeoff call sheet): from tomorrow, up to 30 working days ahead, never a Sunday."""
    if d <= today:
        return "The next date must be after today"
    if d.weekday() == 6:
        return "The next date must be a working day (not a Sunday)"
    last, n = today, 0
    while n < max_working_days:
        last += timedelta(days=1)
        if is_working_day(last, holidays):
            n += 1
    if d > last:
        return f"The next date can be at most {max_working_days} working days ahead (by {last:%d %b %Y})"
    return None


def count_date(d: date, holidays: set[date]) -> date:
    """The day an entry counts on: its own date, or the next working day if made on a Sunday or a holiday."""
    while not is_working_day(d, holidays):
        d += timedelta(days=1)
    return d


def next_non_sunday(d: date) -> date:
    """Next dates offered to callers are working days with Sundays skipped (7.2)."""
    return d + timedelta(days=1) if d.weekday() == 6 else d
