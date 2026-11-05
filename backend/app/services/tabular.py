"""Reading uploaded CSV / Excel files (roster, attendance, login register) into plain rows."""
import csv
import io
import re
from datetime import date, datetime, timedelta
from typing import Any

from fastapi import HTTPException

MAX_ROWS = 50_000


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
    out = []
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
    raise ValueError(f"'{v}' is not a date (use YYYY-MM-DD or DD-MM-YYYY)")


def text(v: Any, max_len: int) -> str | None:
    if v in (None, ""):
        return None
    if isinstance(v, float) and v.is_integer():
        v = int(v)
    s = re.sub(r"\s+", " ", str(v)).strip()
    return s[:max_len] or None
