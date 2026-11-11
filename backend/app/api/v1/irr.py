"""Weighted average IRR for Home Loans (HL) and Non-Home Loans / LAP (NHL), from the Disbursement Register.

Uploads (MIS), the two report layouts (Today / Month / Year to date, and HL & NHL month to date), the loan-level detail
behind any figure, reconciliation, exceptions and settings. The formula is in app.services.irr.calc; this module only
reads and writes. Every list is cut to the user's branches (app.services.scope), and every table can be downloaded
with format=csv or format=xlsx.
"""
import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any, Literal

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel, ConfigDict
from sqlalchemy import false, func, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_perm
from app.core.db import get_session
from app.models import Branch, ImportBatch, Region, User
from app.models.irr import Disbursement, IrrSettings
from app.services.irr import calc, export, register
from app.services.irr.settings import IrrConfig
from app.services.reference import audit
from app.services.sankalp.ops import company_today
from app.services.scope import visible_branch_ids
from app.services.tabular import norm_header, read_table

router = APIRouter(prefix="/irr", tags=["irr"])
MAX_FILE_BYTES = 10 * 1024 * 1024
Product = Literal["HL", "NHL"]
Level = Literal["branch", "region", "company"]
Period = Literal["TD", "MTD", "YTD"]
Fmt = Literal["csv", "xlsx"]
ELIGIBLE = (Disbursement.excluded.is_(False), Disbursement.exception.is_(None))
OPEN_EXCEPTION = (Disbursement.excluded.is_(False), Disbursement.exception.is_not(None))
NO_REGION = "No region"


async def load_config(s: AsyncSession, company_id: uuid.UUID) -> IrrConfig:
    row = await s.get(IrrSettings, company_id)
    return IrrConfig.model_validate(row.data) if row else IrrConfig()


def _file(fmt: str, name: str, header: list[str], rows: list[list[Any]], sheet: str = "IRR") -> Response:
    return Response(export.render(fmt, header, rows, sheet), media_type=export.MEDIA_TYPES[fmt],
                    headers={"Content-Disposition": f'attachment; filename="{name}.{fmt}"'})


def _num(v: Decimal | None) -> float | None:
    return None if v is None else float(v)


def _pct(v: Decimal | None, decimals: int) -> float | None:
    return _num(calc.rounded(v, decimals))


class Scope:
    """The rows a request may use: the company, the user's branches, and the region / branch filters."""

    def __init__(self, conds: list, company_wide: bool, branches: dict[uuid.UUID, Branch], regions: dict[uuid.UUID, str]):
        self.conds, self.company_wide, self.branches, self.regions = conds, company_wide, branches, regions

    def branch_label(self, bid) -> tuple[str, str]:
        b = self.branches.get(bid)
        return (b.code, b.name) if b else ("", "Unknown branch")

    def region_label(self, rid) -> str:
        return self.regions.get(rid, NO_REGION) if rid else NO_REGION


async def _scope(s: AsyncSession, user: User, region_id: uuid.UUID | None = None,
                 branch_id: uuid.UUID | None = None) -> Scope:
    visible = await visible_branch_ids(s, user)
    conds: list = [Disbursement.company_id == user.company_id]
    if visible is not None:
        conds.append(Disbursement.branch_id.in_(visible) if visible else false())
    if region_id:
        conds.append(Disbursement.region_id == region_id)
    if branch_id:
        conds.append(Disbursement.branch_id == branch_id)
    q = select(Branch).where(Branch.company_id == user.company_id)
    if visible is not None:
        q = q.where(Branch.id.in_(visible)) if visible else q.where(false())
    branches = {b.id: b for b in (await s.execute(q)).scalars().all()}
    regions = dict((await s.execute(select(Region.id, Region.name).where(Region.company_id == user.company_id))).all())
    return Scope(conds, visible is None and not region_id and not branch_id, branches, regions)


async def _as_of(s: AsyncSession, user: User, scope: Scope, as_of: date | None) -> date:
    """The day asked for; else the latest disbursement date the user can see; else today."""
    if as_of:
        return as_of
    latest = (await s.execute(select(func.max(Disbursement.disbursement_date)).where(*scope.conds))).scalar()
    return latest or await company_today(s, user.company_id)


async def _loans(s: AsyncSession, scope: Scope, first: date, last: date, product: str | None = None) -> list[calc.Loan]:
    q = select(Disbursement.loan_account, Disbursement.disbursement_date, Disbursement.amount,
               Disbursement.tenure_months, Disbursement.roi, Disbursement.product_class, Disbursement.branch_id,
               Disbursement.region_id).where(*scope.conds, *ELIGIBLE, Disbursement.disbursement_date >= first,
                                             Disbursement.disbursement_date <= last)
    if product:
        q = q.where(Disbursement.product_class == product)
    return [calc.Loan(*r) for r in (await s.execute(q)).all()]


