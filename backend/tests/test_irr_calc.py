"""The weighted average IRR formula (BRD section 6) and the register reader, without a database."""
import random
from datetime import date, datetime
from decimal import Decimal as D

from app.services.irr import calc, export, register
from app.services.irr.settings import IrrConfig

A = calc.Loan("A", date(2026, 11, 5), D("3000000"), D("240"), D("9"))
B = calc.Loan("B", date(2026, 11, 5), D("500000"), D("60"), D("12"))


def test_brd_example_is_9_12_not_amount_weighted_or_average_tenure():
    irr = calc.weighted_irr([A, B])
    assert irr == D("9.12")  # 68,400 / 7,500 in lakh-months
    assert A.weight + B.weight == D("750000000") and A.product + B.product == D("6840000000")
    amounts_only = (A.amount * A.roi + B.amount * B.roi) / (A.amount + B.amount)
    assert calc.rounded(amounts_only) == D("9.43") and calc.rounded(irr) != calc.rounded(amounts_only)


def test_empty_group_has_no_irr_not_zero():
    assert calc.weighted_irr([]) is None
    assert calc.Group().irr is None and calc.rounded(None) is None
    out = calc.summarise([A], date(2026, 11, 6))
    assert out[None]["TD"].irr is None and out[None]["MTD"].irr == D(9)


def test_mtd_and_ytd_are_cumulative_not_averages_of_days_or_branches():
    day1 = calc.Loan("L1", date(2026, 11, 2), D("1000000"), D("240"), D("8"), branch_id="b1")
    day2 = calc.Loan("L2", date(2026, 11, 3), D("100000"), D("12"), D("14"), branch_id="b2")
    out = calc.summarise([day1, day2], date(2026, 11, 3))
    mtd = out[None]["MTD"].irr
    assert mtd == (day1.product + day2.product) / (day1.weight + day2.weight)
    assert calc.rounded(mtd) == D("8.03")
    assert calc.rounded(mtd) != calc.rounded((D(8) + D(14)) / 2)  # not the average of the two days / branches
    by_branch = calc.summarise([day1, day2], date(2026, 11, 3), key=lambda x: x.branch_id)
    assert by_branch["b1"]["MTD"].irr == D(8) and by_branch["b2"]["TD"].irr == D(14)
    assert by_branch["b1"]["TD"].irr is None  # nothing on 3 Nov in b1


def test_accounts_are_distinct_loan_accounts_tranches_count_once():
    t1 = calc.Loan("HL1", date(2026, 10, 20), D("1000000"), D("240"), D("9"))
    t2 = calc.Loan("HL1", date(2026, 11, 4), D("500000"), D("240"), D("9"))
    other = calc.Loan("HL2", date(2026, 11, 4), D("200000"), D("120"), D("10"))
    out = calc.summarise([t1, t2, other], date(2026, 11, 4))[None]
    assert out["YTD"].accounts == 2 and out["YTD"].records == 3  # HL1 once in the year
    assert out["MTD"].accounts == 2 and out["TD"].accounts == 2
    oct_ = calc.summarise([t1, t2, other], date(2026, 10, 31))[None]
    assert oct_["MTD"].accounts == 1  # and once in October's month to date
    # each tranche is weighted by its own amount
    assert out["YTD"].weight == D("1000000") * 240 + D("500000") * 240 + D("200000") * 120


