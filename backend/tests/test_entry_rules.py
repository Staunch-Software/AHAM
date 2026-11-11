"""Pure rules of section 4: phone cleaning (4.3), Entry ID (4.2), count date (4.4); contact cells (11.1)."""
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import pytest

from app.services.calendar import count_date, entry_code, entry_date, next_non_sunday
from app.services.phone import clean_phone, is_valid_phone, split_contacts

IST = ZoneInfo("Asia/Kolkata")


@pytest.mark.parametrize("raw,clean,valid", [
    ("9876543210", "9876543210", True),
    ("+91 98765 43210", "9876543210", True),
    ("+91-98765-43210", "9876543210", True),
    ("919876543210", "9876543210", True),  # 12 digits starting 91
    ("09876543210", "9876543210", True),  # 11 digits starting 0
    ("9876543210.0", "9876543210", True),  # through Excel
    (9876543210.0, "9876543210", True),
    ("98765​43210", "9876543210", True),  # invisible mark
    (" 98765 43210 ", "9876543210", True),
    ("5876543210", "5876543210", False),  # must start 6-9
    ("98765", "98765", False),
    ("98765432101", "98765432101", False),  # 11 digits not starting 0
    ("abc", "", False),
    (None, "", False),
])
def test_phone_cleaning(raw, clean, valid):
    assert clean_phone(raw) == clean and is_valid_phone(clean) is valid


@pytest.mark.parametrize("cell,numbers", [
    ("9876543210", ["9876543210"]),
    ("9876543210 / 9123456780", ["9876543210", "9123456780"]),
    ("9876543210,9123456780&8123456789", ["9876543210", "9123456780", "8123456789"]),
    ("+91 98765 43210; 9123456780", ["9876543210", "9123456780"]),  # spaces inside a number keep it whole
    ("9876543210 9123456780", ["9876543210", "9123456780"]),  # space as separator
    ("9876543210 / 9876543210", ["9876543210"]),  # repeats dropped
    ("NA / 12345", []),
    (9876543210, ["9876543210"]),
    (None, []),
])
def test_contact_cell_split(cell, numbers):
    assert split_contacts(cell) == numbers


def test_entry_id_is_ist_and_truncated():
    t = datetime(2026, 10, 15, 3, 37, 6, 999000, tzinfo=timezone.utc)  # 09:07:06.999 IST
    assert entry_code("AHFL01810", t, IST) == "AHFL01810-20261015-090706"
    late = datetime(2026, 10, 15, 19, 0, 0, tzinfo=timezone.utc)  # 00:30 IST next day
    assert entry_code("X", late, IST) == "X-20261016-003000" and entry_date(late, IST) == date(2026, 10, 16)


def test_count_date_moves_sundays_and_holidays():
    sun = date(2026, 10, 18)
    assert sun.weekday() == 6
    assert count_date(date(2026, 10, 17), set()) == date(2026, 10, 17)  # Saturday counts
    assert count_date(sun, set()) == date(2026, 10, 19)
    assert count_date(sun, {date(2026, 10, 19)}) == date(2026, 10, 20)  # Sunday then a holiday Monday
    assert count_date(date(2026, 10, 2), {date(2026, 10, 2)}) == date(2026, 10, 3)
    assert next_non_sunday(sun) == sun + timedelta(days=1) and next_non_sunday(date(2026, 10, 17)) == date(2026, 10, 17)


def test_next_date_runs_from_tomorrow_up_to_30_working_days():
    from app.services.calendar import next_date_problem
    today = date(2026, 11, 11)  # a Wednesday
    assert next_date_problem(today, today, set())  # not today
    assert next_date_problem(date(2026, 11, 15), today, set())  # a Sunday
    assert next_date_problem(date(2026, 11, 12), today, set()) is None
    assert next_date_problem(date(2026, 12, 16), today, set()) is None  # the 30th working day
    assert next_date_problem(date(2026, 12, 17), today, set())
    assert next_date_problem(date(2026, 12, 17), today, {date(2026, 11, 20)}) is None  # a holiday is not counted


def test_register_contacts_match_on_the_last_10_digits():
    assert split_contacts("0091 98765 43210") == ["9876543210"]  # RIGHT(number, 10), as the Takeoff master
    assert split_contacts("9876543210 9123456789") == ["9876543210", "9123456789"]