async def _open_exceptions(s: AsyncSession, scope: Scope, bounds: dict[str, tuple[date, date]],
                           product: str | None = None) -> dict[str, int]:
    """How many disbursements of each period are left out until their tenure or ROI is corrected."""
    d = Disbursement.disbursement_date
    q = select(*[func.count().filter(d >= bounds[p][0], d <= bounds[p][1]) for p in calc.PERIODS]).where(
        *scope.conds, *OPEN_EXCEPTION, d >= bounds["YTD"][0], d <= bounds["YTD"][1])
    if product:
        q = q.where(Disbursement.product_class == product)
    return dict(zip(calc.PERIODS, (await s.execute(q)).one()))


def _rows_for(level: str, scope: Scope, region_id: uuid.UUID | None, branch_id: uuid.UUID | None,
              keys_with_data: set) -> list[tuple[Any, dict]]:
    """(group key, labels) of every row to show: each branch (or region) in scope, plus any group that has data.
    Groups without disbursements are listed too, with no IRR."""
    if level == "company":
        return [(None, {"label": "Company total" if scope.company_wide else "Total"})]
    shown = [b for b in scope.branches.values()
             if (b.status == "active" or b.id in keys_with_data) and (not branch_id or b.id == branch_id)
             and (not region_id or b.region_id == region_id)]
    if level == "branch":
        ids = {b.id for b in shown} | {k for k in keys_with_data if k in scope.branches}
        out = []
        for bid in ids:
            b = scope.branches[bid]
            out.append((bid, {"branch_id": str(bid), "region_id": str(b.region_id) if b.region_id else None,
                              "code": b.code, "label": b.name, "region": scope.region_label(b.region_id)}))
        return sorted(out, key=lambda r: (r[1]["region"], r[1]["label"]))
    ids = ({b.region_id for b in shown} if not region_id else {region_id}) | keys_with_data
    out = [(rid, {"region_id": str(rid) if rid else None, "label": scope.region_label(rid)}) for rid in ids]
    return sorted(out, key=lambda r: (r[0] is None, r[1]["label"]))


def _cell(g: calc.Group | None, decimals: int) -> dict:
    if g is None or not g.records:
        return {"accounts": 0, "irr": None, "amount": 0.0, "records": 0}
    return {"accounts": g.accounts, "irr": _pct(g.irr, decimals), "amount": float(g.amount), "records": g.records}


def _warn(label: str, where: str, product: str, g: calc.Group | None, cfg: IrrConfig) -> str | None:
    band = cfg.band(product)
    side = calc.outside_band(g.irr if g else None, band, cfg.decimals)
    if not side:
        return None
    d = cfg.decimals
    return (f"{label}, {where}: {calc.rounded(g.irr, d)}% is {side} the expected {product} range of "
            f"{calc.rounded(band[0], d)}% to {calc.rounded(band[1], d)}%")


def _key_fn(level: str):
    return {"branch": lambda x: x.branch_id, "region": lambda x: x.region_id, "company": None}[level]


