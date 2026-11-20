# Loading Aham's Takeoff master (the move from Excel)

`backend/app/import_takeoff.py` loads Aham's call-centre workbook (`Takeoff_CallCentre_Master_*.xlsx`) into the app,
so the app starts from where the Excel stands. It loads the **facts** the workbook holds and lets the app work out
every status, RAG, action and flag with its own rules, as of the workbook's run date (Control sheet), then compares
the result with the workbook's own **Monitor export**, entry by entry.

## What is loaded

| Sheet | Loaded as |
|---|---|
| Raw Data | One entry per row with an Entry ID: SO, branch, spoke, category, CP sub-type, person met, number, description. The Entry ID is kept as it is. |
| Monitor export | The Excel's decision for entries it did not call ("Not called – …"), so the app does not decide them again. Entries the Excel had not decided yet wait for the app's next daily run. |
| History | Every recorded try: caller, call date, slot, outcome, and the answers on the connected call; the lead card and lead ID. |
| Earlier entries | Entries of 22 Sep – 6 Oct called in the September file, whose tries are not in this workbook: one try is carried over with the final status that file gave it (caller "September Takeoff file"). |
| SO corrections | The corrected SO (and branch). |
| Follow-up tracker | The rows keyed by an Entry ID. |
| Logins | The MIS login register, through the app's own register import (matching, Sankalp success). |

Not loaded, and why:

- **Raw Data rows without an Entry ID** (1,942 in the October workbook): entries from before Takeoff start, handled by
  the old process ([Legacy]). Tracker rows keyed "date|number" point at these rows and are not loaded either.
- **"Discarded – old process"** (96): the old process is not built.
- A row with no category, a call row with no date, and an answer that is not one of the app's choices (for example a
  sentence typed in "Loan need") are left out and counted.

SOs, callers and CP sub-types the app does not have are added. The people get **no password they can use**: HR
gives one with a temporary password (Users & roles). Entries whose Emp ID could not be read belong to the SO
**UNRES** ("Unresolved SO"), for the monitor to correct (wrong SO, 13.1). An entry's page says "loaded from the
Takeoff master (Excel)".

A number that is not a valid mobile number is kept as it was typed (digits only), and the entry stays "Not called –
no valid number", as in the Excel.

## Running it

From `backend/`, with the Docker database running. It uses `DATABASE_URL` like the backend; without it, the
database on `localhost:5433` called `fieldsync` (the one the lessons use).

```bash
.venv/Scripts/python.exe -m app.import_takeoff "C:\path\Takeoff_CallCentre_Master_Oct2026.xlsx" --dry-run --report report.csv
```
`--dry-run` loads, works everything out, compares and writes the report, then undoes it all. Without `--dry-run` it
saves. `--as-of YYYY-MM-DD` works statuses out as of another day than the workbook's run date. A second load into
the same database is refused; take the first one out with:

```bash
.venv/Scripts/python.exe -m app.import_takeoff --remove
```
`--remove` deletes every loaded entry with its calls, lead cards, tracker rows, events and logins, the people and
CP sub-types the load added (anyone the app has used since stays, made inactive), and puts the app's own entries'
logins right again. Customer names and numbers are never printed; the report has Entry IDs and the two values.

## How close the app comes to the Excel (October workbook, as of 5 Nov 2026)

8,729 entries, 10,320 tries (1,443 carried over from the September file), 52 tracker rows, 338 login rows (245
entries matched).

| Field | Agree | The differences |
|---|---|---|
| Status | 96.7% | 258 entries were put on call sheets (26 Oct – 3 Nov) but no try was ever recorded: the Excel calls them "In retry", the app "Waiting for the first call". 12 carry an old "Not called – branch follow-up (mail sent)". About 15 depend on September tries the workbook does not have. |
| RAG | 88.1% | Follows from the line above (Green in the Excel, Pending in the app), and two conventions: an Existing Customer / Applicant is **NA** in the app (never called) and Pending in the Excel (505); an entry not called yet is **Pending** in the app and NA in the Excel (248). |
| SO action | 99.9% | Compared with the action whether or not its window has passed (the Monitor export's column ignores the window; in the app it becomes the expired action). |
| CC action | 100% | 2 callbacks. |
| TCS ID | 98.7% | The app shows a login's TCS ID on **every** entry with that number; the Excel only on lead-type entries (112, mostly Existing Customers / Applicants). |
| Lead outcome | 99.8% | 7 logins the Excel dates from the September login file, which this workbook does not hold. |
| Sankalp success | 100% | 4 entries. |

To decide with Aham: whether an Existing Customer's RAG and a not-yet-called entry's RAG should follow the Excel,
and whether a TCS ID belongs on entries that are not leads.
