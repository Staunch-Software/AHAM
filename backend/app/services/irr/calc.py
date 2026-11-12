"""The weighted average IRR formula, as Aham's process note (12 Nov 2026) gives it and Aham confirmed. Pure: no
database, no web. Tested in tests/test_irr_calc.py.

Per eligible disbursement row: Transaction IRR = disbursed amount x that row's own tenure (months) x ROI (%).
The IRR of a group = sum of Transaction IRR / (sum of disbursed amount x average tenure), where the average tenure is
the plain average of the tenure column over the group's rows (sum of tenures / number of rows), not weighted by amount.

- "No." is the number of disbursement rows: a loan paid out in two tranches counts twice.
- HL and NHL (LAP) are always worked out separately; nothing adds the two together.
- Month and year to date are worked out from all the rows of the period (their amounts, tenures and Transaction IRRs
  added up), never from daily, branch or region percentages; a total always comes from the rows themselves.
- Because the average tenure is not weighted by amount, a group's IRR can be above or below every row's own rate
  (Loan A 30 lakh, 240 months, 9% and Loan B 5 lakh, 60 months, 12% give 13.03%).
- Everything is Decimal; rounding happens only for display (`rounded`).
- A group with no rows has no IRR (None), never 0%.
"""
from collections.abc import Callable, Hashable, Iterable
from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

PERIODS = ("TD", "MTD", "YTD")
PERIOD_LABELS = {"TD": "For the day (TD)", "MTD": "Month to date (MTD)", "YTD": "Year to date (YTD)"}
CLASSES = ("HL", "NHL")
CLASS_LABELS = {"HL": "Home Loan (HL)", "NHL": "Non-Home Loan / LAP (NHL)"}
ZERO = Decimal(0)


@dataclass(frozen=True)
class Loan:
    """One eligible disbursement row: not cancelled / reversed and without an open exception."""

    account: str
    day: date
    amount: Decimal
    tenure: Decimal  # months
    roi: Decimal  # % a year
    product_class: str = "HL"
    branch_id: Hashable = None
    region_id: Hashable = None

    @property
    def product(self) -> Decimal:
        """The row's Transaction IRR: amount x its own tenure x ROI."""
        return self.amount * self.tenure * self.roi


def irr_of(product: Decimal, amount: Decimal, tenure: Decimal, records: int) -> Decimal | None:
    """sum of Transaction IRR / (sum of amount x (sum of tenure / rows)), from the four sums of a group."""
    if not records or not amount or not tenure:
        return None
    return Decimal(product) * records / (Decimal(amount) * Decimal(tenure))


def average_tenure(tenure: Decimal, records: int) -> Decimal | None:
    return Decimal(tenure) / records if records else None


def denominator(amount: Decimal, tenure: Decimal, records: int) -> Decimal:
    """sum of amount x average tenure."""
    return Decimal(amount) * Decimal(tenure) / records if records else ZERO


@dataclass
class Group:
    """Running sums of one group (a branch, a region, the company) over one period. All four add up across days,
    months, branches and regions; the IRR is worked out from them at the end."""

    product: Decimal = ZERO  # sum of Transaction IRR
    amount: Decimal = ZERO
    tenure: Decimal = ZERO  # sum of the rows' tenures, for the plain average
    records: int = 0  # rows: "No."

    def add(self, loan: Loan) -> None:
        self.product += loan.product
        self.amount += loan.amount
        self.tenure += loan.tenure
        self.records += 1

    @property
    def average_tenure(self) -> Decimal | None:
        return average_tenure(self.tenure, self.records)

    @property
    def denominator(self) -> Decimal:
        return denominator(self.amount, self.tenure, self.records)

    @property
    def irr(self) -> Decimal | None:
        return irr_of(self.product, self.amount, self.tenure, self.records)


def weighted_irr(loans: Iterable[Loan]) -> Decimal | None:
    g = Group()
    for loan in loans:
        g.add(loan)
    return g.irr


def fy_start(day: date, start_month: int = 4) -> date:
    """First day of the financial year containing `day` (Indian FY: 1 April)."""
    return date(day.year if day.month >= start_month else day.year - 1, start_month, 1)


def period_bounds(as_of: date, fy_start_month: int = 4) -> dict[str, tuple[date, date]]:
    """Inclusive first and last day of the day itself (TD), Month to date and Year to date."""
    return {"TD": (as_of, as_of), "MTD": (as_of.replace(day=1), as_of), "YTD": (fy_start(as_of, fy_start_month), as_of)}


def summarise(loans: Iterable[Loan], as_of: date, fy_start_month: int = 4,
              key: Callable[[Loan], Hashable] | None = None) -> dict[Hashable, dict[str, Group]]:
    """{group key: {"TD": Group, "MTD": Group, "YTD": Group}}. Without `key` everything is one group (key None).
    Loans outside the year to date are ignored; a group appears once it has a loan in the year to date."""
    bounds = period_bounds(as_of, fy_start_month)
    out: dict[Hashable, dict[str, Group]] = {}
    for loan in loans:
        groups = None
        for p in PERIODS:
            first, last = bounds[p]
            if first <= loan.day <= last:
                if groups is None:
                    groups = out.setdefault(key(loan) if key else None, {q: Group() for q in PERIODS})
                groups[p].add(loan)
    return out


def rounded(value: Decimal | None, decimals: int = 2) -> Decimal | None:
    """For display only (half up, like a calculator)."""
    if value is None:
        return None
    return value.quantize(Decimal(1).scaleb(-decimals), rounding=ROUND_HALF_UP)


def outside_band(irr: Decimal | None, band: tuple[Decimal, Decimal] | None, decimals: int = 2) -> str | None:
    """"below" / "above" when the IRR (as shown) is outside the reasonableness band; a warning only."""
    if irr is None or band is None:
        return None
    shown = rounded(irr, decimals)
    if shown < band[0]:
        return "below"
    if shown > band[1]:
        return "above"
    return None