# ---------------------------------------------------------------- report 1: Today / Month / Year to date
@router.get("/report")
async def report(as_of: date | None = None, product: Product = "HL", level: Level = "branch",
                 region_id: uuid.UUID | None = None, branch_id: uuid.UUID | None = None, format: Fmt | None = None,
                 user: User = Depends(require_perm("irr.view")), s: AsyncSession = Depends(get_session)):
    """Number of loan accounts and weighted average IRR for TD, MTD and YTD of one product class, per branch, region
    or for the company. The total row is worked out from the loans themselves, never from the rows above it."""
    cfg = await load_config(s, user.company_id)
    scope = await _scope(s, user, region_id, branch_id)
    day = await _as_of(s, user, scope, as_of)
    bounds = calc.period_bounds(day, cfg.fy_start_month)
    loans = await _loans(s, scope, bounds["YTD"][0], day, product)
    groups = calc.summarise(loans, day, cfg.fy_start_month, _key_fn(level))
    total = calc.summarise(loans, day, cfg.fy_start_month).get(None, {})
    total_label = "Company total" if scope.company_wide else "Total"
    rows, warnings = [], []
    for key, labels in _rows_for(level, scope, region_id, branch_id, set(groups) if level != "company" else set()):
        g = total if level == "company" else groups.get(key, {})
        flags = []
        for p in calc.PERIODS:
            w = _warn(labels["label"], calc.PERIOD_LABELS[p], product, g.get(p), cfg)
            if w:
                warnings.append(w)
                flags.append(p)
        rows.append({**labels, "periods": {p: _cell(g.get(p), cfg.decimals) for p in calc.PERIODS}, "flags": flags})
    total_flags = []
    if level != "company":
        for p in calc.PERIODS:
            w = _warn(total_label, calc.PERIOD_LABELS[p], product, total.get(p), cfg)
            if w:
                warnings.append(w)
                total_flags.append(p)
    tot = {"label": total_label, "periods": {p: _cell(total.get(p), cfg.decimals) for p in calc.PERIODS},
           "flags": total_flags}
    if format:
        first = {"branch": ["Branch code", "Branch", "Region"], "region": ["Region"], "company": ["Scope"]}[level]
        header = first + [f"{calc.PERIOD_LABELS[p]}: {h}" for p in calc.PERIODS
                          for h in ("Number of loan accounts", "Weighted average IRR (%)")]

        def line(r: dict, total_row: bool = False) -> list:
            lead = {"branch": [r.get("code", ""), r["label"], r.get("region", "")], "region": [r["label"]],
                    "company": [r["label"]]}[level]
            if total_row and level == "branch":
                lead = ["", r["label"], ""]
            return lead + [x for p in calc.PERIODS for x in (r["periods"][p]["accounts"], r["periods"][p]["irr"])]

        body = [line(r) for r in rows] + ([line(tot, True)] if level != "company" else [])
        return _file(format, f"irr_{product}_{level}_{day}", header, body, f"{product} IRR {day}")
    return {
        "as_of": day, "product": product, "level": level, "decimals": cfg.decimals,
        "periods": {p: {"from": a, "to": b} for p, (a, b) in bounds.items()},
        "rows": rows, "total": tot, "warnings": warnings,
        "band": cfg.bands.get(product).model_dump() if cfg.bands.get(product) else None,
        "open_exceptions": await _open_exceptions(s, scope, bounds, product),
    }


# ---------------------------------------------------------------- report 2: HL & NHL month to date
@router.get("/report/month-by-product")
async def month_by_product(as_of: date | None = None, level: Level = "branch", region_id: uuid.UUID | None = None,
                           branch_id: uuid.UUID | None = None, format: Fmt | None = None,
                           user: User = Depends(require_perm("irr.view")), s: AsyncSession = Depends(get_session)):
    """Month to date, HL next to NHL: number of loan accounts and weighted average IRR of each, per row and in total."""
    cfg = await load_config(s, user.company_id)
    scope = await _scope(s, user, region_id, branch_id)
    day = await _as_of(s, user, scope, as_of)
    bounds = calc.period_bounds(day, cfg.fy_start_month)
    loans = await _loans(s, scope, bounds["MTD"][0], day)
    by_class = {c: [x for x in loans if x.product_class == c] for c in calc.CLASSES}
    groups = {c: calc.summarise(by_class[c], day, cfg.fy_start_month, _key_fn(level)) for c in calc.CLASSES}
    totals = {c: calc.summarise(by_class[c], day, cfg.fy_start_month).get(None, {}).get("MTD") for c in calc.CLASSES}
    keys = set().union(*[set(groups[c]) for c in calc.CLASSES]) if level != "company" else set()
    total_label = "Company total" if scope.company_wide else "Total"
    rows, warnings = [], []
    for key, labels in _rows_for(level, scope, region_id, branch_id, keys):
        cells, flags = {}, []
        for c in calc.CLASSES:
            g = totals[c] if level == "company" else groups[c].get(key, {}).get("MTD")
            cells[c] = _cell(g, cfg.decimals)
            w = _warn(labels["label"], calc.PERIOD_LABELS["MTD"], c, g, cfg)
            if w:
                warnings.append(w)
                flags.append(c)
        rows.append({**labels, "classes": cells, "flags": flags})
    tot = {"label": total_label, "classes": {c: _cell(totals[c], cfg.decimals) for c in calc.CLASSES}, "flags": []}
    if level != "company":
        for c in calc.CLASSES:
            w = _warn(total_label, calc.PERIOD_LABELS["MTD"], c, totals[c], cfg)
            if w:
                warnings.append(w)
                tot["flags"].append(c)
    if format:
        first = {"branch": ["Branch code", "Branch", "Region"], "region": ["Region"], "company": ["Scope"]}[level]
        header = first + [f"{c}: {h}" for c in calc.CLASSES
                          for h in ("Number of loan accounts", "Weighted average IRR (%)")]
        body = []
        for r in rows + ([tot] if level != "company" else []):
            lead = {"branch": [r.get("code", ""), r["label"], r.get("region", "")], "region": [r["label"]],
                    "company": [r["label"]]}[level]
            body.append(lead + [x for c in calc.CLASSES for x in (r["classes"][c]["accounts"], r["classes"][c]["irr"])])
        return _file(format, f"irr_HL_NHL_MTD_{level}_{day}", header, body, f"HL NHL MTD {day}")
    return {
        "as_of": day, "level": level, "decimals": cfg.decimals, "period": {"from": bounds["MTD"][0], "to": day},
        "rows": rows, "total": tot, "warnings": warnings,
        "open_exceptions": (await _open_exceptions(s, scope, bounds))["MTD"],
    }


