# Sankalp: learn it by doing it

Two parts:
1. **The logic on one page.** What happens to an entry, stage by stage, in plain words.
2. **Do the whole process yourself** on an empty system: 13 steps, about 90 minutes. No demo data is loaded; you
   create everything, and each step says what you should see and why.

The rules come from Aham's *Sankalp app: business logic* (v1); the section numbers below point into it.

---

## Part 1: the logic on one page

### The chain
```
SO meets a person ──► Entry ──► Daily selection ──► Caller's list ──► Call ──► One current status + RAG
                                 (who is called)    (which caller)            │
                                                                              ▼
            Sankalp success ◄── Login register ◄── Branch answer ◄── Next action (SO / branch or call centre)
```
Corrections (wrong number, wrong SO, wrong category) can happen on the side at any time.

### 1. The entry (section 4)
- A Sales Officer (SO) records **one entry per person met**: category, name, **mobile number**, description,
  optional photos and Keka photo time. On the phone; or, for meetings not entered on the phone, by HR or the admin
  in a **bulk upload**.
- **Entry ID** = `EmpID-YYYYMMDD-HHMMSS` of the moment Submit was pressed (or the date and time met, for a bulk
  upload). It never changes. An entry made offline keeps its own time when it reaches the server.
- The mobile number is cleaned (`+91`, spaces, a leading 0 removed) and must be 10 digits starting 6–9.
- **A customer who is already a lead is refused**: if any earlier entry for the same mobile number has a TCS lead
  ID or a login, the phone shows who entered the customer and when, and the server refuses the entry.
- **Counts on:** the entry date; a Sunday or holiday counts on the next working day.
- **Daily compliance:** each present SO should make **10 entries a day, 5 of them Lead/Prospect**. Absent = "AB".

### 2. Daily selection: who gets called (section 5)
Once a day the Master owner runs the selection for the entries of earlier days (same-day calling is off unless
switched on in Settings).
- **Call group:** Lead and Prospect → *Lead group*. DSA/Connector and Contact Point → *DSA/CP group*. Existing
  Customer / Applicant → *never called*.
- Each new entry gets one decision, checked in this order; the first that fits wins:

| # | Check | Result |
|---|---|---|
| 1 | No valid mobile number | Not called – no valid number |
| 2 | Lead group, same SO, same number, an earlier entry within 30 days | Not called – repeat entry by same SO |
| 3 | Same number already in today's new entries with an earlier time | Not called – duplicate entry |
| 4 | The number is being called on another entry | Not called – number already being called |
| 5 | Lead group, the number was spoken to (connected) in the last 30 days | Not called – spoken within 30 days |
| 6 | DSA/CP group, the number was ever spoken to | Not called – known contact |
| 7 | Otherwise | **Allocate** (it will be called) |

"Not called" is final for that entry.

### 3. Allocation: which caller (section 6)
- **New entries** go to the caller the Master owner set for that branch today ("caller of the day").
- **Retries** go back to the caller who **first** handled the entry.
- **PRIORITY** entries come first and go on the list **at once**: a branch says the customer is not answering them
  (code 3), or the Master owner reopens the entry for calling.
- Work not recorded by the next run is offered again.

### 4. The call (section 7)
- **Lead group:** 2 tries a day are planned (morning and afternoon); up to 3 can be recorded; after **9**
  unanswered tries the entry is "Discarded – 9 unanswered".
- **DSA/CP group:** called on one day only (plus a callback date it asks for).
- **Outcomes:** Connected · Rang, no answer · Busy · Switched off · Not reachable · Invalid number · Wrong person ·
  Callback requested · Refused to talk. *Unanswered* = Rang, no answer · Busy · Switched off · Not reachable.
- **Only a call that gives a status changes the status** (as the Takeoff master): connected, invalid number, wrong
  person, refused to talk, or a DSA/CP closed. An unanswered try or a callback request leaves it as it was, so a
  validated lead stays validated when a later follow-up call is not answered. A DSA/CP's callback request closes it.
- **Connected, Lead group:** Timeline, Income, Documents, Next step and Purpose are asked only when the loan need is a
  loan (not LAP, BT + LAP or "Not looking for a loan"); Own contribution only for a purchase or construction.
- **Connected, Lead group:** the caller asks the Lead questions (name check, did the SO meet you, does the customer
  know the SO, loan need, documents, timeline, income, next step and date).
