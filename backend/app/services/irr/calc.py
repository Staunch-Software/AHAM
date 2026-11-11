"""The weighted average IRR formula (BRD section 6). Pure: no database, no web. Tested in tests/test_irr_calc.py.

Per eligible disbursement record: weight = disbursed amount x loan tenure (months); product = weight x ROI (%).
The IRR of a group = sum of products / sum of weights.

- Month and year to date add up the records of the period (cumulative numerator over cumulative denominator). They are
  never an average of daily, branch or region percentages, and a total always comes from the loan-level records.
- Each loan's own tenure is used. (The BRD's other sentence, "total amount x average tenure", is a known error.)
- Everything is Decimal; rounding happens only for display (`rounded`).
- A group with no records has no IRR (None), never 0%.
"""
from collections.abc import Callable, Hashable, Iterable
from dataclasses import dataclass, field
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

PERIODS = ("TD", "MTD", "YTD")
PERIOD_LABELS = {"TD": "Today (TD)", "MTD": "Month to date (MTD)", "YTD": "Year to date (YTD)"}
CLASSES = ("HL", "NHL")
CLASS_LABELS = {"HL": "Home Loan (HL)", "NHL": "Non-Home Loan / LAP (NHL)"}
ZERO = Decimal(0)


@dataclass(frozen=True)
class Loan:
    """One eligible disbursement record: not cancelled / reversed and without an open exception."""

    account: str
    day: date
    amount: Decimal
    tenure: Decimal  # months
    roi: Decimal  # % a year
    product_class: str = "HL"
    branch_id: Hashable = None
    region_id: Hashable = None

    @property
    def weight(self) -> Decimal:
        return self.amount * self.tenure

    @property
    def product(self) -> Decimal:
        return self.weight * self.roi


@dataclass
class Group:
    """Running sums of one group (a branch, a region, the company) over one period."""

    weight: Decimal = ZERO
    product: Decimal = ZERO
    amount: Decimal = ZERO
    records: int = 0
    account_numbers: set = field(default_factory=set)
    min_roi: Decimal | None = None
    max_roi: Decimal | None = None

    def add(self, loan: Loan) -> None:
        self.weight += loan.weight
        self.product += loan.product
        self.amount += loan.amount
        self.records += 1
        self.account_numbers.add(loan.account)  # an account with several tranches counts once
        self.min_roi = loan.roi if self.min_roi is None else min(self.min_roi, loan.roi)
        self.max_roi = loan.roi if self.max_roi is None else max(self.max_roi, loan.roi)

    @property
    def accounts(self) -> int:
        return len(self.account_numbers)

    @property
    def irr(self) -> Decimal | None:
        return self.product / self.weight if self.weight else None


def weighted_irr(loans: Iterable[Loan]) -> Decimal | None:
    g = Group()
    for loan in loans:
        g.add(loan)
    return g.irr


def fy_start(day: date, start_month: int = 4) -> date:
    """First day of the financial year containing `day` (Indian FY: 1 April)."""
    return date(day.year if day.month >= start_month else day.year - 1, start_month, 1)


def period_bounds(as_of: date, fy_start_month: int = 4) -> dict[str, tuple[date, date]]:
    """Inclusive first and last day of Today, Month to date and Year to date."""
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