# ---------------------------------------------------------------- loan-level detail (audit)
DETAIL_HEADER = ["Loan account number", "Disbursement reference", "Disbursement date", "Branch code", "Branch",
                 "Region", "Product", "Product class", "Disbursed amount (₹)", "Tenure (months)", "ROI (%)",
                 "Weight (amount × tenure)", "Amount × tenure × ROI"]


@router.get("/detail")
async def detail(as_of: date | None = None, period: Period = "MTD", product: Product | None = None,
                 region_id: uuid.UUID | None = None, branch_id: uuid.UUID | None = None,
                 page: int = Query(1, ge=1), page_size: int = Query(50, ge=1, le=500), format: Fmt | None = None,
                 user: User = Depends(require_perm("irr.view")), s: AsyncSession = Depends(get_session)):
    """The disbursements behind a report figure, with each one's weight and product, so the IRR can be checked by
    hand: sum of "Amount × tenure × ROI" divided by sum of "Weight"."""
    cfg = await load_config(s, user.company_id)
    scope = await _scope(s, user, region_id, branch_id)
    day = await _as_of(s, user, scope, as_of)
    first, last = calc.period_bounds(day, cfg.fy_start_month)[period]
    where = [*scope.conds, *ELIGIBLE, Disbursement.disbursement_date >= first, Disbursement.disbursement_date <= last]
    if product:
        where.append(Disbursement.product_class == product)
    weight = Disbursement.amount * Disbursement.tenure_months
    sums = (await s.execute(select(func.count(), func.count(func.distinct(Disbursement.loan_account)),
                                   func.coalesce(func.sum(Disbursement.amount), 0), func.coalesce(func.sum(weight), 0),
                                   func.coalesce(func.sum(weight * Disbursement.roi), 0)).where(*where))).one()
    q = select(Disbursement).where(*where).order_by(Disbursement.disbursement_date, Disbursement.loan_account,
                                                    Disbursement.disbursement_ref)
    if not format:
        q = q.offset((page - 1) * page_size).limit(page_size)
    items = []
    for d in (await s.execute(q)).scalars().all():
        loan = calc.Loan(d.loan_account, d.disbursement_date, d.amount, d.tenure_months, d.roi)
        code, name = scope.branch_label(d.branch_id)
        items.append({"id": str(d.id), "loan_account": d.loan_account, "disbursement_ref": d.disbursement_ref,
                      "disbursement_date": d.disbursement_date, "branch_code": code, "branch": name,
                      "region": scope.region_label(d.region_id), "product": d.product,
                      "product_class": d.product_class, "amount": d.amount, "tenure_months": d.tenure_months,
                      "roi": d.roi, "weight": loan.weight, "weighted_roi": loan.product})
    if format:
        body = [[i["loan_account"], i["disbursement_ref"], i["disbursement_date"].strftime("%d-%m-%Y"),
                 i["branch_code"], i["branch"], i["region"], i["product"], i["product_class"], i["amount"],
                 i["tenure_months"], i["roi"], i["weight"], i["weighted_roi"]] for i in items]
        return _file(format, f"irr_loans_{period}_{product or 'HL_NHL'}_{day}", DETAIL_HEADER, body, f"Loans {period}")
    records, accounts, amount, w_sum, p_sum = sums
    irr = Decimal(p_sum) / Decimal(w_sum) if w_sum else None
    return {
        "as_of": day, "period": period, "from": first, "to": last, "product": product, "decimals": cfg.decimals,
        "total": records, "page": page, "page_size": page_size,
        "items": [{**i, **{k: _num(i[k]) for k in ("amount", "tenure_months", "roi", "weight", "weighted_roi")}}
                  for i in items],
        "totals": {"records": records, "accounts": accounts, "amount": _num(Decimal(amount)),
                   "weight": _num(Decimal(w_sum)), "weighted_roi": _num(Decimal(p_sum)),
                   "irr": _pct(irr, cfg.decimals)},
    }


