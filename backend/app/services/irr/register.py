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
                     "lan no", "lan number", "loan no", "loan number", "account number", "account no", "unique id"],
    "disbursement_ref": ["disbursement reference", "disbursement reference number", "disbursement ref",
                         "disbursement ref no", "disbursement no", "disbursement number", "disb ref", "disb ref no",
                         "disb no", "tranche number", "tranche no", "tranche"],
    "disbursement_date": ["disbursement date", "disbursal date", "date of disbursement", "disb date",
                          "disbursed on", "disbursed date", "date"],
    # Aham's own register has a "HL/NHL" column instead of the product: its values are the class itself
    "product": ["product", "product name", "product type", "loan product", "scheme", "hl nhl", "hl or nhl",
                "product class"],
    "branch": ["branch", "branch name", "branch code", "location"],
    "amount": ["disbursed amount", "disbursed amount rs", "disbursed amount inr", "disbursement amount",
               "disbursal amount", "amount disbursed", "disb amount", "disbursed amt", "amount"],
    "tenure": ["tenure in months", "tenure months", "tenure", "loan tenure", "loan tenure months",
               "loan tenure in months", "tenor", "tenor months", "tenor in months", "tenure mths", "term months",
               "tenure in years", "tenure years", "tenure yrs", "loan tenure in years", "loan tenure years",
               "tenor in years", "tenor years", "term years"],
    # never "Transaction IRR" or "IRR": in Aham's process note that is amount x tenure x rate, not the rate
    "roi": ["roi", "roi percent", "roi pct", "rate of interest", "interest rate", "rate", "interest"],
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


# Headings that look like the rate but are not (Aham's process note, 12 Nov 2026: Transaction IRR = amount x tenure x rate)
NOT_THE_RATE = ("transaction irr", "irr")


def rate_hint(labels: list[str], missing: list[str]) -> str:
    """When the rate column is missing but the file has a Transaction IRR column, say why it is not used."""
    if LABELS["roi"] not in missing:
        return ""
    odd = [h for h in labels if norm_header(h) in NOT_THE_RATE]
    return (f" '{odd[0]}' is not read as the rate: Transaction IRR is the disbursed amount × tenure × rate of interest. "
            f"Add the rate of interest column ({LABELS['roi']}).") if odd else ""


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


def dedup_key(account: str, ref: str | None, day: date, amount: Decimal, *, branch_id: Any = None,
              customer: str | None = None) -> str:
    """Loan account + disbursement reference; without a reference, loan account + date + amount. A row with no loan
    account (Aham's register has some) is known by branch, date, amount and customer name; not by tenure or ROI, so a
    later upload that fills in a missing tenure replaces the row instead of adding it again."""
    if not account:
        parts = [str(branch_id), day.isoformat(), f"{amount.quantize(Decimal('0.01'))}",
                 " ".join((customer or "").upper().split())]
        return ("N|" + "|".join(parts))[:200]
    if ref:
        return f"R|{account}|{ref.upper()}"[:200]
    return f"D|{account}|{day.isoformat()}|{amount.quantize(Decimal('0.01'))}"[:200]


# Tenure headings that say their unit; any other tenure heading ("Tenure", "TENURE", "Tenor") follows the setting
TENURE_IN_YEARS = {"tenure in years", "tenure years", "tenure yrs", "loan tenure in years", "loan tenure years",
                   "tenor in years", "tenor years", "term years"}
TENURE_IN_MONTHS = {"tenure in months", "tenure months", "loan tenure months", "loan tenure in months",
                    "tenor months", "tenor in months", "tenure mths", "term months"}
CLASS_NAMES = {"hl": "HL", "nhl": "NHL"}  # a product cell that is the class itself (Aham's "HL/NHL" column)


def tenure_in_years(heading: str, default_unit: str) -> bool:
    h = norm_header(heading)
    if h in TENURE_IN_YEARS:
        return True
    if h in TENURE_IN_MONTHS:
        return False
    return default_unit == "years"


