# Weighted average IRR (HL and NHL / LAP)

From the client's BRD "Automation of Weighted Average IRR Calculation – HL & NHL (LAP)". MIS uploads the
**Disbursement Register**; the app reports the weighted average IRR of Home Loans (HL) and Non-Home Loans (NHL = LAP)
for **the day (TD; Aham's note also says FTD)**, **Month to date (MTD)** and **Year to date (YTD)**, by branch, region and for the company.

## The formula (Aham's process note, confirmed 12 Nov 2026)
For every eligible disbursement row:

- **Transaction IRR** = disbursed amount × **that row's own** tenure (months) × ROI (%)

For a group (a branch, a region or the company, over TD, MTD or YTD):

- average tenure = Σ tenure ÷ number of rows (the **plain** average of the tenure column, not weighted by amount)
- weighted average IRR = Σ Transaction IRR ÷ (Σ disbursed amount × average tenure)
- **No.** = the number of disbursement rows: a loan paid out in two tranches counts twice

**HL and NHL (LAP) are always worked out separately**: every report, the loan-level detail and the reconciliation are
for one product class at a time, and nothing adds the two together.

MTD and YTD are always worked out from all the rows of the period (their amounts, tenures and Transaction IRRs added
up), never from daily, branch or region percentages; every total is worked out from the rows themselves. The four sums
(rows, amount, tenure, Transaction IRR) add up across days, months, branches and regions; the denominator does not,
because it multiplies the whole group's amount by the whole group's average tenure. Everything is calculated with
`Decimal`; rounding (half up) happens only for display. A group with no rows has no IRR: the screen shows "–", never 0%.

Worked example (also a test): Loan A ₹30,00,000, 240 months, 9% and Loan B ₹5,00,000, 60 months, 12%:

- Transaction IRR: 30 lakh × 240 × 9 = 64,800 and 5 lakh × 60 × 12 = 3,600 (in lakh-months); Σ = 68,400
- average tenure = (240 + 60) ÷ 2 = 150 months; denominator = 35 lakh × 150 = 5,250
- IRR = 68,400 ÷ 5,250 = **13.03%**

Because the average tenure is not weighted by amount, a group's IRR can be **above or below every loan's own rate**
(13.03% here, against 9% and 12%). The expected-range warning (IRR settings) is the place to catch a figure that
looks wrong.

## Aham's process note (12 Nov 2026)
Aham sent "Process Note – HL & NHL IRR Calculation". It confirms: the daily Disbursement Register as the source; HL
and LAP (= NHL) by branch and region; FTD/TD, MTD and YTD on a financial-year basis; the two report layouts (HL & LAP
MTD: region × HL No./IRR × NHL No./IRR; and TD / MTD / YTD: region × No./IRR per period); per loan, **Transaction IRR =
disbursed amount × loan tenure × interest rate** (our "product"); and a review of accounts, tenure, rate, IRR and
regional totals before the report is shared (our Reconciliation and Exceptions pages).

The note wrote `Σ Transaction IRR ÷ (Σ disbursed amount × average tenure)` without saying which average, and its
last page used the average tenure inside each loan's figure too. With the worked example the readings give 9.12%
(average weighted by amount, the app's earlier formula), 13.03% (plain average) or 9.43% (average tenure in each loan's
figure as well). **Decided on 12 Nov 2026:**

| Question | Answer |
|---|---|
| Which average tenure? | The plain average of the tenure column (Σ tenure ÷ rows) |
| Each loan's own tenure in its Transaction IRR, or the average? | The loan's own tenure |
| TD / MTD / YTD: one table per product, or HL and LAP together? | Separate, everywhere |
| "No.": loan accounts or disbursement rows? | Rows (a loan in two tranches counts twice) |

Still open: one month of Aham's own Excel to match to two decimals, the financial-year start, and whether a finalised
report must be locked.

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
| ROI % | column yes, value may be empty | ROI, Rate of interest, Interest rate, Rate. **Not** "Transaction IRR" or "IRR": in Aham's process note that is amount × tenure × rate; a file with only that column is refused and told why |
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
| `GET /report` | TD / MTD / YTD (for the day, month to date, year to date): `as_of` (default: latest disbursement the user can see, else today), `product` HL\|NHL, `level` branch\|region\|company, `region_id`, `branch_id`. Rows with No. (disbursements) and IRR per period, the total, warnings, open exceptions per period |
| `GET /report/month-by-product` | HL & NHL month to date: HL No., HL IRR, NHL No., NHL IRR per row and in total (each class worked out on its own) |
| `GET /detail` | The disbursements behind a figure (paged), for one `product` (default HL): account, date, branch, region, product, class, amount, tenure, ROI, Transaction IRR, with the sums that give the IRR (rows, amount, Σ tenure, average tenure, denominator, Σ Transaction IRR) |
| `GET /reconciliation` | For a period and one `product` (default HL): rows uploaded, included, excluded, exceptions, amount and average tenure by branch, by region and for the company, each worked out separately, with checks that they agree; and the **year to date month by month** (rows, amount, average tenure, denominator Σ amount × average tenure and numerator Σ Transaction IRR per month) with the BRD's YTD check: the year's rows, amounts, tenures and Transaction IRR equal the sum of its months, for the financial year of the period's end, in the same scope and product |
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

1. **Rate** = the ROI (rate of interest) column of the register, as uploaded. Aham's process note (12 Nov) calls
   amount × tenure × rate the "Transaction IRR", so a column with that name is never read as the rate.
2. **Tranches**: each disbursement row is its own record, with its own amount and the tenure on the row, and counts
   in "No." and in the average tenure once per row (Aham, 12 Nov 2026): a loan paid in two tranches counts twice.
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
21. In reconciliation, rows, amounts, tenures and Transaction IRR always add up from branches to regions to the
    company and from months to the year; the denominator and the IRR are worked out for each group and never added.

## Upload size
A register file can be up to 10 MB (CSV or Excel); `limit_body_size` in `backend/app/main.py` allows it for
`/api/v1/irr/disbursements`.