def test_financial_year_boundary_31_march_1_april():
    march = calc.Loan("M", date(2026, 3, 31), D("1000000"), D("240"), D("8"))
    april = calc.Loan("P", date(2026, 4, 1), D("1000000"), D("240"), D("10"))
    assert calc.fy_start(date(2026, 3, 31)) == date(2025, 4, 1)
    assert calc.fy_start(date(2026, 4, 1)) == date(2026, 4, 1)
    on_31 = calc.summarise([march, april], date(2026, 3, 31))[None]
    assert on_31["YTD"].irr == D(8) and on_31["YTD"].accounts == 1
    on_1 = calc.summarise([march, april], date(2026, 4, 1))[None]
    assert on_1["YTD"].irr == D(10) and on_1["YTD"].accounts == 1  # the new year starts afresh
    # a January year start (setting)
    jan = calc.summarise([march, april], date(2026, 4, 1), fy_start_month=1)[None]
    assert jan["YTD"].accounts == 2 and jan["YTD"].irr == D(9)
    assert calc.period_bounds(date(2026, 11, 9)) == {"TD": (date(2026, 11, 9), date(2026, 11, 9)),
                                                      "MTD": (date(2026, 11, 1), date(2026, 11, 9)),
                                                      "YTD": (date(2026, 4, 1), date(2026, 11, 9))}


def test_every_group_irr_lies_between_its_lowest_and_highest_roi():
    rnd = random.Random(20261109)
    branches = ["b1", "b2", "b3", "b4"]
    loans = [calc.Loan(f"L{rnd.randint(1, 300)}", date(2026, rnd.randint(4, 11), rnd.randint(1, 28)),
                       D(rnd.randint(50_000, 9_000_000)), D(rnd.choice([12, 36, 60, 120, 180, 240, 300])),
                       D(rnd.randint(750, 1800)) / 100, branch_id=rnd.choice(branches)) for _ in range(800)]
    as_of = date(2026, 11, 28)
    for key in (None, lambda x: x.branch_id):
        for groups in calc.summarise(loans, as_of, key=key).values():
            for g in groups.values():
                if g.records:
                    assert g.min_roi <= g.irr <= g.max_roi, (g.min_roi, g.irr, g.max_roi)
    # the company total is worked out from the loans, and equals the ratio of the summed branch sums
    by_branch = calc.summarise(loans, as_of, key=lambda x: x.branch_id)
    total = calc.summarise(loans, as_of)[None]["YTD"]
    assert total.irr == sum(g["YTD"].product for g in by_branch.values()) / sum(g["YTD"].weight for g in by_branch.values())


def test_rounding_and_band():
    assert calc.rounded(D("9.125")) == D("9.13") and calc.rounded(D("9.124999"), 3) == D("9.125")
    band = (D(8), D(14))
    assert calc.outside_band(D("7.994"), band) == "below" and calc.outside_band(D("7.996"), band) is None
    assert calc.outside_band(D("14.01"), band) == "above" and calc.outside_band(None, band) is None


def _cols(*labels):
    return register.column_map(list(labels))


def _parse(rows, labels, products=None):
    look = register.Lookups({"b1": ("B1", "R1"), "branch one": ("B1", "R1")},
                            products or IrrConfig().class_by_key(), date(2026, 11, 9))
    return register.parse_register(rows, _cols(*labels), look)


LABELS = ["LAN", "Tranche No", "Date of Disbursement", "Product", "Branch Code", "Disbursed Amount (Rs.)",
          "Tenure (Months)", "ROI %", "Status"]


