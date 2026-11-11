# Weighted average IRR (HL and NHL / LAP)

From the client's BRD "Automation of Weighted Average IRR Calculation – HL & NHL (LAP)". MIS uploads the
**Disbursement Register**; the app reports the weighted average IRR of Home Loans (HL) and Non-Home Loans (NHL = LAP)
for **Today (TD)**, **Month to date (MTD)** and **Year to date (YTD)**, by branch, region and for the company.

## The formula (BRD section 6)
For every eligible disbursement record:

- weight = disbursed amount × loan tenure (months)
- product = weight × ROI (%)
- weighted average IRR of a group = Σ product ÷ Σ weight

MTD and YTD are always the sums over the records of the period (cumulative numerator ÷ cumulative denominator), never
an average of daily, branch or region percentages; every total is worked out from the loan-level records. Each loan's
own tenure is used (the BRD's sentence about "total amount × average tenure" is a known error and is not implemented).
Everything is calculated with `Decimal`; rounding (half up) happens only for display. A group with no records has no
IRR: the screen shows "–", never 0%.

Worked example (also a test): Loan A ₹30,00,000, 240 months, 9% and Loan B ₹5,00,000, 60 months, 12% →
(7,200 × 9 + 300 × 12) ÷ (7,200 + 300) lakh-months = 68,400 ÷ 7,500 = **9.12%**. Weighting by amount only would give
9.43%, which is wrong.

## Where it lives
| Part | File |
|---|---|
| Formula, periods, bands (pure, no database) | `backend/app/services/irr/calc.py` |
| Register reader and row errors (pure) | `backend/app/services/irr/register.py` |
| Settings model, CSV / Excel export | `backend/app/services/irr/settings.py`, `export.py` |
| Tables `irr_disbursements`, `irr_settings` | `backend/app/models/irr.py`, migration `c3d5f8a1e6b2` |
| API (`/api/v1/irr/...`) | `backend/app/api/v1/irr.py` |
| Web pages | `admin-web/src/features/irr/` |
| Tests | `backend/tests/test_irr_calc.py`, `test_irr_api.py`, `admin-web/tests/irr.test.tsx` |

## Disbursement Register upload
CSV or Excel (first sheet), with a template (CSV or Excel) and **Check first** (a dry run that saves nothing). Each
upload is kept in the upload history (`ImportBatch`, kind `disbursement`) and in the audit log.

| Column | Required | Also accepted as (case and punctuation do not matter) |
|---|---|---|
| Loan account number | yes | LAN, Loan account, Loan no, Account number, … |
| Disbursement reference | no | Tranche number, Tranche no, Disbursement no, Disb ref, … |
| Disbursement date | yes | Disbursal date, Date of disbursement, Disb date, Date |
| Product | yes | Product name, Product type, Loan product, Scheme |
| Branch (code or name) | yes | Branch name, Branch code |
| Disbursed amount (₹, > 0) | yes | Disbursement amount, Amount disbursed, Disbursed amount (Rs), Amount |
| Tenure in months | column yes, value may be empty | Tenure, Loan tenure, Tenor |
| ROI % | column yes, value may be empty | ROI, Rate of interest, Interest rate, Transaction IRR, IRR |
| Status | no | Disbursement status, Loan status |
| Customer name | no | Customer, Borrower name, Applicant name |

- **Same row again**: the key is loan account + disbursement reference, or loan account + date + amount when there is
  no reference. A row already uploaded is replaced (latest upload wins), so a file uploaded twice is never counted twice.
- **Summary**: rows, new, replaced, excluded, exceptions, errors (rows not saved).
- **Row errors** are exact: `{"row": 7, "column": "Disbursement date", "value": "31/02/2026", "message": "Not a real
  date. Use DD-MM-YYYY, for example 05-11-2026"}` (the column as written in the file). A row with any error is not
  saved; all its problems are listed at once. The web shows them as a table with **Download errors**.
- **File problems** (not CSV / Excel, empty, missing columns, no data rows) are a 422 that names the missing columns
  and lists the columns found.

## Reports and API (prefix `/api/v1/irr`)
Every table endpoint takes `format=csv` or `format=xlsx` to download.

| Endpoint | What |
|---|---|
| `GET /report` | Today / Month / Year to date: `as_of` (default: latest disbursement the user can see, else today), `product` HL\|NHL, `level` branch\|region\|company, `region_id`, `branch_id`. Rows with accounts and IRR per period, the total, warnings, open exceptions per period |
| `GET /report/month-by-product` | HL & NHL month to date: HL accounts, HL IRR, NHL accounts, NHL IRR per row and in total |
| `GET /detail` | The loans behind a figure (paged): account, date, branch, region, product, class, amount, tenure, ROI, weight, weight × ROI, with the sums that give the IRR |
| `GET /reconciliation` | For a period: rows uploaded, included, excluded, exceptions, amount and accounts by branch, by region and for the company, each summed separately, with checks that they agree; and the **year to date month by month** (numerator Σ amount × tenure × ROI and denominator Σ amount × tenure per month) with the BRD's YTD check: the year's figures equal the sum of its months, for the financial year of the period's end, in the same scope and product |
| `GET /exceptions`, `PATCH /exceptions/{id}` | Disbursements left out for missing / zero / negative tenure or ROI; correcting them (audited) brings them in |
| `GET /settings`, `PUT /settings` | Product mapping, expected ranges, financial-year start month, decimals |
| `POST /disbursements`, `GET /disbursements/template`, `GET /uploads` | Upload (with `dry_run`), template, history |

Web: HR & Admin portal, menu group **IRR** (IRR report, Disbursement register with reconciliation, IRR exceptions,
IRR settings); Management portal, **IRR report** (read-only, scoped).

## Access
| Permission | Roles |
|---|---|
| `irr.view` (reports, detail, reconciliation, exception list, settings read) | Branch Manager, Cluster Manager, Region Manager, Product Manager, Business Manager, MIS, System admin |
| `irr.manage` (upload, correct exceptions, change settings) | MIS, System admin |

Data scope as everywhere else (`visible_branch_ids`): a BM sees their branch, an RTM their cluster, an RBH their
region, everyone else the company. Callers, Sales Officers, the Master owner and the Sankalp monitor get nothing.

## Assumptions to confirm with Aham
The client has not answered these yet; the app does the following. Items marked **(setting)** can be changed under
IRR settings without a code change.

1. **Rate** = the ROI column of the register (the BRD's "transaction IRR"), as uploaded.
2. **Tranches**: each disbursement row is its own record, weighted by its own amount and the tenure on the row.
   Number of accounts = distinct loan account numbers in the group and period (an account with tranches in two months
   counts once in YTD and once in each MTD).
3. **Product → HL / NHL** through the product mapping **(setting)**. Seeded: Home Loan → HL; LAP and Loan Against
   Property → NHL. A row with a product that is not mapped is a row error that says to add it in IRR settings.
4. **Tenure** is in months, as in the register.
5. **Branch and region** are the ones at disbursement: the branch on the row, and its region from our branch master
   at upload time, stored on the record (moving a branch later does not move old disbursements between regions).
6. **Status** Cancelled / Reversed (any case; anything starting with "cancel" or "revers") → stored but excluded and
   counted as "excluded". Re-uploading a row replaces the earlier copy.
7. **Missing, zero or negative tenure or ROI** → stored as an exception, left out, listed under IRR exceptions, where
   MIS / admin can correct tenure and ROI (audited); it is then included. The report shows how many are open.
8. **Financial year** starts on 1 April **(setting: start month)**. **Decimals shown**: 2 **(setting)**.
9. **Reasonableness**: an optional expected range (lowest %, highest %) per product class **(setting)**. A group
   whose IRR, as shown, is outside it gets a warning on the report; it never blocks.
10. **Export**: CSV and Excel for every report table, reconciliation, exceptions and the loan-level detail.
11. **Access** as in the table above.
12. **On demand**: reports are worked out when opened; nothing is scheduled.

Further choices made while building (also to confirm):

13. The Tenure and ROI **columns** must be in the file (a file without them is refused); an empty cell in them makes
    that row an exception.
14. A tenure or ROI that is not a number (for example "20 years"), an ROI between 0 and 1 (a percentage-formatted
    Excel cell such as 0.095 for 9.5%), an ROI of 100 or more, a disbursement date after today, and the same row twice
    in one file are **row errors** (the row is not saved), not exceptions.
15. Re-uploading a row also replaces a **manual correction** made to it on the Exceptions page (latest upload wins);
    the correction remains in the audit log.
16. Changing a product's class in the mapping also moves the disbursements **already uploaded** under that product
    name. Removing a product from the mapping leaves earlier rows in the class they had.
17. Settings apply to every report at once, past days included (they are not dated like the Sankalp settings).
18. The reports list every active branch (or region) in the user's scope, with "–" where there are no disbursements.
19. A user's scope follows the branch on the record; the region rows and the region filter use the region stored on
    the record.
20. The duplicate key depends on whether a reference is given: if a register first uploaded **without** the reference
    column is later uploaded **with** it, the same disbursements get new keys and would be counted twice. Keep the
    same columns across uploads.
21. In reconciliation, branch account counts can add up to more than the company count only if one loan account has
    disbursements in two branches; amounts, record counts and the IRR sums always agree.

## Upload size
A register file can be up to 10 MB (CSV or Excel); `limit_body_size` in `backend/app/main.py` allows it for
`/api/v1/irr/disbursements`.