# ---------------------------------------------------------------- reconciliation
RECON_HEADER = ["Level", "Branch code", "Name", "Region", "Rows uploaded", "Included", "Excluded (cancelled / reversed)",
                "Exceptions (open)", "Included amount (₹)", "Number of loan accounts", "Weighted average IRR (%)"]


@router.get("/reconciliation")
async def reconciliation(date_from: date | None = None, date_to: date | None = None, product: Product | None = None,
                         region_id: uuid.UUID | None = None, branch_id: uuid.UUID | None = None,
                         format: Fmt | None = None, user: User = Depends(require_perm("irr.view")),
                         s: AsyncSession = Depends(get_session)):
    """What was uploaded for a period and what the IRR uses, by branch, by region and for the company, each worked
    out separately from the disbursement rows; the checks say whether branch totals = region totals = company total,
    and whether the year to date equals the sum of its months (BRD section 6, for the financial year of the period's
    end, in the same scope and product). Default period: month to date of the latest disbursement."""
    cfg = await load_config(s, user.company_id)
    scope = await _scope(s, user, region_id, branch_id)
    last = date_to or await _as_of(s, user, scope, None)
    first = date_from or last.replace(day=1)
    if first > last:
        raise HTTPException(422, "The start date is after the end date")
    D = Disbursement
    where = [*scope.conds, D.disbursement_date >= first, D.disbursement_date <= last]
    if product:
        where.append(D.product_class == product)
    ok = (D.excluded.is_(False), D.exception.is_(None))
    weight = D.amount * D.tenure_months
    cols = (func.count(), func.count().filter(*ok), func.count().filter(D.excluded.is_(True)),
            func.count().filter(*OPEN_EXCEPTION), func.coalesce(func.sum(D.amount).filter(*ok), 0),
            func.count(func.distinct(D.loan_account)).filter(*ok), func.coalesce(func.sum(weight).filter(*ok), 0),
            func.coalesce(func.sum(weight * D.roi).filter(*ok), 0))

    def block(r) -> dict:
        n, inc, exc, ex, amt, acc, w, p = r
        return {"rows": n, "included": inc, "excluded": exc, "exceptions": ex, "amount": Decimal(amt),
                "accounts": acc, "weight": Decimal(w), "weighted_roi": Decimal(p),
                "irr": Decimal(p) / Decimal(w) if w else None}

    by_branch = [(bid, block(r)) for bid, *r in (await s.execute(select(D.branch_id, *cols).where(*where)
                                                                 .group_by(D.branch_id))).all()]
    by_region = [(rid, block(r)) for rid, *r in (await s.execute(select(D.region_id, *cols).where(*where)
                                                                 .group_by(D.region_id))).all()]
    company = block((await s.execute(select(*cols).where(*where))).one())
    fields = ("rows", "included", "excluded", "exceptions", "amount", "weight", "weighted_roi")
    checks = []
    for name, parts in (("Branch totals = company total", by_branch), ("Region totals = company total", by_region)):
        diffs = [f for f in fields if sum((b[f] for _, b in parts), Decimal(0)) != company[f]]
        checks.append({"name": name, "ok": not diffs,
                       "detail": "All figures agree" if not diffs else f"Different: {', '.join(diffs)}"})
    # YTD validation: the year's numerator and denominator, worked out at once, against the sum of each month's
    fy_start = calc.period_bounds(last, cfg.fy_start_month)["YTD"][0]
    year_where = [*scope.conds, D.disbursement_date >= fy_start, D.disbursement_date <= last,
                  *([D.product_class == product] if product else [])]
    month = func.date_trunc("month", D.disbursement_date)
    by_month = [(m.date() if hasattr(m, "date") else m, block(r)) for m, *r in (await s.execute(
        select(month, *cols).where(*year_where).group_by(month).order_by(month))).all()]
    year = block((await s.execute(select(*cols).where(*year_where))).one())
    diffs = [f for f in fields if sum((b[f] for _, b in by_month), Decimal(0)) != year[f]]
    checks.append({"name": f"Year to date ({fy_start:%d-%m-%Y} to {last:%d-%m-%Y}) = sum of its months", "ok": not diffs,
                   "detail": "Numerator and denominator agree" if not diffs else f"Different: {', '.join(diffs)}"})

    def out(b: dict) -> dict:
        return {**{k: b[k] for k in ("rows", "included", "excluded", "exceptions", "accounts")},
                "amount": _num(b["amount"]), "irr": _pct(b["irr"], cfg.decimals)}

    branches = sorted(({"branch_id": str(bid), "code": scope.branch_label(bid)[0], "label": scope.branch_label(bid)[1],
                        "region": scope.region_label(scope.branches[bid].region_id) if bid in scope.branches else "",
                        **out(b)} for bid, b in by_branch), key=lambda r: (r["region"], r["label"]))
    regions = sorted(({"region_id": str(rid) if rid else None, "label": scope.region_label(rid), **out(b)}
                      for rid, b in by_region), key=lambda r: r["label"])
    total = {"label": "Company total" if scope.company_wide else "Total", **out(company)}
    months = [{"label": f"{m:%b %Y}", "month": m, "weight": _num(b["weight"]), "weighted_roi": _num(b["weighted_roi"]),
               **out(b)} for m, b in by_month]
    year_total = {"label": f"Year to date (from {fy_start:%d-%m-%Y})", "weight": _num(year["weight"]),
                  "weighted_roi": _num(year["weighted_roi"]), **out(year)}
    if format:
        def line(level: str, code: str, r: dict, region: str = "") -> list:
            return [level, code, r["label"], region, r["rows"], r["included"], r["excluded"], r["exceptions"],
                    r["amount"], r["accounts"], r["irr"]]
        body = ([line("Branch", r["code"], r, r["region"]) for r in branches]
                + [line("Region", "", r) for r in regions] + [line("Company", "", total)]
                + [line("Month", "", r) for r in months] + [line("Year to date", "", year_total)])
        return _file(format, f"irr_reconciliation_{first}_{last}", RECON_HEADER, body, "Reconciliation")
    return {"from": first, "to": last, "product": product, "decimals": cfg.decimals, "branches": branches,
            "regions": regions, "total": total, "months": months, "year": year_total, "checks": checks}