def rates_are_fractions(rows: list[dict[str, Any]], cols: dict[str, list[str]]) -> bool:
    """True when every rate in the file written as a plain number is below 1 (0.16 for 16%, or an Excel cell formatted
    as a percentage): the file gives rates as fractions. A text with a % sign ("17.50%") is a percentage as written and
    does not count either way. A file mixing 0.16 and 16 is not read as fractions; its rates below 1 stay row errors."""
    names = [norm_header(n) for n in cols.get("roi") or []]
    seen = False
    for row in rows:
        for name in names:
            v = row.get(name)
            if v in (None, ""):
                continue
            if isinstance(v, str) and "%" in v:
                break
            try:
                n = number(v)
            except ValueError:
                break
            if n is not None and n > 0:
                if n >= 1:
                    return False
                seen = True
            break
    return seen


@dataclass
class Lookups:
    branches: dict[str, tuple[Any, Any]]  # normalised branch name, code or register alias -> (branch id, region id)
    products: dict[str, str]  # product key -> HL | NHL
    today: date
    tenure_unit: str = "months"  # for a tenure heading that does not say its unit


@dataclass
class Parsed:
    records: list[dict] = field(default_factory=list)  # column values of the Disbursement table
    errors: list[dict] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)  # how the file was read, when it is not the obvious way


def parse_register(rows: list[dict[str, Any]], cols: dict[str, list[str]], look: Lookups) -> Parsed:
    """Rows from app.services.tabular.read_table -> records to save and row errors. A row with any error is not saved;
    all its problems are reported at once."""
    out = Parsed()
    first_row_of: dict[str, int] = {}
    fractions = rates_are_fractions(rows, cols)
    tenure_heading = (cols.get("tenure") or [LABELS["tenure"]])[0]
    years = tenure_in_years(tenure_heading, look.tenure_unit)
    if fractions:
        out.notes.append(f"Every rate in '{(cols.get('roi') or [LABELS['roi']])[0]}' is below 1, so the rates are read "
                         "as fractions: 0.16 = 16%.")
    if years:
        out.notes.append(f"'{tenure_heading}' is read in years and kept in months (10 years = 120 months). Change this "
                         "under IRR settings if the register gives months.")
    no_account = 0
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
        if len(account) > 50:
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
            product_class = look.products.get(product_key(product)) or CLASS_NAMES.get(product_key(product))
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
            if tenure is not None and years:
                tenure *= 12
            if tenure is not None and abs(tenure) >= 1_000_000:
                err(col, v, "Too large for a tenure. Enter the tenure as a number, for example 240 months")
        except ValueError:
            err(col, v, "Not a number. Enter the tenure using digits only, for example 240 months or 20 years")

        v, col = cell("roi")
        roi = None
        try:
            roi = number(v)
            if roi is not None and fractions and not (isinstance(v, str) and "%" in v):
                roi *= 100
            problem = roi_problem(roi) if roi is not None and roi > 0 else None
            if problem:
                err(col, v, problem)
            elif roi is not None and roi <= -100:
                err(col, v, "Not a rate of interest. Enter the rate as a percentage, for example 9.25")
        except ValueError:
            err(col, v, "Not a number. Enter the rate as a percentage, for example 9.25")

        status = text(cell("status")[0], 50)
        customer = text(cell("customer_name")[0], 200)
        if not errs:
            key = dedup_key(account, ref, day, amount, branch_id=place[0], customer=customer)
            if key in first_row_of:
                v, col = cell("loan_account")
                if not account:
                    err(col, v, f"Same branch, date, amount and customer as row {first_row_of[key]}, and no loan "
                                "account. Keep one row, or add the loan account numbers")
                elif ref:
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
        no_account += not account
        out.records.append({
            "dedup_key": key, "loan_account": account, "disbursement_ref": ref, "disbursement_date": day,
            "product": product, "product_key": product_key(product), "product_class": product_class,
            "branch_id": place[0], "region_id": place[1], "amount": amount.quantize(Decimal("0.01")),
            "tenure_months": tenure, "roi": roi, "status": status, "excluded": excluded,
            "exception": None if excluded else exception_reason(tenure, roi),
            "customer_name": customer, "source_row": n,
        })
    if no_account:
        out.notes.append(f"{no_account} row{'s have' if no_account > 1 else ' has'} no loan account. They are kept and "
                         "known by branch, date, amount and customer, so uploading them again replaces them; "
                         "but if the loan account is added later, they would count twice.")
    return out
