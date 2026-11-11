"""Reading the Disbursement Register (CSV / Excel) into disbursement rows. Pure: no database, no web.

Every problem with a row is reported as {"row", "column", "value", "message"}: the spreadsheet row number, the column
heading as written in the file, what was found there, and what is wrong and how to fix it.
"""
import csv
import io
import re
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from app.services.irr.settings import product_key
from app.services.tabular import norm_header, parse_date, text

# field -> accepted headings (normalised: lowercase, punctuation as spaces; "ROI %" -> "roi")
COLUMNS: dict[str, list[str]] = {
    "loan_account": ["loan account number", "loan account no", "loan account", "loan acc no", "loan ac no", "lan",
                     "lan no", "lan number", "loan no", "loan number", "account number", "account no"],
    "disbursement_ref": ["disbursement reference", "disbursement reference number", "disbursement ref",
                         "disbursement ref no", "disbursement no", "disbursement number", "disb ref", "disb ref no",
                         "disb no", "tranche number", "tranche no", "tranche"],
    "disbursement_date": ["disbursement date", "disbursal date", "date of disbursement", "disb date",
                          "disbursed on", "disbursed date", "date"],
    "product": ["product", "product name", "product type", "loan product", "scheme"],
    "branch": ["branch", "branch name", "branch code"],
    "amount": ["disbursed amount", "disbursed amount rs", "disbursed amount inr", "disbursement amount",
               "disbursal amount", "amount disbursed", "disb amount", "disbursed amt", "amount"],
    "tenure": ["tenure in months", "tenure months", "tenure", "loan tenure", "loan tenure months",
               "loan tenure in months", "tenor", "tenor months", "tenor in months", "tenure mths", "term months"],
    "roi": ["roi", "roi percent", "roi pct", "rate of interest", "interest rate", "transaction irr", "irr", "rate"],
    "status": ["status", "disbursement status", "loan status"],
    "customer_name": ["customer name", "customer", "borrower name", "applicant name", "name"],
}
# The headings of the template; also how a missing column is named.
LABELS = {
    "loan_account": "Loan account number", "disbursement_ref": "Disbursement reference",
    "disbursement_date": "Disbursement date", "product": "Product", "branch": "Branch",
    "amount": "Disbursed amount", "tenure": "Tenure in months", "roi": "ROI %", "status": "Status",
    "customer_name": "Customer name",
}
# Tenure and ROI columns must be there; an empty cell in them makes the row an exception, not an error.
REQUIRED = ("loan_account", "disbursement_date", "product", "branch", "amount", "tenure", "roi")
TEMPLATE_ROWS = [
    ["HL0001234", "1", "05-11-2026", "Home Loan", "Vijayawada", "3000000", "240", "9.00", "Disbursed", "Ravi Kumar"],
    ["LAP0005678", "", "05-11-2026", "LAP", "Vijayawada", "500000", "60", "12.00", "Disbursed", "Asha Devi"],
]
EXCLUDED_STATUS = ("cancel", "revers")  # Cancelled / Canceled / Cancellation, Reversed / Reversal, in any case
DATE_HINT = "Use DD-MM-YYYY, for example 05-11-2026"


def header_labels(filename: str, data: bytes) -> list[str]:
    """The heading row as written in the file (app.services.tabular.read_table keeps only normalised names)."""
    name = (filename or "").lower()
    if name.endswith((".xlsx", ".xlsm")):
        from openpyxl import load_workbook  # noqa: PLC0415 - only needed for Excel uploads

        try:
            wb = load_workbook(io.BytesIO(data), read_only=True, data_only=True)
        except Exception:  # noqa: BLE001 - read_table has already reported an unreadable file
            return []
        rows = wb.worksheets[0].iter_rows(values_only=True)
    else:
        try:
            body = data.decode("utf-8-sig")
        except UnicodeDecodeError:
            body = data.decode("cp1252", errors="replace")
        try:
            dialect = csv.Sniffer().sniff(body[:4096], delimiters=",;\t|")
        except csv.Error:
            dialect = csv.excel
        rows = csv.reader(io.StringIO(body), dialect)
    for r in rows:
        if any(str(c).strip() for c in r if c is not None):
            return [str(c).strip() if c is not None else "" for c in r]
    return []