def test_register_reads_synonyms_and_exact_row_errors():
    rows = [
        {"_row": 2, "lan": "hl001", "tranche no": 1.0, "date of disbursement": datetime(2026, 11, 5), "product": "home loan",
         "branch code": "B1", "disbursed amount rs": "30,00,000", "tenure months": 240, "roi": "9.00%", "status": "Disbursed"},
        {"_row": 7, "lan": "HL002", "tranche no": None, "date of disbursement": "31/02/2026", "product": "Home Loan",
         "branch code": "B1", "disbursed amount rs": 100000, "tenure months": 240, "roi": 9, "status": None},
        {"_row": 8, "lan": "", "tranche no": None, "date of disbursement": "05-11-2026", "product": "Personal Loan",
         "branch code": "Nowhere", "disbursed amount rs": "abc", "tenure months": "20 years", "roi": 0.095, "status": None},
        {"_row": 9, "lan": "HL001", "tranche no": "1", "date of disbursement": "05-11-2026", "product": "LAP",
         "branch code": "branch one", "disbursed amount rs": -5, "tenure months": None, "roi": None, "status": None},
    ]
    out = _parse(rows, LABELS)
    assert len(out.records) == 1
    r = out.records[0]
    assert (r["loan_account"], r["disbursement_ref"], r["amount"], r["roi"], r["product_class"]) == (
        "HL001", "1", D("3000000.00"), D("9.00"), "HL")
    assert r["dedup_key"] == "R|HL001|1" and r["exception"] is None and r["excluded"] is False
    errs = {(e["row"], e["column"]): e for e in out.errors}
    assert errs[(7, "Date of Disbursement")] == {
        "row": 7, "column": "Date of Disbursement", "value": "31/02/2026",
        "message": "Not a real date. Use DD-MM-YYYY, for example 05-11-2026"}
    assert errs[(8, "LAN")]["message"] == "Empty. Every row needs the loan account number"
    assert errs[(8, "Product")]["value"] == "Personal Loan"
    assert "not in the product mapping" in errs[(8, "Product")]["message"]
    assert errs[(8, "Branch Code")]["value"] == "Nowhere"
    assert errs[(8, "Disbursed Amount (Rs.)")]["message"] == (
        "Not a number. Enter the amount in rupees using digits only, for example 3000000")
    assert errs[(8, "Tenure (Months)")]["value"] == "20 years"
    assert errs[(8, "ROI %")]["message"].startswith("Looks like a fraction, not a percentage")
    assert errs[(9, "Disbursed Amount (Rs.)")]["value"] == "-5"
    assert errs[(9, "Disbursed Amount (Rs.)")]["message"].startswith("Must be more than 0")


def test_register_exceptions_exclusions_and_duplicates_in_the_file():
    base = {"tranche no": None, "date of disbursement": "01-11-2026", "product": "LAP", "branch code": "B1",
            "disbursed amount rs": 500000}
    rows = [
        {"_row": 2, "lan": "L1", **base, "tenure months": None, "roi": 12, "status": None},
        {"_row": 3, "lan": "L2", **base, "tenure months": 0, "roi": -1, "status": None},
        {"_row": 4, "lan": "L3", **base, "tenure months": 60, "roi": 12, "status": "CANCELLED"},
        {"_row": 5, "lan": "L4", **base, "tenure months": 60, "roi": 12, "status": "reversal"},
        {"_row": 6, "lan": "L1", **base, "tenure months": 60, "roi": 12, "status": None},
    ]
    out = _parse(rows, LABELS)
    by = {r["loan_account"]: r for r in out.records}
    assert by["L1"]["exception"] == "Tenure missing" and by["L2"]["exception"] == "Tenure is 0; ROI is negative (-1)"
    assert by["L3"]["excluded"] and by["L4"]["excluded"] and by["L3"]["exception"] is None
    assert out.errors == [{"row": 6, "column": "LAN", "value": "L1", "message": (
        "Same loan account, date and amount as row 2, and no disbursement reference. Keep one row, or add the "
        "reference to tell the tranches apart")}]


def test_missing_columns_are_named():
    cols = _cols("Loan No", "Date", "Product", "Amount", "Tenure")
    assert register.missing_columns(cols) == ["Branch", "ROI %"]


def test_exports_are_csv_with_bom_and_real_xlsx():
    import io

    from openpyxl import load_workbook

    csv_bytes = export.to_csv(["Branch", "IRR"], [["=cmd()", D("9.12")], ["Branch One", None]])
    assert csv_bytes.startswith("﻿".encode()) and b"'=cmd()" in csv_bytes and b"9.12" in csv_bytes
    wb = load_workbook(io.BytesIO(export.to_xlsx(["Branch", "IRR"], [["Branch One", D("9.12")]])))
    assert [c.value for c in wb.active[2]] == ["Branch One", 9.12]