- **Lead card:** once the loan need is a loan type, the caller fills the lead card; the **TCS lead ID** goes here.
  The lead ID never closes a lead; only the login register does.

### 5. One current status (sections 8, 11)
Every entry shows **one** status, the latest truth; the earlier ones stay in its History:

| Stage | What the current status can be |
|---|---|
| Before selection | Waiting for the daily selection · Not called – existing customer / applicant |
| After selection | Not called – (reason) · Waiting for the first call |
| While calling | In retry – 2 unanswered · In retry – call back on (date) · In retry – PRIORITY (reopened) |
| After a connected call (Lead) | Validated · Validated – different person · Validated – visit not confirmed · Validated – converted from DSA/CP · Already in process · Not counted – LAP · Amber – answers missing · Amber – knows SO · Red |
| Not connected, final | Discarded – 9 unanswered · Discarded – invalid number · Amber – wrong person · Closed – no answer · Rejected – refused to talk |
| DSA/CP | DSA/CP – Green / NA / Amber / Red / no RAG |
| After the login register | Logged in · Rejected · Login on/before entry date (not counted) |

The lead logic (8.1), in order: no loan need answered → Amber – answers missing; "Not looking for a loan" → Red;
LAP → Not counted – LAP; file already with Aham → Already in process; knows the same SO → Amber – knows SO;
different person → Validated – different person; SO did not visit → Validated – visit not confirmed; else
**Validated**.

### 6. RAG (section 9)
| RAG | Means |
|---|---|
| Green | Validated, or a DSA/CP rated Green, and an action is open |
| Amber | Needs fixing: wrong person, answers missing, knows the SO, invalid number |
| Red | Not interested |
| No answer | Being called and not answering, or discarded after the tries |
| Not called yet | Selected, waiting for the first call |
| Not applicable | Closed: logged in, rejected, not called, or nothing left to do |

### 7. Next actions (section 12)
| Situation | Action | Who | Open for |
|---|---|---|---|
| Validated, next step "SO / branch visit" | Visit customer (on the next date) | SO / branch | until login or rejection |
| Validated, documents Partly / No | Collect documents | SO / branch | until login or rejection |
| Validated otherwise | Follow up lead | SO / branch | until login or rejection |
| Next step "Call centre to continue" | Take case forward | Call centre | until done |
| Wrong person / invalid number | Correct customer number | BM / RTM | 15 days from the entry |
| DSA/CP Green | DSA/CP follow-up | SO | 14 days |
| In retry with a callback date | Callback | Call centre | on that date, then 14 days |
| Follow-up tracker, Owner = Branch | the tracker's action type (e.g. Confirmation of login required) | SO / branch | until the tracker changes |
| Green-channel reject sent back | Log in under green channel | SO / branch | until login or rejection |

**Branch answer (12.4):** the BM answers each validated lead with **one code and one date**. A date more than 14 days
away sends the lead to the call centre's **Follow-up** on that date; once the call centre has called, the lead is
the branch's again. Code 3 = customer not answering the branch → PRIORITY call at once. R1–R6 = rejected; but for a
**green-channel** loan (self-construction or improvement up to ₹8 lakh, purchase up to ₹15 lakh) an R2 (income) or R3
(credit score) waits for the Master owner's check. A branch without a BM is answered by the RBH.

### 8. Login and success (sections 10, 11)
- MIS uploads the **login register** (TCS ID, mobile numbers, login date, product). Every number in a cell is matched
  to the entries with that number.
- **Logged in** when the login is after the entry date (or the Master owner typed the TCS ID by hand).
- **Sankalp success:** logged in, entry on or after Takeoff start, and the **earliest** entry for that TCS ID.
  One success per loan.
- **Customer validated** (for the incentive): a Validated status, or the entry that is the Sankalp success for its
  TCS ID (logged in, not LAP); never for a repeat entry by the same SO. **First validation** goes to the earliest validated entry for that number: a customer is paid once.

### 9. Corrections (section 13)
- **Wrong number:** the BM (or RTM) types the right number within 15 days; the entry is called again with a fresh 9
  tries. Same Entry ID.
- **Wrong SO:** the RTM or the monitor picks the right SO; the credit moves; same Entry ID.
- **Category wrong:** the branch answers code 2; the monitor fixes the category.
- **Follow-up tracker:** the Master owner can reopen, reject, enter a TCS ID by hand or override the RAG.