# ---------------------------------------------------------------- exceptions
EXC_HEADER = ["Loan account number", "Disbursement reference", "Disbursement date", "Branch", "Region", "Product",
              "Disbursed amount (₹)", "Tenure (months)", "ROI (%)", "Problem", "Corrected on"]


def _exception_out(d: Disbursement, scope: Scope) -> dict:
    return {"id": str(d.id), "loan_account": d.loan_account, "disbursement_ref": d.disbursement_ref,
            "disbursement_date": d.disbursement_date, "branch": scope.branch_label(d.branch_id)[1],
            "region": scope.region_label(d.region_id), "product": d.product, "product_class": d.product_class,
            "amount": _num(d.amount), "tenure_months": _num(d.tenure_months), "roi": _num(d.roi),
            "problem": d.exception, "corrected_at": d.corrected_at, "source_row": d.source_row}


@router.get("/exceptions")
async def list_exceptions(status: Literal["open", "corrected", "all"] = "open", date_from: date | None = None,
                          date_to: date | None = None, region_id: uuid.UUID | None = None,
                          branch_id: uuid.UUID | None = None, page: int = Query(1, ge=1),
                          page_size: int = Query(50, ge=1, le=500), format: Fmt | None = None,
                          user: User = Depends(require_perm("irr.view")), s: AsyncSession = Depends(get_session)):
    """Disbursements left out of the IRR because tenure or ROI is missing, zero or negative ("open"), and the ones a
    user has corrected since ("corrected")."""
    scope = await _scope(s, user, region_id, branch_id)
    D = Disbursement
    where = [*scope.conds, D.excluded.is_(False)]
    if status == "open":
        where.append(D.exception.is_not(None))
    elif status == "corrected":
        where.append(D.corrected_at.is_not(None))
    else:
        where.append((D.exception.is_not(None)) | (D.corrected_at.is_not(None)))
    if date_from:
        where.append(D.disbursement_date >= date_from)
    if date_to:
        where.append(D.disbursement_date <= date_to)
    total = (await s.execute(select(func.count()).where(*where))).scalar_one()
    q = select(D).where(*where).order_by(D.disbursement_date.desc(), D.loan_account)
    if not format:
        q = q.offset((page - 1) * page_size).limit(page_size)
    items = [_exception_out(d, scope) for d in (await s.execute(q)).scalars().all()]
    if format:
        body = [[i["loan_account"], i["disbursement_ref"], i["disbursement_date"].strftime("%d-%m-%Y"), i["branch"],
                 i["region"], i["product"], i["amount"], i["tenure_months"], i["roi"], i["problem"] or "Corrected",
                 i["corrected_at"].strftime("%d-%m-%Y %H:%M") if i["corrected_at"] else ""] for i in items]
        return _file(format, f"irr_exceptions_{status}", EXC_HEADER, body, "IRR exceptions")
    return {"items": items, "total": total, "page": page, "page_size": page_size}


