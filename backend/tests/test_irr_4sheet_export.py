import io
from openpyxl import load_workbook
from app.services.irr.export import build_complete_irr_workbook


def test_build_complete_irr_workbook_creates_all_four_sheets():
    sample_loans = [
        {
            "account_number": "AP/LBN/001",
            "disbursement_ref": "REF001",
            "customer_name": "Ramesh",
            "date": "2026-04-08",
            "month_start": "2026-04-01",
            "fy": "2026-2027",
            "amount": 150000.0,
            "tenure": 15.0,
            "roi": 20.0,
            "product_class": "HL",
            "branch": "LB Nagar",
            "region": "AP",
        },
        {
            "account_number": "TAN/USI/002",
            "disbursement_ref": "REF002",
            "customer_name": "Vadivel",
            "date": "2026-04-20",
            "month_start": "2026-04-01",
            "fy": "2026-2027",
            "amount": 312500.0,
            "tenure": 15.0,
            "roi": 17.0,
            "product_class": "NHL",
            "branch": "Usilampatti",
            "region": "ROTN-U",
        },
    ]

    period_summary = {
        "regions": [
            {
                "label": "AP",
                "periods": {
                    "TD": {"records": 0, "amount": 0, "irr": 0},
                    "MTD": {"records": 1, "amount": 150000, "irr": 20.0},
                    "YTD": {"records": 1, "amount": 150000, "irr": 20.0},
                },
                "branches": [
                    {
                        "label": "LB Nagar",
                        "periods": {
                            "TD": {"records": 0, "amount": 0, "irr": 0},
                            "MTD": {"records": 1, "amount": 150000, "irr": 20.0},
                            "YTD": {"records": 1, "amount": 150000, "irr": 20.0},
                        },
                    }
                ],
            }
        ],
        "total": {
            "periods": {
                "TD": {"records": 0, "amount": 0, "irr": 0},
                "MTD": {"records": 1, "amount": 150000, "irr": 20.0},
                "YTD": {"records": 1, "amount": 150000, "irr": 20.0},
            }
        },
    }

    product_summary = {
        "regions": [
            {
                "label": "AP",
                "classes": {
                    "HL": {"records": 1, "amount": 150000, "irr": 20.0},
                    "NHL": {"records": 0, "amount": 0, "irr": 0},
                    "TOTAL": {"records": 1, "amount": 150000, "irr": 20.0},
                },
                "branches": [
                    {
                        "label": "LB Nagar",
                        "classes": {
                            "HL": {"records": 1, "amount": 150000, "irr": 20.0},
                            "NHL": {"records": 0, "amount": 0, "irr": 0},
                            "TOTAL": {"records": 1, "amount": 150000, "irr": 20.0},
                        },
                    }
                ],
            }
        ],
        "total": {
            "classes": {
                "HL": {"records": 1, "amount": 150000, "irr": 20.0},
                "NHL": {"records": 0, "amount": 0, "irr": 0},
                "TOTAL": {"records": 1, "amount": 150000, "irr": 20.0},
            }
        },
    }

    raw_bytes = build_complete_irr_workbook(
        all_loans=sample_loans,
        period_loans=sample_loans[:1],
        period_summary=period_summary,
        product_summary=product_summary,
        as_of_str="2026-04-30",
    )

    assert isinstance(raw_bytes, bytes)
    assert len(raw_bytes) > 0

    wb = load_workbook(io.BytesIO(raw_bytes))
    sheet_names = wb.sheetnames

    assert len(sheet_names) == 5
    assert sheet_names == [
        "Analytics Dashboard",
        "All Disbursements",
        "Period Disbursements",
        "TD MTD YTD Summary",
        "Product MTD Summary",
    ]

    # Verify Sheet 0 Analytics Dashboard
    ws0 = wb["Analytics Dashboard"]
    assert "EXECUTIVE IRR & DISBURSEMENT ANALYTICS" in ws0["A1"].value
    assert ws0["A8"].value == "1. PRODUCT MIX BREAKDOWN (HL vs NHL)"
    assert ws0["A14"].value == "2. REGIONAL PERFORMANCE RANKING"

    # Verify Sheet 3 Header Structure
    ws3 = wb["TD MTD YTD Summary"]
    assert ws3["A1"].value == "REGION"
    assert ws3["B1"].value == "TD"
    assert ws3["E1"].value == "MTD"
    assert ws3["H1"].value == "YTD"

    assert ws3["B2"].value == "No."
    assert ws3["C2"].value == "vol"
    assert ws3["D2"].value == "IRR"

    # Verify Sheet 4 Header Structure
    ws4 = wb["Product MTD Summary"]
    assert ws4["A1"].value == "REGION"
    assert ws4["B1"].value == "HL MTD"
    assert ws4["E1"].value == "NHL MTD"
    assert ws4["H1"].value == "TOTAL MTD"

    assert ws4["B2"].value == "No."
    assert ws4["C2"].value == "vol"
    assert ws4["D2"].value == "IRR"