---

## Part 2: do the whole process yourself

### Step 0: an empty system (5 min)
In `C:\Staunch\AHAM\AHAM`, run these one by one (the database is emptied):
```bash
docker compose down -v
```
```bash
docker compose up -d --build
```
```bash
docker compose exec backend python -m app.seed
```
Do **not** run `app.demo_data`. You now have the company, its regions and branches, the settings, and one account per
role. Every account's password is the value of `SEED_PASSWORD` in `.env`. Start the web app (`cd admin-web`, then
`npm run dev`) and open http://localhost:5173.

| Account | Who | Portal |
|---|---|---|
| AHFL90001 | Ravi Kumar, Sales Officer, Vijayawada (the phone) | phone app |
| AHFL90002 | Lakshmi Devi, Sales Officer, Guntur | phone app |
| AHFL90011 | Suresh Reddy, Branch Manager, Vijayawada | Management |
| AHFL90021 | Anil Varma, RTM | Management |
| AHFL90031 | Prakash Rao, RBH (answers Guntur and Nellore: no BM there) | Management |
| AHFL90061 / AHFL90062 | Divya S / Farhan Ali, callers | Call centre |
| AHFL90071 | Geetha M, Master owner | Call centre |
| AHFL90081 | Hari Prasad, Sankalp monitor (HR) | HR & Admin |
| AHFL90091 | Indira N, MIS | HR & Admin |
| AHFL90099 | System admin | HR & Admin |

Tip: each portal keeps its own sign-in, so one browser window can hold three portals; use a private window for a
second person in the same portal (for example a caller beside the Master owner).

The sample files are in `docs/demo-files/learn/`. They use **Saturday 7 Nov 2026** as the day of the meetings, so
they work on any later day.

### Step 1: the roster (HR & Admin, Hari Prasad)
**Data → Uploads → Employee roster.** Choose `1-roster.csv` → **Check first**: *created 3, errors 0* (Srinivas
Naidu and Padma Priya in Vijayawada, Kiran Kumar in Guntur). Press **Upload**.
- Now choose `docs/demo-files/roster-with-mistakes.csv` → **Check first**: a table shows each problem with its row,
  column, the value found and how to fix it (a branch put in the wrong region, an unknown designation, an empty Emp
  ID).
  Do not upload it.
- **Why:** the roster is the only source of who an SO is and which branch an entry belongs to.

### Step 2: attendance (Hari Prasad)
**Daily attendance** → `2-attendance.csv` → Check first → Upload. Kiran is **AB** (absent) on 7 Nov.
**Why:** compliance counts only SOs who were present; an absent SO shows "AB" instead of a shortfall.

### Step 3: entries in bulk (Hari Prasad)
**Bulk entries** → `3-entries.csv` → **Check first**: *rows 13, new entries 11, errors 2* (row 13: category
"Builder" does not exist; row 14: Emp ID AHFL99999 is not on the roster). Press **Upload**.
Open **Entries**: 11 entries of 7 Nov, each **"Waiting for the daily selection"**, made by bulk upload. Upload the
same file again: *new entries 0, already uploaded 11*. Nothing is added twice.

The rows are chosen to show the selection rules in step 6:

| Customer | Entered by | Shows |
|---|---|---|
| Nagarjuna Rao | Srinivas 10:40 and Ravi 16:20 | duplicate entry: the earlier one wins |
| Revathi Kumari | Padma 11:00 (Prospect) and 15:00 (Lead) | repeat entry by the same SO |
| Mohan Das | Srinivas (Existing Customer) | never called |
| Balaji Constructions | Srinivas (DSA/Connector) | DSA/CP calling |
| Sri Sai Hardware | Lakshmi (Contact Point) | DSA/CP calling, one day only |
| Venkata Rao, Gopi Krishna | Lakshmi, Kiran (Guntur) | Guntur's caller; the RBH answers for Guntur |
| Prasad Varma, Lakshmi Prasanna | Ravi, Padma | used for a wrong number and the green channel |

### Step 4: one entry on the phone (Ravi Kumar, AHFL90001)
Install `mobile/dist/aham-sankalp-1.3.0.apk` (it replaces the old app; clear its storage after Step 0) and set
the PC's address on the sign-in screen ("Server" → Change; see `docs/client-demo.md` "Phone and network"). Then: **New entry** → Lead, any
name, a new mobile number → Submit. The Entry ID appears at once (`AHFL90001-<today>-<time>`). In the web
**Entries** it shows the GPS place and "Waiting for the daily selection".
- **Why it is not called today:** entries are called from the next day (5.2). To try calling it today, the admin can
  switch on **Settings → Allow same-day calling**; switch it off again afterwards.