class Correction(BaseModel):
    model_config = ConfigDict(extra="forbid")
    tenure_months: Decimal | None = None
    roi: Decimal | None = None


@router.patch("/exceptions/{disbursement_id}")
async def correct_exception(disbursement_id: uuid.UUID, body: Correction,
                            user: User = Depends(require_perm("irr.manage")), s: AsyncSession = Depends(get_session)):
    """Sets the tenure and / or ROI of a disbursement that was left out; once both are above 0 it counts in the IRR.
    Audited with the old and new values. A later upload of the same row replaces the correction."""
    scope = await _scope(s, user)
    d = (await s.execute(select(Disbursement).where(Disbursement.id == disbursement_id, *scope.conds))).scalar_one_or_none()
    if d is None:
        raise HTTPException(404, "Disbursement not found")
    if d.excluded:
        raise HTTPException(409, "This disbursement is cancelled or reversed, so it never counts in the IRR")
    if d.exception is None and d.corrected_at is None:
        raise HTTPException(409, "This disbursement has no exception. Correct it in the register and upload again")
    if body.tenure_months is None and body.roi is None:
        raise HTTPException(422, "Enter the tenure in months, the ROI, or both")
    if body.tenure_months is not None and not (0 < body.tenure_months < 1_000_000):
        raise HTTPException(422, "Tenure must be more than 0 months, for example 240")
    if body.roi is not None:
        problem = register.roi_problem(body.roi) if body.roi > 0 else "ROI must be more than 0, for example 9.25"
        if problem:
            raise HTTPException(422, problem)
    old = {"tenure_months": _num(d.tenure_months), "roi": _num(d.roi), "exception": d.exception}
    if body.tenure_months is not None:
        d.tenure_months = body.tenure_months
    if body.roi is not None:
        d.roi = body.roi
    d.exception = register.exception_reason(d.tenure_months, d.roi)
    d.corrected_by, d.corrected_at = user.id, datetime.now(timezone.utc)
    audit(s, user, "irr.exception.correct", "irr_disbursement", d.id, {
        "loan_account": d.loan_account, "old": old,
        "new": {"tenure_months": _num(d.tenure_months), "roi": _num(d.roi), "exception": d.exception}})
    await s.commit()
    return _exception_out(d, scope)


# ---------------------------------------------------------------- settings
@router.get("/settings")
async def get_settings(user: User = Depends(require_perm("irr.view")), s: AsyncSession = Depends(get_session)):
    return (await load_config(s, user.company_id)).model_dump()


@router.put("/settings")
async def put_settings(body: IrrConfig, user: User = Depends(require_perm("irr.manage")),
                       s: AsyncSession = Depends(get_session)):
    """Saves the settings. Disbursements already uploaded under a product name follow its new class."""
    row = await s.get(IrrSettings, user.company_id)
    old = IrrConfig.model_validate(row.data).model_dump() if row else IrrConfig().model_dump()
    data = body.model_dump()
    if row is None:
        s.add(IrrSettings(company_id=user.company_id, data=data, updated_by=user.id))
    else:
        row.data, row.updated_by = data, user.id
    moved = 0
    for key, cls in body.class_by_key().items():
        res = await s.execute(update(Disbursement).where(
            Disbursement.company_id == user.company_id, Disbursement.product_key == key,
            Disbursement.product_class != cls).values(product_class=cls))
        moved += res.rowcount or 0
    audit(s, user, "irr.settings", "irr_settings", user.company_id, {"old": old, "new": data, "reclassified": moved})
    await s.commit()
    return {**data, "reclassified": moved}


# ---------------------------------------------------------------- Disbursement Register upload
@router.get("/disbursements/template")
async def template(format: Fmt = "csv", user: User = Depends(require_perm("irr.manage"))):
    header = [register.LABELS[f] for f in register.COLUMNS]
    return _file(format, "disbursement_register_template", header, register.TEMPLATE_ROWS, "Disbursement register")


