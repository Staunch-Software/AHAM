"""Report tables as CSV or Excel (.xlsx) files. Pure: header + rows in, bytes out."""
import csv
import io
from collections.abc import Iterable, Sequence
from decimal import Decimal
from typing import Any

MEDIA_TYPES = {"csv": "text/csv", "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"}


def _safe(v: Any) -> Any:
    """Text that a spreadsheet would run as a formula gets a leading apostrophe; numbers stay numbers (a Decimal
    without its trailing zeros: 2160000000, not 2160000000.00000000); "" is an empty cell."""
    if isinstance(v, Decimal):
        return v.quantize(Decimal(1)) if v == v.to_integral_value() else v.normalize()
    if isinstance(v, str) and v[:1] in ("=", "+", "-", "@", "\t", "\r"):
        return "'" + v
    return None if v == "" else v


def to_csv(header: Sequence[str], rows: Iterable[Sequence[Any]]) -> bytes:
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(header)
    for r in rows:
        w.writerow(["" if v is None else _safe(v) for v in r])
    return ("﻿" + buf.getvalue()).encode("utf-8")  # the BOM makes Excel read ₹ and names correctly


def to_xlsx(header: Sequence[str], rows: Iterable[Sequence[Any]], sheet: str = "IRR") -> bytes:
    from openpyxl import Workbook  # noqa: PLC0415 - only needed for Excel exports
    from openpyxl.cell import WriteOnlyCell  # noqa: PLC0415
    from openpyxl.styles import Font  # noqa: PLC0415

    wb = Workbook(write_only=True)
    ws = wb.create_sheet(sheet[:31])
    ws.freeze_panes = "A2"
    for i, h in enumerate(header):
        ws.column_dimensions[_col(i)].width = max(12, min(40, len(h) + 2))
    bold = []
    for h in header:
        c = WriteOnlyCell(ws, value=h)
        c.font = Font(bold=True)
        bold.append(c)
    ws.append(bold)
    for r in rows:
        ws.append([_safe(v) for v in r])
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def _col(i: int) -> str:
    s = ""
    i += 1
    while i:
        i, rem = divmod(i - 1, 26)
        s = chr(65 + rem) + s
    return s


def render(fmt: str, header: Sequence[str], rows: Iterable[Sequence[Any]], sheet: str = "IRR") -> bytes:
    return to_xlsx(header, rows, sheet) if fmt == "xlsx" else to_csv(header, rows)