### Step 5: daily compliance (Hari Prasad)
**Daily compliance** → day **07-11-2026**. Each SO's entries against 10 and Lead/Prospect against 5; Kiran shows
**AB**. Export it with **Export: Excel**.

### Step 6: the daily run (Call centre, Geetha M)
**Daily run & allocation** → set the **caller of the day**: Vijayawada → Divya S, Guntur → Farhan Ali → Save →
**Run for today**. Expected:
- **Selected for calling: 8**; not called: **Nagarjuna Rao (Ravi's)** – duplicate entry; **Revathi Kumari
  (15:00)** – repeat entry by same SO. Mohan Das was never in the run (Existing Customer).
- **Divya's list:** Nagarjuna Rao, Revathi Kumari, Balaji Constructions, Prasad Varma, Lakshmi Prasanna (all
  Vijayawada). **Farhan's list:** Venkata Rao, Sri Sai Hardware, Gopi Krishna (Guntur).
- Open **Entries**: the two not-called entries show their reason as their current status.

### Step 7: the calls (Divya S in a private window; then Farhan Ali)
Open **My calls**, click a name to open the call screen, pick the time slot and outcome, **Save try**.

| Customer | Record | Current status after it | Next action |
|---|---|---|---|
| Nagarjuna Rao | Connected: Same person · Yes · No · Home purchase · Documents **Partly** · 1–3 months · Salaried · **SO / branch visit** + a working-day date. Then the lead card: TCS lead ID **TCS-L-100001**, loan requirement **25,00,000** | Validated, Green | Visit customer (branch) |
| Revathi Kumari | Rang, no answer (10-11), then Busy (03-04) | In retry – 2 unanswered | she leaves the list and appears under **Called today, still not answered**: a third try may be recorded today |
| Prasad Varma | Wrong person | Amber – wrong person | Correct customer number (BM) |
| Balaji Constructions | Connected: RAG given by caller **Green**, needs a home loan himself **No** | DSA/CP – Green | DSA/CP follow-up |
| Lakshmi Prasanna | Connected: … · **Self-construction** · … · SO / branch visit + date; lead card loan requirement **6,00,000** | Validated | Visit customer |

As **Farhan Ali**: Venkata Rao → Connected, loan need **LAP** (for a LAP the screen asks no timeline, documents or
next step) → *Not counted – LAP*, action *Follow up lead*; Gopi Krishna
→ Connected, Home purchase, next step **Call centre to continue** → *Validated*, action *Take case forward* (call
centre); Sri Sai Hardware → Not reachable → *Closed – no answer* (DSA/CP: one day only).

### Step 8: the branch answers (Suresh Reddy, then Prakash Rao)
**Suresh Reddy → Leads to answer** (Vijayawada): Nagarjuna Rao and Lakshmi Prasanna.
- **Nagarjuna Rao → A2** (documents pending: income proof) with a login date next week. The lead stays with the
  branch; its action date becomes that date. A date in the past is refused.
- **Lakshmi Prasanna → R2** (rejected: income). Her loan is self-construction ₹6 lakh, within the ₹8 lakh green
  channel, so the row says **green-channel check pending**. Geetha → **Green channel** → **Back to branch**: the
  reject is not accepted and the lead's action becomes **Log in under green channel**.

**Prakash Rao (RBH) → Leads to answer:** Guntur has no BM, so he answers **Venkata Rao → E2** (out of station) with a
date **three weeks** away. The lead moves to the call centre: Geetha → **Call-centre actions** shows a Follow-up on
that date. Gopi Krishna is there too (Take case forward).

Optional: answer a validated lead with **code 3** (customer not answering the branch): it appears **at once** on its
caller's list under PRIORITY.

### Step 9: correct a number (Suresh Reddy)
**Open actions → Correct number → Prasad Varma** → open the entry → **Correct number** → `90001 00077` → save. His
status is *In retry – not called yet on this number*; History shows the old and the new number. He is back on
**Divya's** list at once (she handled him first) with a fresh 9 tries; no new run is needed.