@router.get("/uploads")
async def upload_history(user: User = Depends(require_perm("irr.manage")), s: AsyncSession = Depends(get_session)):
    q = (select(ImportBatch, User.full_name).join(User, User.id == ImportBatch.uploaded_by)
         .where(ImportBatch.company_id == user.company_id, ImportBatch.kind == "disbursement")
         .order_by(ImportBatch.created_at.desc()).limit(100))
    return [{"id": str(b.id), "filename": b.filename, "uploaded_by": name, "created_at": b.created_at,
             "rows_total": b.rows_total, "rows_ok": b.rows_ok, "rows_error": b.rows_error, "summary": b.summary,
             "errors": b.errors or []} for b, name in (await s.execute(q)).all()]


@router.post("/disbursements")
async def upload_register(file: UploadFile = File(...), dry_run: bool = Form(False),
                          user: User = Depends(require_perm("irr.manage")), s: AsyncSession = Depends(get_session)):
    """The Disbursement Register (CSV or Excel). With dry_run=true nothing is saved and the answer says what would
    happen. A row already uploaded (same loan account + disbursement reference, or loan account + date + amount when
    there is no reference) is replaced, so uploading a file twice never counts a disbursement twice."""
    data = await file.read(MAX_FILE_BYTES + 1)
    if len(data) > MAX_FILE_BYTES:
        raise HTTPException(413, "The file is larger than 10 MB. Split it into smaller files")
    filename = file.filename or "upload"
    if not filename.lower().endswith((".csv", ".txt", ".xlsx", ".xlsm")):
        raise HTTPException(422, f"'{filename}' is not a CSV or Excel file. Save it as .csv or .xlsx and try again")
    rows = read_table(filename, data)
    labels = register.header_labels(filename, data)
    cols = register.column_map(labels)
    missing = register.missing_columns(cols)
    if missing:
        found = ", ".join(f"'{h}'" for h in labels if h) or "none"
        raise HTTPException(422, f"Missing column{'s' if len(missing) > 1 else ''}: {', '.join(missing)}. "
                                 f"Columns found in the file: {found}. Download the template for the expected headings.")
    if not rows:
        raise HTTPException(422, "The file has a heading row but no disbursements below it")
    cid = user.company_id
    cfg = await load_config(s, cid)
    branches: dict[str, tuple] = {}
    for b in (await s.execute(select(Branch).where(Branch.company_id == cid))).scalars().all():
        branches[norm_header(b.name)] = branches[norm_header(b.code)] = (b.id, b.region_id)
    parsed = register.parse_register(rows, cols, register.Lookups(branches, cfg.class_by_key(),
                                                                  await company_today(s, cid)))
    keys = [r["dedup_key"] for r in parsed.records]
    existing: set[str] = set()
    for i in range(0, len(keys), 5000):
        existing |= set((await s.execute(select(Disbursement.dedup_key).where(
            Disbursement.company_id == cid, Disbursement.dedup_key.in_(keys[i:i + 5000])))).scalars().all())
    error_rows = len({e["row"] for e in parsed.errors})
    summary = {"rows": len(rows), "new": len(keys) - len(existing), "replaced": len(existing),
               "excluded": sum(r["excluded"] for r in parsed.records),
               "exceptions": sum(1 for r in parsed.records if r["exception"]), "errors": error_rows}
    columns = {register.LABELS[f]: names[0] for f, names in cols.items() if names}
    result = {"dry_run": dry_run, "summary": summary, "errors": parsed.errors[:5000], "columns": columns}
    if dry_run:
        return result
    batch = ImportBatch(company_id=cid, kind="disbursement", filename=filename[:255], uploaded_by=user.id,
                        rows_total=len(rows), rows_error=error_rows, rows_ok=len(rows) - error_rows,
                        summary=summary, errors=parsed.errors[:2000])
    s.add(batch)
    await s.flush()
    replace = ("loan_account", "disbursement_ref", "disbursement_date", "product", "product_key", "product_class",
               "branch_id", "region_id", "amount", "tenure_months", "roi", "status", "excluded", "exception",
               "customer_name", "import_batch_id", "source_row")
    values = [{"id": uuid.uuid4(), "company_id": cid, "import_batch_id": batch.id, **r} for r in parsed.records]
    for i in range(0, len(values), 1000):
        stmt = pg_insert(Disbursement).values(values[i:i + 1000])
        await s.execute(stmt.on_conflict_do_update(
            constraint="uq_irr_disbursement_key",
            set_={**{c: stmt.excluded[c] for c in replace}, "corrected_by": None, "corrected_at": None,
                  "updated_at": func.now()}))
    audit(s, user, "import.disbursement", "import", batch.id, summary)
    await s.commit()
    return {**result, "batch_id": str(batch.id)}