def column_map(labels: list[str]) -> dict[str, list[str]]:
    """field -> the file's columns that can feed it, best heading first (as written in the file)."""
    by_norm: dict[str, str] = {}
    for label in labels:
        by_norm.setdefault(norm_header(label), label)
    return {f: [by_norm[a] for a in aliases if a in by_norm] for f, aliases in COLUMNS.items()}


def missing_columns(cols: dict[str, list[str]]) -> list[str]:
    return [LABELS[f] for f in REQUIRED if not cols.get(f)]


def shown(v: Any) -> str:
    """A cell as the user sees it in the spreadsheet."""
    if v is None:
        return ""
    if isinstance(v, datetime):
        return v.strftime("%d-%m-%Y") if v.time() == datetime.min.time() else v.strftime("%d-%m-%Y %H:%M")
    if isinstance(v, date):
        return v.strftime("%d-%m-%Y")
    if isinstance(v, float) and v.is_integer():
        return str(int(v))
    return str(v)


def number(v: Any) -> Decimal | None:
    """A number from a cell: 3000000, "30,00,000", "₹ 30,00,000", "Rs. 3000000", "9.5%". None when empty;
    ValueError when it is not a number."""
    if v is None or (isinstance(v, str) and not v.strip()):
        return None
    if isinstance(v, bool):
        raise ValueError(v)
    if isinstance(v, (int, Decimal)):
        return Decimal(v)
    if isinstance(v, float):
        return Decimal(repr(v))
    s = re.sub(r"[\s,₹%]", "", str(v))
    s = re.sub(r"^(rs\.?|inr)", "", s, flags=re.IGNORECASE)
    if not re.fullmatch(r"[-+]?(\d+(\.\d*)?|\.\d+)", s):
        raise ValueError(v)
    try:
        return Decimal(s)
    except InvalidOperation:
        raise ValueError(v)


def exception_reason(tenure: Decimal | None, roi: Decimal | None) -> str | None:
    """Why a disbursement cannot be used in the IRR yet (missing, zero or negative tenure or ROI); None = usable."""
    out = []
    for name, v in (("Tenure", tenure), ("ROI", roi)):
        if v is None:
            out.append(f"{name} missing")
        elif v == 0:
            out.append(f"{name} is 0")
        elif v < 0:
            out.append(f"{name} is negative ({v.normalize():f})")
    return "; ".join(out) or None


def roi_problem(roi: Decimal) -> str | None:
    """A positive ROI that cannot be a yearly percentage (zero and negative ones are exceptions instead)."""
    if 0 < roi < 1:
        return ("Looks like a fraction, not a percentage. Enter 9.25 for 9.25% "
                "(in Excel, format the column as Number, not Percentage)")
    if roi >= 100:
        return "Too high for a rate of interest. Enter the rate as a percentage, for example 9.25"
    return None


def dedup_key(account: str, ref: str | None, day: date, amount: Decimal) -> str:
    """Loan account + disbursement reference; without a reference, loan account + date + amount."""
    if ref:
        return f"R|{account}|{ref.upper()}"[:200]
    return f"D|{account}|{day.isoformat()}|{amount.quantize(Decimal('0.01'))}"[:200]


@dataclass
class Lookups:
    branches: dict[str, tuple[Any, Any]]  # normalised branch name or code -> (branch id, region id)
    products: dict[str, str]  # product key -> HL | NHL
    today: date


@dataclass
class Parsed:
    records: list[dict] = field(default_factory=list)  # column values of the Disbursement table
    errors: list[dict] = field(default_factory=list)


