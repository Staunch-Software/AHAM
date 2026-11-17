"""The callers' call sheets as one Excel file, in the layout of the per-caller sheets the Master owner hands out today
(for example "Pooja Sankalp 5.xlsx"): a title, the caller and the call date, then one row per entry on that caller's
list: the lead details, the tries and answers recorded in the app, and the lead card. One worksheet per caller.

Pure: plain rows in, bytes out. The calls themselves are recorded in the app; this file is a copy to read and share.
"""
import io
import re
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any

from app.services.irr.export import _safe

LEAD_DETAILS = ["Caller", "Call date", "Entry ID", "Call type", "Category", "Call group", "Entry date", "SO name",
                "Branch", "Person met", "Mobile number", "SO description", "Tries left (of {max})", "Callback due",
                "Past call-centre history"]
CALLS = ["Attempt 1 slot", "Attempt 1 outcome", "Attempt 2 slot", "Attempt 2 outcome", "Attempt 3 slot",
         "Attempt 3 outcome", "DSA/CP: RAG", "DSA/CP: needs home loan himself?", "Name check", "Name as given", "Visit",
         "Relationship", "Loan need", "Timeline", "Income", "Documents", "Next step", "Next date", "Purpose",
         "Own contribution", "Remarks", "Lead ID"]
LEAD_CARD = ["Handling branch", "Age", "Date of birth", "Address", "Property pincode", "Business pincode", "City",
             "Payslip or ITR available", "Job profile", "Individual monthly income (₹)", "Family monthly income (₹)",
             "Vehicle (yes/no and type)", "CIBIL score", "EMI or cheque bounce in 6 months", "Property owner",
             "Property area", "Approved property", "Purpose of loan", "Loan requirement (₹)", "Property type"]
SECTIONS = [("Lead details", LEAD_DETAILS, "6B7280"), ("Calls and answers recorded in the app", CALLS, "142B78"),
            ("Lead card recorded in the app", LEAD_CARD, "142B78")]
WIDTHS = [12, 11, 27, 16, 15, 9, 11, 18, 14, 18, 13, 30, 9, 11, 46] + [9, 15] * 3 + [10, 12] + [14] * 16 + [12] * 20
GREY = "E5E7EB"
NOTE = ("Leads: 2 tries a day, up to 9 unanswered in all; DSA/CP: one try. Grey cells do not apply to that row. "
        "Calls are recorded in the app (My calls): this file is a copy of the list and what was recorded by {at}.")

# not applicable (grey), by column number (1-based), as on the hand-made sheets
_DSA_ONLY = range(22, 24)       # V:W  DSA/CP: RAG, needs home loan himself?
_LATER_TRIES = range(18, 22)    # R:U  attempts 2 and 3 (a DSA/CP gets one try)
_LEAD_QUESTIONS = range(24, 37)  # X:AJ the Lead questions (a DSA/CP only when he needs a home loan himself)


@dataclass
class SheetRow:
    cells: list[Any]  # in the order LEAD_DETAILS + CALLS + LEAD_CARD
    group: str  # "lead" | "dsa_cp"
    needs_home_loan: bool = False


def sheet_name(name: str, taken: set[str]) -> str:
    """Excel's rules: at most 31 characters, none of []:*?/\\, unique in the file."""
    base = re.sub(r"[\[\]:*?/\\]", " ", name).strip()[:31] or "Sheet"
    out, n = base, 2
    while out.lower() in taken:
        out = f"{base[:28]} {n}"
        n += 1
    taken.add(out.lower())
    return out


def _grey(row: SheetRow, col: int) -> bool:
    if row.group == "dsa_cp":
        return col in _LATER_TRIES or (col in _LEAD_QUESTIONS and not row.needs_home_loan)
    return col in _DSA_ONLY


def build(day: date, sheets: Sequence[tuple[str, Sequence[SheetRow]]], max_tries: int, exported_at: datetime) -> bytes:
    from openpyxl import Workbook  # noqa: PLC0415 - only needed for this export
    from openpyxl.styles import Alignment, Font, PatternFill  # noqa: PLC0415
    from openpyxl.utils import get_column_letter  # noqa: PLC0415

    header = [h.format(max=max_tries) for h in LEAD_DETAILS] + CALLS + LEAD_CARD
    last = get_column_letter(len(header))
    grey = PatternFill("solid", fgColor=GREY)
    wb = Workbook()
    wb.remove(wb.active)
    taken: set[str] = set()
    for caller, rows in sheets or [("No calls", [])]:
        ws = wb.create_sheet(sheet_name(caller, taken))
        ws["A1"] = "Takeoff lead call sheet"
        ws["A1"].font = Font(bold=True, size=14)
        ws["A2"], ws["B2"], ws["D2"], ws["E2"] = "Caller:", _safe(caller), "Call date:", day
        ws["E2"].number_format = "DD-MM-YYYY"
        ws["G2"] = NOTE.format(at=f"{exported_at:%d-%m-%Y %H:%M}")
        for c in ("A2", "D2"):
            ws[c].font = Font(bold=True)
        start = 1
        for title, cols, colour in SECTIONS:
            end = start + len(cols) - 1
            ws.merge_cells(start_row=3, start_column=start, end_row=3, end_column=end)
            cell = ws.cell(3, start, title)
            cell.font = Font(bold=True, color=colour)
            for c in range(start, end + 1):
                h = ws.cell(4, c, header[c - 1])
                h.font = Font(bold=True, color="FFFFFF")
                h.fill = PatternFill("solid", fgColor=colour)
                h.alignment = Alignment(wrap_text=True, vertical="top")
            start = end + 1
        for r, row in enumerate(rows, start=5):
            for c, v in enumerate(row.cells, start=1):
                cell = ws.cell(r, c, _safe(v) if v is not None else None)
                if isinstance(v, date):
                    cell.number_format = "DD-MM-YYYY"
                if _grey(row, c):
                    cell.fill = grey
        if not rows:
            ws["A5"] = "Nothing on this list for the day."
        for i, w in enumerate(WIDTHS[: len(header)], start=1):
            ws.column_dimensions[get_column_letter(i)].width = w
        ws.row_dimensions[4].height = 45
        ws.freeze_panes = "D5"
        ws.auto_filter.ref = f"A4:{last}{max(4 + len(rows), 5)}"
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()
