"""Reading uploaded CSV / Excel files (roster, attendance, login register) into plain rows."""
import csv
import difflib
import io
import re
from datetime import date, datetime, time, timedelta
from typing import Any

from fastapi import HTTPException

MAX_ROWS = 50_000


class Rows(list):
    """The rows of an upload, plus the file's own column names (normalised name -> as written in the file)."""
    headers: dict[str, str]


def norm_header(h: Any) -> str:
    return re.sub(r"[^a-z0-9]+", " ", str(h or "").lower()).strip()


def read_table(filename: str, data: bytes) -> list[dict[str, Any]]:
    """Rows as dicts keyed by normalised header (lowercase, punctuation -> spaces). The first non-empty row is the header.
    Excel: the first sheet. Blank rows are skipped. Each row also carries "_row", its line number in the file."""
    name = (filename or "").lower()
    if name.endswith((".xlsx", ".xlsm")):
        from openpyxl import load_workbook  # noqa: PLC0415 - only needed for Excel uploads

        try:
            wb = load_workbook(io.BytesIO(data), read_only=True, data_only=True)
        except Exception:  # noqa: BLE001 - any parse failure is the user's file
            raise HTTPException(422, "Could not read this Excel file. Save it as .xlsx or .csv and try again.")
        raw = list(wb.worksheets[0].iter_rows(values_only=True))
    elif name.endswith((".csv", ".txt")):
        try:
            text = data.decode("utf-8-sig")
        except UnicodeDecodeError:
            text = data.decode("cp1252", errors="replace")
        try:
            dialect = csv.Sniffer().sniff(text[:4096], delimiters=",;\t|")
        except csv.Error:
            dialect = csv.excel
        raw = list(csv.reader(io.StringIO(text), dialect))
    else:
        raise HTTPException(422, "Upload a .csv or .xlsx file")
    rows = [(i, r) for i, r in enumerate(raw, start=1) if any(str(c).strip() for c in r if c is not None)]
    if not rows:
        raise HTTPException(422, "The file is empty")
    if len(rows) > MAX_ROWS + 1:
        raise HTTPException(422, f"The file has more than {MAX_ROWS} rows; split it into smaller files")
    header = [norm_header(h) for h in rows[0][1]]
    out = Rows()
    out.headers = {norm_header(h): str(h).strip() for h in rows[0][1] if norm_header(h)}
    for line, r in rows[1:]:
        rec: dict[str, Any] = {"_row": line}
        for h, v in zip(header, r):
            if h and h not in rec:
                rec[h] = v.strip() if isinstance(v, str) else v
        out.append(rec)
    return out


def pick(row: dict, aliases: list[str]) -> Any:
    for a in aliases:
        v = row.get(a)
        if v not in (None, ""):
            return v
    return None


def has_column(rows: list[dict], aliases: list[str]) -> bool:
    return any(a in r for r in rows[:1] for a in aliases)


def column_name(rows: list[dict], aliases: list[str]) -> str:
    """The column as the file names it ("Emp Code"), else the expected name ("Emp ID"), for error messages."""
    headers = getattr(rows, "headers", {})
    for a in aliases:
        if a in headers:
            return headers[a]
    return aliases[0].title().replace("Id", "ID")


def require_columns(rows: list[dict], required: dict[str, list[str]], what: str) -> None:
    """A 422 that names every missing column and lists the columns the file has."""
    missing = [label for label, aliases in required.items() if not has_column(rows, aliases)]
    if missing:
        found = ", ".join(f"'{h}'" for h in getattr(rows, "headers", {}).values()) or "none"
        raise HTTPException(422, f"The {what} is missing the column{'s' if len(missing) > 1 else ''} "
                                 f"{', '.join(repr(m) for m in missing)}. Columns found in the file: {found}. "
                                 "Download the template to see the expected columns.")


def row_error(row: int, column: str | None, value: Any, message: str, **extra: Any) -> dict:
    """One problem in an uploaded file: where it is, what was found and what to do about it."""
    shown = "" if value is None else (value.isoformat() if isinstance(value, (date, datetime)) else str(value))
    return {"row": row, "column": column, "value": shown, "message": message, **extra}


def did_you_mean(value: str, choices: list[str]) -> str:
    """" Did you mean 'Vijayawada'?" when a name is close to a known one, else ""."""
    close = difflib.get_close_matches(value, choices, n=2, cutoff=0.6)
    return f" Did you mean {' or '.join(repr(c) for c in close)}?" if close else ""


_DATE_FORMATS = ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%d.%m.%Y", "%d-%b-%Y", "%d %b %Y", "%d-%b-%y", "%d/%m/%y",
                 "%Y/%m/%d", "%d %B %Y")


def parse_date(v: Any) -> date | None:
    """Accepts real dates, ISO / Indian day-first text, and Excel serial numbers. Raises ValueError otherwise."""
    if v in (None, ""):
        return None
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, date):
        return v
    if isinstance(v, (int, float)) and 20000 < float(v) < 80000:  # Excel serial day
        return date(1899, 12, 30) + timedelta(days=int(v))
    s = str(v).strip()
    if re.fullmatch(r"\d{5}(\.0+)?", s):
        return parse_date(float(s))
    s = s.split(" 00:00")[0].split("T")[0] if re.match(r"\d{4}-\d{2}-\d{2}[ T]", s) else s
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"'{v}' is not a date. Write it as DD-MM-YYYY (for example 05-11-2026) or YYYY-MM-DD")


def parse_time(v: Any) -> time | None:
    """A time of day: "10:30", "10:30:15", "10.30", "2:45 PM", an Excel time. Raises ValueError otherwise."""
    if v in (None, ""):
        return None
    if isinstance(v, datetime):
        return v.time().replace(microsecond=0)
    if isinstance(v, time):
        return v.replace(microsecond=0)
    if isinstance(v, (int, float)) and 0 <= float(v) < 1:  # Excel stores a time as a fraction of a day
        secs = round(float(v) * 86400)
        return time(secs // 3600 % 24, secs // 60 % 60, secs % 60)
    s = str(v).strip().upper().replace(".", ":")
    for fmt in ("%H:%M", "%H:%M:%S", "%I:%M %p", "%I:%M:%S %p", "%I:%M%p", "%I %p"):
        try:
            return datetime.strptime(s, fmt).time()
        except ValueError:
            continue
    raise ValueError(f"'{v}' is not a time. Write it as HH:MM, for example 10:30 or 14:45 (or 2:45 PM)")


def text(v: Any, max_len: int) -> str | None:
    if v in (None, ""):
        return None
    if isinstance(v, float) and v.is_integer():
        v = int(v)
    s = re.sub(r"\s+", " ", str(v)).strip()
    return s[:max_len] or None