### Step 10: the login register (Indira N, MIS)
**Uploads → Login register** → `4-login-register.csv` → **Check first**: 6 rows, 1 problem (row 7: "not
available" is no mobile number; the row is kept for matching by hand). Upload. Then in **Entries**:

| Customer | Current status | Sankalp success | Why |
|---|---|---|---|
| Nagarjuna Rao (Ravi's, 16:20) | Logged in | **Yes** | both entries are dated 7 Nov: a tie on the same date goes to the lower Entry ID (11.3), and AHFL90001… is lower than AHFL90003…, even though Ravi's entry was never called |
| Nagarjuna Rao (Srinivas's, 10:40) | Logged in | No | the same loan (TCS ID 4851001): one success per loan |
| Revathi Kumari (11:00) | Logged in | **Yes** | matched on the **second** number in the cell; customer validated through the login |
| Revathi Kumari (15:00) | Logged in | No | a repeat by the same SO is never validated or paid |
| Venkata Rao | Logged in | **Yes** | LAP: a Sankalp success, but *not* "customer validated" |
| Lakshmi Prasanna | Login on/before entry date (not counted) | No | the login (6 Nov) is before the entry (7 Nov) |

TCS ID 4851005 matches no entry: a branch walk-in, not a Sankalp customer.

Note on Nagarjuna Rao: the app follows section 11.3 as written (same date → lower Entry ID). Whether the earlier
time, or the entry the call centre actually called, should win instead is a rule to confirm with Aham.

### Step 11: a converted lead is not entered again (Ravi on the phone)
**New entry** → mobile **9000100001** (Nagarjuna Rao). Under the number the phone says the customer is already a lead
(TCS lead ID TCS-L-100001) from Srinivas Naidu's entry of 07 Nov 2026, and Submit is blocked. If the phone is offline,
the entry is saved, then refused by the server when it syncs, with the same reason.

### Step 12: the incentive file and exports (Hari Prasad)
**Takeoff export** → 01-11-2026 to today → Download: one row per entry with the four flags (customer validated,
first validation, validated on, Sankalp success). Every table in the app has **Export: CSV · Excel**; a paged list
(Entries, Open actions, Audit log) exports **all** its rows, not only the page on screen.

### Step 13: the IRR report (Indira N or the admin)
**IRR → Disbursement register** → `5-disbursement-register.csv` → **Check first** (*rows 10, new 9, excluded 1,
exceptions 1, errors 1*), then Upload:
- **Row 11** is refused: "31-02-2026" is not a real date.
- **HL1004** is *excluded* (status Cancelled).
- **HL1005** is an *exception*: no tenure, so it is left out of the calculation until fixed.
- **HL1003** has two tranches (20 Oct and 5 Nov): one loan account, two records.

**IRR report**, as of **07-11-2026**, level Company:

| | Today (TD) | Month to date (MTD) | Year to date (YTD, from 1 Apr) |
|---|---|---|---|
| Home loans (HL) | 1 account · **9.00%** | 3 accounts · **9.06%** | 3 accounts · **8.97%** |
| Non-home loans (NHL / LAP) | 1 account · **12.00%** | 1 account · **12.00%** | 2 accounts · **13.04%** |

Check one by hand: HL, MTD = (30 lakh × 240 × 9 + 15 lakh × 180 × 9.5 + 10 lakh × 240 × 8.75) ÷ (30 × 240 + 15 × 180 +
10 × 240) = 1,11,450 ÷ 12,300 = **9.06%**. HL1006 (31 Mar 2026) is in the previous financial year, so not in YTD.
By branch (level Branch), YTD HL: Vijayawada **8.88%**, Guntur **9.50%**, Nellore **–** (no home loans).

Back on **Disbursement register → Reconciliation**, set the period to 01-11-2026 – 07-11-2026: all three checks are
green (branch totals = company total, region totals = company total, **year to date = sum of its months**). The
month-by-month table shows Aug, Oct and Nov 2026 with each month's numerator and denominator; HL1003 counts as one
loan account in the year although its tranches are in two months.

Then **IRR exceptions** → HL1005 → tenure **180** → save. The report changes: Guntur MTD HL **9.39%**, company MTD HL
**9.09%**, company YTD HL **9.00%**.

---

When you have finished, run Step 0 again for an empty system. For the client demo with a prepared week of data, see
`docs/client-demo.md`.