def parse_register(rows: list[dict[str, Any]], cols: dict[str, list[str]], look: Lookups) -> Parsed:
    """Rows from app.services.tabular.read_table -> records to save and row errors. A row with any error is not saved;
    all its problems are reported at once."""
    out = Parsed()
    first_row_of: dict[str, int] = {}
    for row in rows:
        n = row["_row"]
        errs: list[dict] = []

        def cell(f: str) -> tuple[Any, str]:
            """(value, column heading in the file): the first non-empty of the columns that feed the field."""
            names = cols.get(f) or []
            for name in names:
                v = row.get(norm_header(name))
                if v not in (None, ""):
                    return v, name
            return None, names[0] if names else LABELS[f]

        def err(column: str, value: Any, message: str) -> None:
            errs.append({"row": n, "column": column, "value": shown(value), "message": message})

        v, col = cell("loan_account")
        account = (text(v, 200) or "").upper()
        if not account:
            err(col, v, "Empty. Every row needs the loan account number")
        elif len(account) > 50:
            err(col, v, "Longer than 50 characters. Check that this is the loan account number")

        v, col = cell("disbursement_ref")
        ref = text(v, 200)
        if ref and len(ref) > 50:
            err(col, v, "Longer than 50 characters. Check that this is the disbursement reference or tranche number")

        v, col = cell("disbursement_date")
        day = None
        if v is None:
            err(col, v, f"Empty. Enter the disbursement date. {DATE_HINT}")
        else:
            try:
                day = parse_date(v)
            except ValueError:
                err(col, v, f"Not a real date. {DATE_HINT}")
            if day and day > look.today:
                err(col, v, f"This date is after today ({look.today:%d-%m-%Y}). Check the day, month and year")
                day = None

        v, col = cell("product")
        product = text(v, 100)
        product_class = None
        if not product:
            err(col, v, "Empty. Enter the product, for example Home Loan or LAP")
        else:
            product_class = look.products.get(product_key(product))
            if not product_class:
                err(col, v, "This product is not in the product mapping. Add it as HL or NHL under IRR settings "
                            "(HR & Admin > IRR settings), then upload again")

        v, col = cell("branch")
        place = None
        if v is None:
            err(col, v, "Empty. Enter the branch code or name as in Organization")
        else:
            place = look.branches.get(norm_header(text(v, 200)))
            if not place:
                err(col, v, "No branch has this code or name. Use the branch code or name exactly as in "
                            "HR & Admin > Organization")

        v, col = cell("amount")
        amount = None
        try:
            amount = number(v)
            if amount is None:
                err(col, v, "Empty. Enter the disbursed amount in rupees, for example 3000000")
            elif amount <= 0:
                err(col, v, "Must be more than 0. For a reversal, keep the original row and write Reversed "
                            "in the Status column")
                amount = None
            elif amount >= Decimal("1e14"):
                err(col, v, "Too large for a disbursed amount. Enter the amount in rupees, for example 3000000")
                amount = None
        except ValueError:
            err(col, v, "Not a number. Enter the amount in rupees using digits only, for example 3000000")

        v, col = cell("tenure")
        tenure = None
        try:
            tenure = number(v)
            if tenure is not None and abs(tenure) >= 1_000_000:
                err(col, v, "Too large for a tenure in months. Enter the tenure in months, for example 240")
        except ValueError:
            err(col, v, "Not a number. Enter the tenure in months using digits only, for example 240")

        v, col = cell("roi")
        roi = None
        try:
            roi = number(v)
            problem = roi_problem(roi) if roi is not None and roi > 0 else None
            if problem:
                err(col, v, problem)
            elif roi is not None and roi <= -100:
                err(col, v, "Not a rate of interest. Enter the rate as a percentage, for example 9.25")
        except ValueError:
            err(col, v, "Not a number. Enter the rate as a percentage, for example 9.25")

        status = text(cell("status")[0], 50)
        if not errs:
            key = dedup_key(account, ref, day, amount)
            if key in first_row_of:
                v, col = cell("loan_account")
                if ref:
                    err(col, v, f"Same loan account and disbursement reference as row {first_row_of[key]}. "
                                "Keep one of the two rows")
                else:
                    err(col, v, f"Same loan account, date and amount as row {first_row_of[key]}, and no "
                                "disbursement reference. Keep one row, or add the reference to tell the tranches apart")
            else:
                first_row_of[key] = n
        if errs:
            out.errors.extend(errs)
            continue
        excluded = bool(status) and status.lower().startswith(EXCLUDED_STATUS)
        out.records.append({
            "dedup_key": key, "loan_account": account, "disbursement_ref": ref, "disbursement_date": day,
            "product": product, "product_key": product_key(product), "product_class": product_class,
            "branch_id": place[0], "region_id": place[1], "amount": amount.quantize(Decimal("0.01")),
            "tenure_months": tenure, "roi": roi, "status": status, "excluded": excluded,
            "exception": None if excluded else exception_reason(tenure, roi),
            "customer_name": text(cell("customer_name")[0], 200), "source_row": n,
        })
    return out
