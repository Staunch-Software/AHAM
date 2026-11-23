"""Report tables as CSV or Excel (.xlsx) files. Pure: header + rows in, bytes out."""
import csv
import io
from collections.abc import Iterable, Sequence
from decimal import Decimal
from typing import Any

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

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
    return ("\ufeff" + buf.getvalue()).encode("utf-8")  # BOM makes Excel read ₹ and names correctly


def to_xlsx(header: Sequence[str], rows: Iterable[Sequence[Any]], sheet: str = "IRR") -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.title = sheet[:31]
    ws.views.sheetView[0].showGridLines = True

    header_fill = PatternFill(start_color="1E1B4B", end_color="1E1B4B", fill_type="solid")
    header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    thin_border = Border(
        left=Side(style="thin", color="CBD5E1"),
        right=Side(style="thin", color="CBD5E1"),
        top=Side(style="thin", color="CBD5E1"),
        bottom=Side(style="thin", color="CBD5E1"),
    )

    ws.append(list(header))
    for col_idx in range(1, len(header) + 1):
        cell = ws.cell(row=1, column=col_idx)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = thin_border

    ws.row_dimensions[1].height = 26

    for r_idx, r in enumerate(rows, start=2):
        row_vals = [_safe(v) for v in r]
        ws.append(row_vals)
        for col_idx in range(1, len(row_vals) + 1):
            cell = ws.cell(row=r_idx, column=col_idx)
            cell.border = thin_border
            cell.font = Font(name="Calibri", size=10)
            if isinstance(cell.value, (int, float, Decimal)):
                cell.alignment = Alignment(horizontal="right", vertical="center")
            else:
                cell.alignment = Alignment(horizontal="left", vertical="center")

    for col in ws.columns:
        max_len = max(len(str(cell.value or "")) for cell in col)
        col_letter = get_column_letter(col[0].column)
        ws.column_dimensions[col_letter].width = max(12, min(40, max_len + 3))

    ws.freeze_panes = "A2"
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def build_complete_irr_workbook(
    all_loans: list[dict],
    period_loans: list[dict],
    period_summary: dict,
    product_summary: dict,
    as_of_str: str,
) -> bytes:
    """Builds the comprehensive Executive IRR Workbook with Analytics Dashboard:
    Sheet 1: Analytics Dashboard (KPI Cards, Product Mix, Regional Rank, Ticket Size & ROI Bands)
    Sheet 2: All Disbursements (Full Year / Range register with loan details & bottom totals)
    Sheet 3: Period Disbursements (Filtered MTD / active period loans with totals)
    Sheet 4: TD MTD YTD Summary (2-tier merged headers: TD, MTD, YTD over No., vol in Lakhs, IRR)
    Sheet 5: Product MTD Summary (2-tier merged headers: HL MTD, NHL MTD, TOTAL MTD over No., vol, IRR)
    """
    wb = Workbook()

    # Styling tokens
    fill_navy = PatternFill(start_color="1E1B4B", end_color="1E1B4B", fill_type="solid")
    fill_subnavy = PatternFill(start_color="283079", end_color="283079", fill_type="solid")
    fill_region = PatternFill(start_color="F1F5F9", end_color="F1F5F9", fill_type="solid")
    fill_total = PatternFill(start_color="FEF9C3", end_color="FEF9C3", fill_type="solid")
    fill_card = PatternFill(start_color="F8FAFC", end_color="F8FAFC", fill_type="solid")
    fill_accent = PatternFill(start_color="EFF6FF", end_color="EFF6FF", fill_type="solid")

    font_banner = Font(name="Calibri", size=14, bold=True, color="1E1B4B")
    font_subbanner = Font(name="Calibri", size=11, color="64748B")
    font_section = Font(name="Calibri", size=12, bold=True, color="1E1B4B")
    font_white_bold = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    font_card_num = Font(name="Calibri", size=15, bold=True, color="1E1B4B")
    font_card_lbl = Font(name="Calibri", size=9, bold=True, color="64748B")
    font_bold = Font(name="Calibri", size=10, bold=True, color="0F172A")
    font_regular = Font(name="Calibri", size=10, color="1E293B")
    font_branch = Font(name="Calibri", size=10, color="334155")

    thin_border = Border(
        left=Side(style="thin", color="CBD5E1"),
        right=Side(style="thin", color="CBD5E1"),
        top=Side(style="thin", color="CBD5E1"),
        bottom=Side(style="thin", color="CBD5E1"),
    )
    total_border = Border(
        left=Side(style="thin", color="CBD5E1"),
        right=Side(style="thin", color="CBD5E1"),
        top=Side(style="thin", color="0F172A"),
        bottom=Side(style="double", color="0F172A"),
    )

    align_center = Alignment(horizontal="center", vertical="center")
    align_left = Alignment(horizontal="left", vertical="center")
    align_right = Alignment(horizontal="right", vertical="center")

    num_fmt_int = "#,##0"
    num_fmt_lakh = "#,##0.00"
    num_fmt_pct = "0.00%"
    num_fmt_currency = "#,##0"

    def _safe_irr_val(val: Any) -> float:
        if val is None or val == "":
            return 0.0
        if isinstance(val, (int, float, Decimal)):
            return float(val) / 100.0
        try:
            val_str = str(val).strip().rstrip("%")
            return float(val_str) / 100.0
        except (ValueError, TypeError):
            return 0.0

    # -------------------------------------------------------------
    # 0. SHEET 1: Analytics Dashboard (Executive Overview)
    # -------------------------------------------------------------
    ws0 = wb.active
    ws0.title = "Analytics Dashboard"
    ws0.views.sheetView[0].showGridLines = True

    # Title Banner
    ws0.cell(row=1, column=1, value="AHAM HOUSING FINANCE · EXECUTIVE IRR & DISBURSEMENT ANALYTICS").font = font_banner
    ws0.cell(row=2, column=1, value=f"Reporting Period As Of: {as_of_str} · Generated for Executive Management").font = font_subbanner

    tot_n = len(all_loans)
    tot_amt = sum(l.get("amount", 0) for l in all_loans)
    tot_lakhs = tot_amt / 100000.0
    tot_cr = tot_amt / 10000000.0
    avg_ten = (sum(l.get("tenure", 0) for l in all_loans) / tot_n) if tot_n > 0 else 0
    prod_sum = sum(l.get("amount", 0) * l.get("tenure", 0) * (l.get("roi", 0) / 100.0 if l.get("roi", 0) > 1 else l.get("roi", 0)) for l in all_loans)
    wt_irr = (prod_sum / (tot_amt * avg_ten)) if (tot_amt > 0 and avg_ten > 0) else 0

    # KPI Metric Cards (Rows 4-5)
    cards = [
        ("TOTAL VOLUME (₹ CR)", f"₹{tot_cr:.2f} Cr", f"{tot_lakhs:,.2f} Lakhs", 1, 2),
        ("TOTAL DISBURSEMENTS", f"{tot_n:,}", "Disbursed Accounts", 4, 5),
        ("PORTFOLIO WEIGHTED IRR", f"{wt_irr:.2%}", "Annualized ROI", 7, 8),
        ("AVERAGE TENURE", f"{avg_ten:.1f} Yrs", "Weighted Maturity", 10, 11),
    ]

    for title, val, sub, sc, ec in cards:
        ws0.merge_cells(start_row=4, start_column=sc, end_row=4, end_column=ec)
        ws0.merge_cells(start_row=5, start_column=sc, end_row=5, end_column=ec)
        ws0.merge_cells(start_row=6, start_column=sc, end_row=6, end_column=ec)

        c1 = ws0.cell(row=4, column=sc, value=title)
        c1.font = font_card_lbl
        c1.fill = fill_card
        c1.alignment = align_center

        c2 = ws0.cell(row=5, column=sc, value=val)
        c2.font = font_card_num
        c2.fill = fill_card
        c2.alignment = align_center

        c3 = ws0.cell(row=6, column=sc, value=sub)
        c3.font = font_subbanner
        c3.fill = fill_card
        c3.alignment = align_center

        for r in (4, 5, 6):
            for c in range(sc, ec + 1):
                ws0.cell(row=r, column=c).border = thin_border

    # Section 1: Product Mix (HL vs NHL) - Row 8
    ws0.cell(row=8, column=1, value="1. PRODUCT MIX BREAKDOWN (HL vs NHL)").font = font_section

    prod_headers = ["Product Class", "Loan Count", "% Count", "Volume (₹ Lakhs)", "% Volume", "Weighted IRR (%)"]
    ws0.row_dimensions[9].height = 22
    for c_idx, h in enumerate(prod_headers, start=1):
        c = ws0.cell(row=9, column=c_idx, value=h)
        c.fill = fill_navy
        c.font = font_white_bold
        c.alignment = align_center
        c.border = thin_border

    hl_loans = [l for l in all_loans if l.get("product_class", "HL").upper() == "HL"]
    nhl_loans = [l for l in all_loans if l.get("product_class", "").upper() == "NHL"]

    def calc_mix(loans):
        cn = len(loans)
        cv = sum(l.get("amount", 0) for l in loans) / 100000.0
        cten = (sum(l.get("tenure", 0) for l in loans) / cn) if cn else 0
        cprod = sum(l.get("amount", 0) * l.get("tenure", 0) * (l.get("roi", 0) / 100.0 if l.get("roi", 0) > 1 else l.get("roi", 0)) for l in loans)
        cirr = (cprod / (sum(l.get("amount", 0) for l in loans) * cten)) if (cn and cten) else 0
        return cn, cv, cirr

    hl_n, hl_v, hl_irr = calc_mix(hl_loans)
    nhl_n, nhl_v, nhl_irr = calc_mix(nhl_loans)

    prod_rows = [
        ("Home Loan (HL)", hl_n, (hl_n / tot_n) if tot_n else 0, hl_v, (hl_v / tot_lakhs) if tot_lakhs else 0, hl_irr),
        ("Non-Home Loan (NHL)", nhl_n, (nhl_n / tot_n) if tot_n else 0, nhl_v, (nhl_v / tot_lakhs) if tot_lakhs else 0, nhl_irr),
        ("Total Portfolio", tot_n, 1.0, tot_lakhs, 1.0, wt_irr),
    ]

    for p_idx, (pname, cn, cpct, cv, cvpct, cirr) in enumerate(prod_rows, start=10):
        is_tot = p_idx == 12
        r_vals = [pname, cn, cpct, cv, cvpct, cirr]
        for c_idx, val in enumerate(r_vals, start=1):
            cell = ws0.cell(row=p_idx, column=c_idx, value=val)
            cell.font = font_bold if is_tot else font_regular
            cell.border = total_border if is_tot else thin_border
            if is_tot:
                cell.fill = fill_total
            if c_idx == 1:
                cell.alignment = align_left
            elif c_idx == 2:
                cell.number_format = num_fmt_int
                cell.alignment = align_right
            elif c_idx in (3, 5, 6):
                cell.number_format = num_fmt_pct
                cell.alignment = align_right
            elif c_idx == 4:
                cell.number_format = num_fmt_lakh
                cell.alignment = align_right

    # Section 2: Regional Performance Ranking - Row 14
    ws0.cell(row=14, column=1, value="2. REGIONAL PERFORMANCE RANKING").font = font_section

    reg_headers = ["Rank", "Region", "Disbursed Loans", "Volume (₹ Lakhs)", "Volume Share (%)", "Weighted IRR (%)"]
    ws0.row_dimensions[15].height = 22
    for c_idx, h in enumerate(reg_headers, start=1):
        c = ws0.cell(row=15, column=c_idx, value=h)
        c.fill = fill_navy
        c.font = font_white_bold
        c.alignment = align_center
        c.border = thin_border

    # Aggregate by region
    by_region_map: dict[str, list] = {}
    for l in all_loans:
        by_region_map.setdefault(l.get("region", "OTHER").upper(), []).append(l)

    reg_ranked = []
    for r_name, r_loans in by_region_map.items():
        rcn, rcv, rcirr = calc_mix(r_loans)
        reg_ranked.append((r_name, rcn, rcv, rcirr))
    reg_ranked.sort(key=lambda x: x[2], reverse=True)

    r_row = 16
    for rank, (r_name, rcn, rcv, rcirr) in enumerate(reg_ranked, start=1):
        share = (rcv / tot_lakhs) if tot_lakhs else 0
        vals = [rank, r_name, rcn, rcv, share, rcirr]
        for c_idx, val in enumerate(vals, start=1):
            cell = ws0.cell(row=r_row, column=c_idx, value=val)
            cell.font = font_regular
            cell.border = thin_border
            if c_idx in (1, 2):
                cell.alignment = align_center if c_idx == 1 else align_left
            elif c_idx == 3:
                cell.number_format = num_fmt_int
                cell.alignment = align_right
            elif c_idx == 4:
                cell.number_format = num_fmt_lakh
                cell.alignment = align_right
            elif c_idx in (5, 6):
                cell.number_format = num_fmt_pct
                cell.alignment = align_right
        r_row += 1

    # Section 3: Ticket Size Distribution
    t_start = r_row + 1
    ws0.cell(row=t_start, column=1, value="3. TICKET SIZE DISTRIBUTION").font = font_section
    t_headers = ["Ticket Size Band", "Count", "% Count", "Volume (₹ Lakhs)", "% Volume", "Weighted IRR (%)"]
    ws0.row_dimensions[t_start + 1].height = 22
    for c_idx, h in enumerate(t_headers, start=1):
        c = ws0.cell(row=t_start + 1, column=c_idx, value=h)
        c.fill = fill_navy
        c.font = font_white_bold
        c.alignment = align_center
        c.border = thin_border

    ticket_bands = [
        ("< ₹5 Lakhs", lambda a: a < 500000),
        ("₹5L – ₹15 Lakhs", lambda a: 500000 <= a < 1500000),
        ("₹15L – ₹30 Lakhs", lambda a: 1500000 <= a < 3000000),
        ("≥ ₹30 Lakhs", lambda a: a >= 3000000),
    ]

    t_row = t_start + 2
    for band_name, fn in ticket_bands:
        b_loans = [l for l in all_loans if fn(l.get("amount", 0))]
        bcn, bcv, bcirr = calc_mix(b_loans)
        b_pct = (bcn / tot_n) if tot_n else 0
        b_vpct = (bcv / tot_lakhs) if tot_lakhs else 0
        vals = [band_name, bcn, b_pct, bcv, b_vpct, bcirr]
        for c_idx, val in enumerate(vals, start=1):
            cell = ws0.cell(row=t_row, column=c_idx, value=val)
            cell.font = font_regular
            cell.border = thin_border
            if c_idx == 1:
                cell.alignment = align_left
            elif c_idx == 2:
                cell.number_format = num_fmt_int
                cell.alignment = align_right
            elif c_idx == 4:
                cell.number_format = num_fmt_lakh
                cell.alignment = align_right
            elif c_idx in (3, 5, 6):
                cell.number_format = num_fmt_pct
                cell.alignment = align_right
        t_row += 1

    # Auto-fit column widths for Sheet 0
    ws0.column_dimensions["A"].width = 24
    ws0.column_dimensions["B"].width = 16
    ws0.column_dimensions["C"].width = 16
    ws0.column_dimensions["D"].width = 18
    ws0.column_dimensions["E"].width = 16
    ws0.column_dimensions["F"].width = 18
    for c_idx in range(7, 13):
        ws0.column_dimensions[get_column_letter(c_idx)].width = 16
    fill_region = PatternFill(start_color="F1F5F9", end_color="F1F5F9", fill_type="solid")
    fill_total = PatternFill(start_color="FEF9C3", end_color="FEF9C3", fill_type="solid")

    font_white_bold = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    font_bold = Font(name="Calibri", size=10, bold=True, color="0F172A")
    font_regular = Font(name="Calibri", size=10, color="1E293B")
    font_branch = Font(name="Calibri", size=10, color="334155")

    thin_border = Border(
        left=Side(style="thin", color="CBD5E1"),
        right=Side(style="thin", color="CBD5E1"),
        top=Side(style="thin", color="CBD5E1"),
        bottom=Side(style="thin", color="CBD5E1"),
    )
    total_border = Border(
        left=Side(style="thin", color="CBD5E1"),
        right=Side(style="thin", color="CBD5E1"),
        top=Side(style="thin", color="0F172A"),
        bottom=Side(style="double", color="0F172A"),
    )

    align_center = Alignment(horizontal="center", vertical="center")
    align_left = Alignment(horizontal="left", vertical="center")
    align_right = Alignment(horizontal="right", vertical="center")

    num_fmt_int = "#,##0"
    num_fmt_lakh = "#,##0.00"
    num_fmt_pct = "0.00%"
    num_fmt_currency = "#,##0"

    def _safe_irr_val(val: Any) -> float:
        if val is None or val == "":
            return 0.0
        if isinstance(val, (int, float, Decimal)):
            return float(val) / 100.0
        try:
            val_str = str(val).strip().rstrip("%")
            return float(val_str) / 100.0
        except (ValueError, TypeError):
            return 0.0

    raw_headers = [
        "UNIQUE ID",
        "location",
        "region",
        "NAME",
        "Date",
        "Month OF DISB",
        "DATE OF DISB",
        "DISBURSED AMOUNT",
        "HL/NHL",
        "TENURE",
        "interest",
        "PRODUCT WITH TENURE",
    ]

    def populate_raw_sheet(ws, loans_list, title):
        ws.title = title
        ws.views.sheetView[0].showGridLines = True
        ws.append(raw_headers)
        ws.row_dimensions[1].height = 24
        for c_idx in range(1, len(raw_headers) + 1):
            cell = ws.cell(row=1, column=c_idx)
            cell.fill = fill_navy
            cell.font = font_white_bold
            cell.alignment = align_center
            cell.border = thin_border

        total_amount = Decimal(0)
        total_tenure = Decimal(0)
        total_product = Decimal(0)
        n = len(loans_list)

        for r_idx, l in enumerate(loans_list, start=2):
            amt = Decimal(str(l.get("amount", 0)))
            ten = Decimal(str(l.get("tenure", 0)))
            roi = Decimal(str(l.get("roi", 0))) / Decimal(100) if l.get("roi", 0) > 1 else Decimal(str(l.get("roi", 0)))
            prod = amt * ten * roi

            total_amount += amt
            total_tenure += ten
            total_product += prod

            row_data = [
                l.get("account_number") or l.get("disbursement_ref") or "",
                (l.get("branch") or "").upper(),
                (l.get("region") or "").upper(),
                l.get("customer_name") or "",
                str(l.get("date") or ""),
                str(l.get("month_start") or ""),
                str(l.get("fy") or ""),
                float(amt),
                (l.get("product_class") or "HL").upper(),
                float(ten),
                float(roi),
                float(prod),
            ]
            ws.append(row_data)
            for c_idx in range(1, len(row_data) + 1):
                c = ws.cell(row=r_idx, column=c_idx)
                c.border = thin_border
                c.font = font_regular
                if c_idx in (8, 12):
                    c.number_format = num_fmt_currency
                    c.alignment = align_right
                elif c_idx == 10:
                    c.number_format = "0.0"
                    c.alignment = align_right
                elif c_idx == 11:
                    c.number_format = num_fmt_pct
                    c.alignment = align_right
                else:
                    c.alignment = align_left

        # Summary rows at bottom
        start_row = len(loans_list) + 3
        # Empty space
        sum_row = start_row + 1
        ws.cell(row=sum_row, column=7, value="Total Disbursed:").font = font_bold
        ws.cell(row=sum_row, column=7).alignment = align_right

        c_amt = ws.cell(row=sum_row, column=8, value=float(total_amount))
        c_amt.font = font_bold
        c_amt.number_format = num_fmt_currency
        c_amt.border = total_border

        avg_tenure = (total_tenure / Decimal(n)) if n > 0 else Decimal(0)
        c_ten = ws.cell(row=sum_row, column=10, value=float(avg_tenure))
        c_ten.font = font_bold
        c_ten.number_format = "0.00"
        c_ten.border = total_border

        c_prod = ws.cell(row=sum_row, column=12, value=float(total_product))
        c_prod.font = font_bold
        c_prod.number_format = num_fmt_currency
        c_prod.border = total_border

        # Weighted IRR row
        irr_row = sum_row + 2
        weighted_irr = (total_product / (total_amount * avg_tenure)) if (total_amount > 0 and avg_tenure > 0) else Decimal(0)
        ws.cell(row=irr_row, column=7, value="Weighted IRR:").font = font_bold
        ws.cell(row=irr_row, column=7).alignment = align_right
        c_irr = ws.cell(row=irr_row, column=8, value=float(weighted_irr))
        c_irr.font = font_bold
        c_irr.number_format = num_fmt_pct
        c_irr.fill = fill_total
        c_irr.border = total_border

        for col in ws.columns:
            m_len = max(len(str(cell.value or "")) for cell in col)
            ws.column_dimensions[get_column_letter(col[0].column)].width = max(11, min(36, m_len + 3))
        ws.freeze_panes = "A2"

    # 1. Sheet 2: All Disbursements
    ws1 = wb.create_sheet("All Disbursements")
    populate_raw_sheet(ws1, all_loans, "All Disbursements")

    # 2. Sheet 3: Period Disbursements
    ws2 = wb.create_sheet("Period Disbursements")
    populate_raw_sheet(ws2, period_loans, "Period Disbursements")

    # 3. Sheet 3: TD MTD YTD Summary
    ws3 = wb.create_sheet("TD MTD YTD Summary")
    ws3.views.sheetView[0].showGridLines = True

    # Two-tier header setup
    ws3.merge_cells("A1:A2")
    ws3.cell(row=1, column=1, value="REGION")
    ws3.cell(row=1, column=1).alignment = align_center

    periods = [("TD", 2, 4), ("MTD", 5, 7), ("YTD", 8, 10)]
    for p_name, start_col, end_col in periods:
        ws3.merge_cells(start_row=1, start_column=start_col, end_row=1, end_column=end_col)
        cell = ws3.cell(row=1, column=start_col, value=p_name)
        cell.alignment = align_center

        for c_offset, sub in enumerate(["No.", "vol", "IRR"]):
            ws3.cell(row=2, column=start_col + c_offset, value=sub).alignment = align_center

    ws3.row_dimensions[1].height = 24
    ws3.row_dimensions[2].height = 22

    # Style header cells
    for r in (1, 2):
        for c in range(1, 11):
            cell = ws3.cell(row=r, column=c)
            cell.fill = fill_navy if r == 1 else fill_subnavy
            cell.font = font_white_bold
            cell.border = thin_border

    cur_row = 3
    # Populating Hierarchical Data for Sheet 3
    # period_summary structure: list of region blocks:
    # { region_name: str, counts: {TD: {no, vol, irr}, MTD: ..., YTD: ...}, branches: [...] }
    for reg in period_summary.get("regions", []):
        r_name = reg["label"]
        # Region Header Row
        ws3.cell(row=cur_row, column=1, value=r_name).font = font_bold
        ws3.cell(row=cur_row, column=1).alignment = align_left
        ws3.cell(row=cur_row, column=1).fill = fill_region

        col_pos = 2
        for p_code in ("TD", "MTD", "YTD"):
            m = reg.get("periods", {}).get(p_code, {"records": 0, "amount": 0, "irr": 0})
            c_no = ws3.cell(row=cur_row, column=col_pos, value=m.get("records", 0))
            c_vol = ws3.cell(row=cur_row, column=col_pos + 1, value=float(m.get("amount", 0)) / 100000.0)
            c_irr = ws3.cell(row=cur_row, column=col_pos + 2, value=_safe_irr_val(m.get("irr")))

            c_no.font = c_vol.font = c_irr.font = font_bold
            c_no.fill = c_vol.fill = c_irr.fill = fill_region
            c_no.number_format = num_fmt_int
            c_vol.number_format = num_fmt_lakh
            c_irr.number_format = num_fmt_pct
            c_no.alignment = c_vol.alignment = c_irr.alignment = align_right
            col_pos += 3

        for c in range(1, 11):
            ws3.cell(row=cur_row, column=c).border = thin_border
        cur_row += 1

        # Branches under this region
        for br in reg.get("branches", []):
            b_name = br["label"]
            ws3.cell(row=cur_row, column=1, value=f"   {b_name}").font = font_branch
            ws3.cell(row=cur_row, column=1).alignment = align_left

            col_pos = 2
            for p_code in ("TD", "MTD", "YTD"):
                bm = br.get("periods", {}).get(p_code, {"records": 0, "amount": 0, "irr": 0})
                c_no = ws3.cell(row=cur_row, column=col_pos, value=bm.get("records", 0))
                c_vol = ws3.cell(row=cur_row, column=col_pos + 1, value=float(bm.get("amount", 0)) / 100000.0)
                c_irr = ws3.cell(row=cur_row, column=col_pos + 2, value=_safe_irr_val(bm.get("irr")))

                c_no.font = c_vol.font = c_irr.font = font_regular
                c_no.number_format = num_fmt_int
                c_vol.number_format = num_fmt_lakh
                c_irr.number_format = num_fmt_pct
                c_no.alignment = c_vol.alignment = c_irr.alignment = align_right
                col_pos += 3

            for c in range(1, 11):
                ws3.cell(row=cur_row, column=c).border = thin_border
            cur_row += 1

    # Grand Total Row for Sheet 3
    gt = period_summary.get("total", {})
    ws3.cell(row=cur_row, column=1, value="Grand Total").font = font_bold
    ws3.cell(row=cur_row, column=1).alignment = align_left
    ws3.cell(row=cur_row, column=1).fill = fill_total

    col_pos = 2
    for p_code in ("TD", "MTD", "YTD"):
        gm = gt.get("periods", {}).get(p_code, {"records": 0, "amount": 0, "irr": 0})
        c_no = ws3.cell(row=cur_row, column=col_pos, value=gm.get("records", 0))
        c_vol = ws3.cell(row=cur_row, column=col_pos + 1, value=float(gm.get("amount", 0)) / 100000.0)
        c_irr = ws3.cell(row=cur_row, column=col_pos + 2, value=_safe_irr_val(gm.get("irr")))

        c_no.font = c_vol.font = c_irr.font = font_bold
        c_no.fill = c_vol.fill = c_irr.fill = fill_total
        c_no.number_format = num_fmt_int
        c_vol.number_format = num_fmt_lakh
        c_irr.number_format = num_fmt_pct
        c_no.alignment = c_vol.alignment = c_irr.alignment = align_right
        col_pos += 3

    for c in range(1, 11):
        ws3.cell(row=cur_row, column=c).border = total_border

    ws3.column_dimensions["A"].width = 28
    for c_idx in range(2, 11):
        ws3.column_dimensions[get_column_letter(c_idx)].width = 13
    ws3.freeze_panes = "B3"

    # 4. Sheet 4: Product MTD Summary (HL MTD, NHL MTD, TOTAL MTD)
    ws4 = wb.create_sheet("Product MTD Summary")
    ws4.views.sheetView[0].showGridLines = True

    ws4.merge_cells("A1:A2")
    ws4.cell(row=1, column=1, value="REGION")
    ws4.cell(row=1, column=1).alignment = align_center

    prod_groups = [("HL MTD", 2, 4), ("NHL MTD", 5, 7), ("TOTAL MTD", 8, 10)]
    for pg_name, start_col, end_col in prod_groups:
        ws4.merge_cells(start_row=1, start_column=start_col, end_row=1, end_column=end_col)
        cell = ws4.cell(row=1, column=start_col, value=pg_name)
        cell.alignment = align_center

        for c_offset, sub in enumerate(["No.", "vol", "IRR"]):
            ws4.cell(row=2, column=start_col + c_offset, value=sub).alignment = align_center

    ws4.row_dimensions[1].height = 24
    ws4.row_dimensions[2].height = 22

    for r in (1, 2):
        for c in range(1, 11):
            cell = ws4.cell(row=r, column=c)
            cell.fill = fill_navy if r == 1 else fill_subnavy
            cell.font = font_white_bold
            cell.border = thin_border

    cur_row = 3
    # Populating Hierarchical Data for Sheet 4
    for reg in product_summary.get("regions", []):
        r_name = reg["label"]
        ws4.cell(row=cur_row, column=1, value=r_name).font = font_bold
        ws4.cell(row=cur_row, column=1).alignment = align_left
        ws4.cell(row=cur_row, column=1).fill = fill_region

        col_pos = 2
        for cls_code in ("HL", "NHL", "TOTAL"):
            m = reg.get("classes", {}).get(cls_code, {"records": 0, "amount": 0, "irr": 0})
            c_no = ws4.cell(row=cur_row, column=col_pos, value=m.get("records", 0))
            c_vol = ws4.cell(row=cur_row, column=col_pos + 1, value=float(m.get("amount", 0)) / 100000.0)
            c_irr = ws4.cell(row=cur_row, column=col_pos + 2, value=_safe_irr_val(m.get("irr")))

            c_no.font = c_vol.font = c_irr.font = font_bold
            c_no.fill = c_vol.fill = c_irr.fill = fill_region
            c_no.number_format = num_fmt_int
            c_vol.number_format = num_fmt_lakh
            c_irr.number_format = num_fmt_pct
            c_no.alignment = c_vol.alignment = c_irr.alignment = align_right
            col_pos += 3

        for c in range(1, 11):
            ws4.cell(row=cur_row, column=c).border = thin_border
        cur_row += 1

        for br in reg.get("branches", []):
            b_name = br["label"]
            ws4.cell(row=cur_row, column=1, value=f"   {b_name}").font = font_branch
            ws4.cell(row=cur_row, column=1).alignment = align_left

            col_pos = 2
            for cls_code in ("HL", "NHL", "TOTAL"):
                bm = br.get("classes", {}).get(cls_code, {"records": 0, "amount": 0, "irr": 0})
                c_no = ws4.cell(row=cur_row, column=col_pos, value=bm.get("records", 0))
                c_vol = ws4.cell(row=cur_row, column=col_pos + 1, value=float(bm.get("amount", 0)) / 100000.0)
                c_irr = ws4.cell(row=cur_row, column=col_pos + 2, value=_safe_irr_val(bm.get("irr")))

                c_no.font = c_vol.font = c_irr.font = font_regular
                c_no.number_format = num_fmt_int
                c_vol.number_format = num_fmt_lakh
                c_irr.number_format = num_fmt_pct
                c_no.alignment = c_vol.alignment = c_irr.alignment = align_right
                col_pos += 3

            for c in range(1, 11):
                ws4.cell(row=cur_row, column=c).border = thin_border
            cur_row += 1

    # Grand Total Row for Sheet 4
    gt = product_summary.get("total", {})
    ws4.cell(row=cur_row, column=1, value="Grand Total").font = font_bold
    ws4.cell(row=cur_row, column=1).alignment = align_left
    ws4.cell(row=cur_row, column=1).fill = fill_total

    col_pos = 2
    for cls_code in ("HL", "NHL", "TOTAL"):
        gm = gt.get("classes", {}).get(cls_code, {"records": 0, "amount": 0, "irr": 0})
        c_no = ws4.cell(row=cur_row, column=col_pos, value=gm.get("records", 0))
        c_vol = ws4.cell(row=cur_row, column=col_pos + 1, value=float(gm.get("amount", 0)) / 100000.0)
        c_irr = ws4.cell(row=cur_row, column=col_pos + 2, value=_safe_irr_val(gm.get("irr")))

        c_no.font = c_vol.font = c_irr.font = font_bold
        c_no.fill = c_vol.fill = c_irr.fill = fill_total
        c_no.number_format = num_fmt_int
        c_vol.number_format = num_fmt_lakh
        c_irr.number_format = num_fmt_pct
        c_no.alignment = c_vol.alignment = c_irr.alignment = align_right
        col_pos += 3

    for c in range(1, 11):
        ws4.cell(row=cur_row, column=c).border = total_border

    ws4.column_dimensions["A"].width = 28
    for c_idx in range(2, 11):
        ws4.column_dimensions[get_column_letter(c_idx)].width = 13
    ws4.freeze_panes = "B3"

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def render(fmt: str, header: Sequence[str], rows: Iterable[Sequence[Any]], sheet: str = "IRR") -> bytes:
    return to_xlsx(header, rows, sheet) if fmt == "xlsx" else to_csv(header, rows)
