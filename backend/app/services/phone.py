"""Phone cleaning and validation (section 4.3), shared by entries and the login register (section 11.1)."""
import re

_VALID = re.compile(r"[6-9]\d{9}")
_TRAILING_DOT_ZERO = re.compile(r"\.0+$")  # numbers that went through Excel: 9876543210.0
_NOT_DIGIT = re.compile(r"[^0-9]")  # ASCII digits only: spaces, +, -, invisible marks all go
_CONTACT_SPLIT = re.compile(r"[,/&;]+")


def clean_phone(raw: str | int | float | None) -> str:
    """Steps 1-2 of 4.3: strip non-digits, then drop a leading 0 (11 digits) or 91 (12 digits)."""
    if raw is None:
        return ""
    if isinstance(raw, float) and raw.is_integer():
        raw = int(raw)
    s = _TRAILING_DOT_ZERO.sub("", str(raw).strip())
    digits = _NOT_DIGIT.sub("", s)
    if len(digits) == 11 and digits.startswith("0"):
        digits = digits[1:]
    elif len(digits) == 12 and digits.startswith("91"):
        digits = digits[2:]
    return digits


def is_valid_phone(cleaned: str) -> bool:
    return bool(_VALID.fullmatch(cleaned))


def valid_phone_or_none(raw) -> str | None:
    c = clean_phone(raw)
    return c if is_valid_phone(c) else None


def split_contacts(cell: str | int | float | None) -> list[str]:
    """Every valid number in a login-register contact cell (up to 3, separated by , / & ; or spaces).

    A part is first cleaned whole, so "+91 98765 43210" stays one number; only if that is not valid is it split on
    spaces. Order is kept and repeats are dropped."""
    if cell is None:
        return []
    if isinstance(cell, (int, float)):
        cell = str(int(cell)) if float(cell).is_integer() else str(cell)
    found: list[str] = []
    for part in _CONTACT_SPLIT.split(str(cell)):
        whole = valid_phone_or_none(part)
        candidates = [whole] if whole else [valid_phone_or_none(t) for t in part.split()]
        for c in candidates:
            if c and c not in found:
                found.append(c)
    return found
