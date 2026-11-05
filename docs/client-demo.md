# AHAM Sankalp: client demo script

A walk through the app for Aham, in the order of their document *Sankalp app: business logic, from SO entry to lead
ID* (v1). For each section: what the document asks for, what to show, and what to point out. About 75 minutes, plus
questions. The last part lists the decisions Aham must take before go-live.

The data is a realistic **last week** (Monday to Sunday before the demo day) for Vijayawada, Guntur and Nellore:
8 Sales Officers, about 380 entries, the daily runs, about 450 calls, lead cards, branch answers, corrections, the
follow-up tracker, a green-channel case and the MIS login register. **Today is left for the live part**: you make an
entry on the phone, run today's selection, make a call and answer a lead in front of the client.

Every example below is found by typing the person's name in the **Entries** search box.

The dates quoted below are for data built on Tue 3 Nov 2026 (last week = Mon 26 Oct to Sun 1 Nov). Built in another
week, the same names happen on the same weekdays; only the dates move.

---

## Before the meeting

**1. Fresh demo data on the morning of the demo** (it rebuilds "last week" relative to that day). In
`C:\Staunch\fieldsync`:
```bash
docker compose down -v
```
```bash
docker compose up -d --build
```
```bash
docker compose exec backend python -m app.seed
```
```bash
docker compose exec backend python -m app.demo_data
```
```bash
docker compose cp backend:/tmp/login-register-live.csv docs/demo-files/login-register-live.csv
```
```bash
docker compose cp backend:/tmp/login-register-saturday.csv docs/demo-files/login-register-saturday.csv
```
This deletes everything in the dev database and makes the demo week again (about 2 minutes). The last two commands
copy out the login registers made for this week's data: the one-row file for section 10 and Saturday's MIS file for
section 11. Place names on the map fill in over the next 10 minutes (needs internet).

**2. Web portals.** `cd admin-web && npm run dev`, then open http://localhost:5173. Sign in once in each window:

| Browser window | Portal | Account | Who |
|---|---|---|---|
| Normal window, tab 1 | /manage | AHFL90011 | Suresh Reddy, Branch Manager, Vijayawada |
| Normal window, tab 2 | /callcentre | AHFL90071 | Geetha M, Master owner |
| Normal window, tab 3 | /admin | AHFL90081 | Hari Prasad, Sankalp monitor (HR) |
| Private window, tab 1 | /callcentre | AHFL90061 | Divya S, caller |
| Private window, tab 2 | /manage | AHFL90031 | Prakash Rao, RBH, AP & TG |
| Private window, tab 3 | /admin | AHFL90099 | System admin |

All demo accounts use the password in `SEED_PASSWORD` (file `.env`). Each portal keeps its own sign-in, so one window
can hold all three portals.

**3. The phone.**
- Install `mobile/dist/aham-sankalp-1.2.0.apk`. Put the phone on the **same Wi-Fi as the PC**.
- Point the app at the PC's address of the day ("Phone and network" at the end, 1 minute).
- The database was wiped, so clear the app's old data first: Android Settings → Apps → AHAM Sankalp → Storage →
  **Clear storage**.
- Open the app and sign in as **AHFL90001** (Ravi Kumar, Sales Officer, Vijayawada).
- If you can, show the phone on the projector (for example Windows Phone Link or scrcpy). Otherwise pass it round.

---

## Opening (2 min)
Open http://localhost:5173.
- **Say:** one application replaces the three tools in section 0:
  - Google Forms → the **AHAM Sankalp app** for Sales Officers;
  - the Sankalp monitor workbook → the **HR & Admin portal**;
  - the Takeoff master → the **Call-centre portal**.
- Managers (BM, RTM, RBH, Product and Business Managers) get the **Management portal**.

## Section 0: how to read the document (3 min)
Section 0 says four things: what replaces what, the scope, the rule labels, and where the dates and numbers live.

1. **What replaces what.** Covered in the Opening: Google Forms, the Sankalp monitor workbook and the Takeoff master
   become the app and the portals.
2. **Scope.** **Say:** "From the SO's entry to the lead ID, the actions after it, and the login confirmed from the MIS
   register. The incentive money is not calculated: the app gives the flags and the Takeoff export for the incentive
   team."
3. **Rule labels.**
   - Unmarked rules are built.
   - **[Legacy]** rules are not built, because the app makes them unnecessary:
     - no UNRES placeholder IDs: the Emp ID always comes from the sign-in;
     - no name/number swap: the number box takes only a valid mobile;
     - no old-process verdicts.
   - **[Aham to decide]** points are not decided in code. Each is a setting that keeps today's behaviour.
4. **Dates and numbers.** HR & Admin (system admin, private window) → **Settings**.
   - **Show:** every value of section 14: Takeoff start 22 Sep, first call date 24 Sep, 30-day window, 9 unanswered,
     2 tries a day, 14 and 15-day windows, targets 10 and 5, green-channel limits ₹8 and ₹15 lakh.
   - **Show:** the [Aham to decide] switches, set to today's behaviour:
     - "Allow same-day calling": Off;
     - "A TCS ID repeated in the login register": the latest row wins.
   - **Say:**
     - "These are your numbers, stored as settings: changing one needs no programmer."
     - "Only the system admin can change them. Every change is in the Audit log with the old and new value."
     - "A change applies from the day it is saved; past days keep the values they had."

## Section 1: the flow from field meeting to login (5 min)
Put up the flow picture from section 1 of their document. **Say:** "Let me show you one real lead going through every
box." HR & Admin (monitor) → **Entries** → search **Venkata Ramana** → open it.

| Box in the picture | Where it is on the entry page |
|---|---|
| (1) Sankalp entry, Entry ID created | Top: `AHFL90001-…-101552`. "When and where": Submit pressed last Monday 10:15:52 |
| Daily cleaning | "The entry": SO, branch, region and spoke from the roster. "Mobile (as typed)" next to the cleaned number. "Entry date" and "Counts on" |
| (2) Selection | History: "selection · Allocate", Tuesday's run |
| (3) Allocation | "Calls": first caller Divya S, the caller of the day for Vijayawada |
| (4) Calling | "Calls": Tuesday, slot 09-10, Connected. A lead gets up to 9 unanswered tries, DSA/CP one (section 7) |
| (5) Classification | Status **Validated**, from the answers in "Answers on the last connected call" |
| (6) Lead card, lead ID | "Lead card": loan ₹35,00,000, TCS lead ID TCS-L-104512 |
| Action to branch / call centre | Next step "SO / branch visit" → branch action. "Branch answers": Suresh Reddy, Wednesday, A1 (KYC pending), login date Friday |
| (7) Login confirmed | "Outcome and flags": **Logged in**, TCS ID 4851203, login date Friday, **Sankalp success**. From the MIS register uploaded on Saturday (Uploads → history) |

- **Point out** the RAG: he is **NA** now because he logged in, so nothing is pending (section 9). For a Green lead,
  open **Kavitha Devi**.
- **Say:** "A lead ID is not a login." Kavitha Devi has a lead ID (TCS-L-415577) but no login, so she is still open.
  Only the register (or a TCS ID the Master owner types) logs a lead in.
- **Point out** the six things your document keeps apart, each in its own place:
  - Entry ID;
  - call outcome;
  - status;
  - RAG;
  - lead ID;
  - login.

## Section 2: people and their roles (6 min)
**Say:** "Each person has one role. The role decides where they sign in, what they see and what they may do. The
server checks it on every action; hiding a menu is not the protection."

**A. One place per role.** In a spare tab open http://localhost:5173/manage and sign in as **AHFL90001** (Ravi, an
SO). It is refused: "This account signs in at the Sales Officer app, not here."

**B. The roles of section 2, and where the client sees each one in this demo:**

| Role in the document | Demo person (Emp ID) | Signs in at | What they see and do | Shown in |
|---|---|---|---|---|
| Sales Officer (RO / RM / ABM) | Ravi Kumar (AHFL90001), RO | phone app | makes entries; sees own entries with status, RAG, action; numbers to correct | section 4 |
| Branch Manager | Suresh Reddy (AHFL90011), Vijayawada | Management | own branch only: leads to answer (one code, one date), open actions, missed dates, number corrections | sections 12–13 |
| RTM (Cluster Manager) | Anil Varma (AHFL90021), AP Coastal | Management | the cluster's branches; corrects the SO and customer numbers (BM does it where there is no cluster) | section 13 |
| RBH (Region Manager) | Prakash Rao (AHFL90031), AP & TG | Management | the region's figures; answers the leads of branches with no BM (Guntur, Nellore) | section 12 |
| Product / Business Manager | Meena Iyer / Karthik Raman | Management | all regions: dashboard, compliance, export | (optional) |
| Caller | Divya S (AHFL90061) | Call centre | only the entries on her list: tries, questions, lead card, TCS lead ID | sections 6–7 |
| Master owner | Geetha M (AHFL90071) | Call centre | daily run and caller per branch, priority, follow-up tracker (only she edits it), green channel, RAG override, manual TCS ID, register upload | sections 5, 6, 12, 13 |
| Sankalp monitor (HR) | Hari Prasad (AHFL90081) | HR & Admin | roster and attendance uploads, compliance, category and check-the-time queues, wrong-SO correction, Takeoff export, audit log | sections 3, 4, 13 |
| Credit / Ops (MIS) | Indira N (AHFL90091) | HR & Admin | only the login register upload | section 11 |
| System admin | AHFL90099 | HR & Admin | users and roles, organization, settings | sections 0, 14 |

**C. Show three menus live**, one tab each:
- **BM:** Entries lists only Vijayawada.
- **Caller:** the menu has only "My calls".
- **MIS:** sign in as AHFL90091 at /admin. The menu has only Uploads, with only the login-register card.

**D. Identity comes from HR.** HR & Admin (monitor) → **Employee roster**: everyone from the FOS Spoke upload, with
designation, branch and the joining and exit dates.
- **Anusha Reddy** (RM, Nellore) joined last Wednesday.
- **Naresh Goud** (RO, Guntur) left last Thursday: "Left" shows the date and he can no longer sign in.
- **Say:** "The SO never types an Emp ID or a branch. The app takes them from this roster."

**E. Who heads what.** HR & Admin (admin) → **Organization**.
- Vijayawada shows its BM, Suresh Reddy. Guntur, Nellore and the other AP & TG branches show **"No BM: RBH
  answers"**. AP Coastal shows its RTM; AP & TG shows its RBH.
- The other six regions have no RBH or BM in the demo data, so the page warns: **"Nobody answers the leads of 26
  branches"**.
- **Say:** "Your document says the RBH answers for a branch with no BM. The app works that out by itself, and this
  page warns HR when a branch has nobody to answer its leads."

## Section 3: reference data (6 min)
**Say:** "Section 3 lists six lookups: the roster, the branch–region map, attendance, holidays, the callers and the
login register. They are kept apart from the entries. An entry keeps a copy of who made it at that moment, so a later
roster change never rewrites old entries."

**A. The uploads** (HR & Admin, monitor → **Uploads**). Three cards, each with a **Template**:
- Employee roster (FOS Spoke);
- Daily attendance;
- Login register (MIS).

**Upload history** at the bottom shows last week:
- the roster on Monday morning;
- one attendance file each working day;
- the MIS register on Saturday;
- the roster again on Saturday, when HR added Naresh Goud's exit date.

**B. Live: "Check first" catches mistakes before anything is saved.** Sample files are in `docs/demo-files/`. Press
only **Check first**, never **Upload**, with these files.
1. Employee roster card → choose `roster-with-mistakes.csv` → **Check first**.
   - "Check only: nothing was saved. created: 1 · … · errors: 3". Click "3 row problems":
     - "Branch Vijayawada is in region AP & TG, not Karnataka";
     - "Cannot tell the role from designation 'Sales Executive' …";
     - "Emp ID is empty".
   - **Say:** "A branch must sit in its region, as Annex A says. The designation decides the role (RO, RM and ABM are
     Sales Officers). Nothing goes in until the file is clean."
2. Daily attendance card → `attendance-with-mistakes.csv` → **Check first**. Three row problems:
   - an Emp ID not on the roster;
   - a date that is not a date;
   - a missing status.

**C. Where each lookup lives:**

| Lookup in the document | Where | Point out |
|---|---|---|
| Employee roster (FOS Spoke) | Uploads; Employee roster page (section 2) | Emp ID, designation, branch, spoke, joining and exit dates |
| Branch–region map | Organization (admin) | 7 regions, 35 branches, optional clusters (Annex A at the end) |
| Attendance | Uploads; Settings → "Attendance codes that count as present" | P, P(MS), P(R), P(MS)(R) are present; any other code is absent; used by daily compliance (section 4.5) |
| Holidays | Settings → Holidays (monitor or admin) | An entry on a Sunday or a holiday counts on the next working day |
| Callers | Users & roles (admin), role Caller | Only active callers can be a branch's caller of the day |
| Login register | Uploads (MIS or Master owner) | All seven columns; up to 3 numbers per contact cell (section 11) |

Admin → **Settings** also shows **"Designation to role (roster upload)"**: RO, RM and ABM become Sales Officers. A new
designation can be added there, with no programmer.

## Section 4: the Sales Officer's entry (14 min, partly live)
**Say:** "Section 4 is the field entry: what the SO fills in (4.1), the Entry ID (4.2), the mobile number rules
(4.3), which day an entry counts on (4.4) and daily compliance (4.5)."

### 4.1 Entry fields (live on the phone, as Ravi Kumar)
1. Show **Today**:
   - today's entries against **10**, and Lead/Prospect against **5**;
   - the last 30 days' RAG counts;
   - the numbers the call centre could not reach, to give to the BM.
2. Tap **New entry**. **Point out:**
   - **No Emp ID, branch, region, spoke or date field.** They come from the roster and the phone's clock.
   - **Six category buttons.** Tap **Contact Point**: the CP sub-type appears (only for Contact Point). Tap **Lead**
     again.
   - Name, Mobile (WhatsApp), Description: all required, so Submit stays off until they are filled.
   - **Keka photo time** is its own field and never changes the Entry ID or dates.
   - Optional: take a photo. Each photo keeps its own time and GPS.
3. Fill: Lead, name "Demo Customer", mobile `+91 98490 11223`, description "Met at the demo". Tap **Submit**.
   **Say:** "One Submit is one person. 'Add another' starts the next one."

### 4.2 Entry ID (phone, then web)
1. Right after Submit the sheet shows the **Entry ID**: `AHFL90001-<today's date>-<time>`. **Say:** "Emp ID, date and
   time of the Submit tap, in India time, to the second. The phone makes it at once, even offline, the same way the
   server does."
2. **Offline:**
   - Turn on **airplane mode** and make a second entry: Lead, "Demo Offline", `98490 11224`.
   - Submit. The ID still shows, with "Saved on this phone · sends automatically", and the header shows "1 waiting to
     send".
   - Wait a minute and turn airplane mode **off**. The header changes to "All sent".
3. On the web (monitor → **Entries**) search **Demo**. Open both entries. **Point out:**
   - the same Entry ID as on the phone;
   - "Submit pressed" is the tap time, not when it arrived;
   - the GPS point is where Submit was pressed.
4. Prepared example, **Lakshmi Prasanna** (Kiran Kumar, last Tuesday 11:20), made at a site with no signal:
   - "Received by the server" shows 17:45, **synced 6 h later**;
   - her Entry ID, date and GPS are still from 11:20, where she was met.
5. **Say:** "The ID is never changed afterwards. If the SO is wrong, the RTM corrects the SO and the ID stays
   (section 13)."

### 4.3 Mobile number rules (live on the phone)
New entry → type in the Mobile box. The problem shows at once:

| Type | The phone says |
|---|---|
| `12345` | "A mobile number has 10 digits"; Submit off |
| `5848012345` | "A mobile number starts with 6, 7, 8 or 9"; Submit off |
| `+91 98490-11225` or `098490 11225` | accepted: +91, a leading 0, spaces and dashes are cleaned |

Leave this one unsaved (go back). On the web, **Venkata Ramana** shows "Mobile (as typed)" `+91 63276 81069` next to
the cleaned 10-digit number used for calling and matching. **Say:** "An invalid number can never be saved: the phone
blocks it and the server checks again."

### 4.4 Which day an entry counts on (web)
- **Ramesh Chowdary** (Ravi, made on **Sunday**): Entry date Sunday, **Counts on Monday**. The Entry ID keeps the real
  Sunday time.
- **Say:**
  - "A Sunday or holiday entry counts on the next working day. Saturday is a working day."
  - "Holidays are HR's list in Settings."
  - "On a Sunday or holiday the phone says which day today's entries count on."

### 4.5 Daily compliance (web, monitor → Daily compliance)
| Day (last week) | Point out |
|---|---|
| **Monday** | **Lakshmi Devi**: 10 entries but only 3 Lead/Prospect, so she met the 10 but is 2 short of the 5. **Anusha Reddy**: "Not joined yet" (joined Wednesday) |
| **Thursday** | **Kiran Kumar**: **AB**, from the attendance upload (even though he made one entry: attendance decides) |
| **Friday** | 7 SOs, not 8: **Naresh Goud** left on Thursday and is not listed after his exit date. The "met the target" card shows the count and % |

- **Show:** the **Region** filter, **Search Sales Officer**, and **Export** (a date range, CSV with both targets and
  shortfalls).
- **Say:** "Entries count on their count date. A repeat or duplicate entry does not count as a genuine Lead/Prospect."

### Check the time (monitor → Review queues → Check the time)
- **Chandra Sekhar:** Sai Teja's phone clock had been set back before the entry.
- **Bhavani Shankar:** Ravi's phone clock was 25 minutes fast.
- **Say:** "The time comes from the phone, so offline entries keep their real time. These two flags catch a phone
  clock that is wrong, for HR to check."

Note: today's live entries are called **tomorrow**. "Allow same-day calling" is Off, one of your [Aham to decide]
points. The live call in section 7 uses a weekend entry.

## Section 5: the daily selection (8 min, live)
**Say:** "Every morning the call centre decides which entries to call. 5.1 puts each entry in a call group, 5.2 says
which entries are fresh, and 5.3 runs seven checks in a fixed order. The first check that applies decides, and a
'Not called' result is final."

### 5.1 Call group and 5.2 fresh entries (1 min)
| Category | Call group |
|---|---|
| Lead, Prospect | Lead group: up to 9 unanswered tries |
| DSA/Connector, Contact Point | DSA/CP group: one calling day |
| Existing Customer, Existing Applicant | never called |

- **Show:** monitor → **Entries** → Category filter **Existing Customer**. Each says **"Not called (existing customer
  / applicant)"**, RAG **NA**. The dashboard counts them the same way.
- A **fresh** entry: has an Entry ID, was never selected, has a call group, its entry date is on or after the first
  call date (24 Sep, a setting), and its entry date is **before** the run date. Same-day calling is Off.

### 5.3 The seven checks, on last week's runs (3 min)
Call centre (Master owner) → **Daily run & allocation** → **Recent runs**: one line per working day.
- **Thursday's** line: 1 duplicate entry, 1 number already being called.
- **Friday's** line: 1 known contact, 1 spoken within 30 days, 1 repeat entry by same SO.

Open each example (monitor → Entries → search the name; each name has **two** entries):

| # | Check | Example | What happened |
|---|---|---|---|
| 1 | No valid number | (none) | cannot happen: the phone and the server refuse an invalid number (section 4.3) |
| 2 | Repeat entry by same SO (Lead group, 30 days) | **Suresh Babu** | Padma met him Monday and again Thursday; the second is not called |
| 3 | Duplicate entry (same run) | **Nagarjuna Rao** | Srinivas at 10:40 and Ravi at 16:20 the same day: the earliest Submit time wins |
| 4 | Number already being called | **Prasad Varma** | his number was in retry on Ravi's entry when Srinivas entered him again |
| 5 | Spoken within 30 days (Lead group) | **Hanumantha Rao** | the call centre spoke to him on Sai Teja's entry; Padma's later entry is not called |
| 6 | Known contact (DSA/CP group) | **Ganesh Hardware** | Lakshmi's entry was connected; Kiran's later entry is not called |
| 7 | Otherwise: Allocate | **Venkata Ramana** | on a caller's list the same morning |

**Say:** "Spoken to means a Connected call, nothing else. Each decision is stored with its run date and is in the
entry's history."

### Live: today's run (3 min)
1. "1 · Caller of the day per branch" → **Copy yesterday**, **before** the run. It fills and saves Saturday's callers:
   Vijayawada and Nellore → Divya S, Guntur → Farhan Ali (Sunday had no callers, so it takes the last day that had
   them). If you run first, the new entries wait with "have no caller yet"; Copy yesterday then puts them on the lists.
   Leave Nellore with Divya for now: section 6 changes it live.
2. "2 · Run the selection" → **Run for** (today's date). Under the button: "Run at (time) by Geetha M", then
   - **Selected for calling: about 45**: Saturday's and Sunday's entries;
   - **Put on lists: about 45 new, 20 retries, 2 follow-ups, 2 PRIORITY**. Retries are unanswered calls and
     callbacks due today.

   The button now says **Run again for** (date), and the run is a new line in **Recent runs**.
3. **Say:** "Today's own entries, including the two we made on the phone, are not in this run: they are called from
   tomorrow." Press **Run again**: the panel says **"Nothing new to select"**. "It only ever adds what is new."

**Rehearsal warning:** the first press of **Run** is the live moment, and it happens once a day. After a rehearsal
the panel still shows what that run did, but rebuild the demo data on the morning of the real demo ("Before the
meeting", step 1) to press it live again.

## Section 6: allocation to callers (6 min)
Master owner (Geetha), straight after the run in section 5. **Story:** "Divya has too much today, so Geetha gives
Nellore to Farhan. Watch what moves and what doesn't."

**Starting point** (after section 5): Vijayawada and Nellore → Divya, Guntur → Farhan. The **Callers** table says
about **Divya 51 open, Farhan 18**. (Rehearsing on used data: set those three callers and **Save** first. Saving moves
the new entries back to match.)

### Step 1: who has what (rule 1: new entries follow the branch)
Daily run → **Callers** table. **Say:** "Every new entry went to its branch's caller: Divya covers Vijayawada and
Nellore, Farhan covers Guntur."

### Step 2: live: give Nellore to Farhan
In "1 · Caller of the day", set **Nellore → Farhan Ali** and press **Save**.
- The page says **"Saved. 11 new entries not yet called went to the caller now set for their branch. Retries stay
  with their first caller."**
- The **Callers** table now says about **Divya 40, Farhan 29**. Only 11 moved, though Nellore has 19 entries on the
  lists (11 new and 8 retries).

### Step 3: the clear example: two Nellore customers, both entered by Sai Teja
My calls → **Caller** menu (top right; the Master owner can open any caller's list):

| | Revathi Kumar | Satyanarayana Varma |
|---|---|---|
| Branch, SO | Nellore, Sai Teja | Nellore, Sai Teja |
| Entered | Sat 31 Oct | Tue 27 Oct |
| Called before? | Never | 8 times by Divya, all unanswered |
| Where now | **Farhan's** list → New entries | **Divya's** list → Retries due |
| Why | Rule 1: new work follows the branch | Rule 2: old work follows the first caller |

- **Proof:** Entries → search **Satyanarayana Varma** → the **Calls** box lists Divya's 8 tries, and its header says
  "first caller Divya S".
- **Say:** "New work follows the branch. Old work follows the person, so the customer hears the same caller each
  time. His next unanswered call is the 9th, and then he is discarded (section 7)."

### Step 4: the order of a list (6.1, 6.2)
Caller menu → **Divya S**, top to bottom:
1. **PRIORITY (1)**, first: **Mohan Krishna** with the red label **"Branch: customer not answering"**. Proof: Entries →
   Mohan Krishna → **Branch answers**: code 3 by Suresh Reddy (BM Vijayawada) on Sat 31 Oct. Code 3 is "reopen for
   calling". (Farhan's list has one too: Ravi Teja Kumar, Guntur.) Then the other way to PRIORITY: open any entry →
   **Follow-up tracker** → the **Immediate call-back** switch ("Master owner: immediate call-back"). Show it; don't
   save.
2. **Retries due (15)**, oldest first: Satyanarayana Varma and Naga Lakshmi Chowdary (both 27 Oct, 8 unanswered). A
   retry is due when it is in retry, its callback date (if any) is today or earlier, it was not called today and it
   is not logged in (6.1). **Rajesh Kumar** shows the callback part: on Tue 27 Oct he asked to be called on Thursday,
   so he was not on Wednesday's list and came back on Thursday (his **Calls** box).
3. **Follow-ups (1):** Naga Lakshmi Murthy, "Take case forward".
4. **New entries (23):** Vijayawada's, from Saturday and Sunday.

### Step 5: unreturned work comes back (and the 1-day target)
- Daily run → **Recent runs** → the **2026-10-31** line: **Offered again 3**. Farhan didn't record **Naga Lakshmi
  Yadav**, Satyanarayana Reddy and Srinivasa Pipes & Fittings on Friday. Saturday's run gave them back to him. Proof:
  Entries → Naga Lakshmi Yadav → entered Thu 29 Oct, first call Sat 31 Oct.
- **Caller performance** → **Last week**: **First try on time 99% (277 of 280)**. The 3 late ones are exactly these
  3: the target is the first try within 1 day.
- Today's new entries show the yellow **First try overdue** label (tile: about 45). They are from Saturday and Sunday,
  and the target counts calendar days (on the decisions list). On a Monday demo only Saturday's are overdue.

### Don't press
**Move today's list to** (Callers table) is for a caller who is off: their whole open list goes to another caller for
the day. Show the menu only: it moves the *whole* list, so moving it back merges both lists into one, and section 7
needs Divya's list.

**If asked:** "Why 136 validated here and 121 on the dashboard?" This page counts **calls** by the day they were
made; a follow-up call to a validated customer counts again. The dashboard counts **entries**.

## Section 7: calling (10 min, live)
Private window, **Divya** (caller) → **My calls**. **Say:** "Now Divya picks up the phone. The screen tells her what
to ask, and the app decides the result, not the caller."

### Step 1: open the call (7.1)
New entries → **Ramesh Chowdary** (Lead; Ravi Kumar met him on Sunday 1 Nov, Vijayawada). The call screen shows:
- the top card: Entry ID, the number (tap to dial), and **"Lead group: 2 tries a day, up to 9 unanswered"**;
- **From the Sales Officer:** who met him, when, where, and the SO's description;
- on the right, **Record this try**: the **Time slot** (already set from the clock; the 10 slots of 7.1) and the
  9 **Outcomes**.

### Step 2: a connected call: the questions of 7.2
Press **Connected**. The questions appear, and under them **"This call will be classified as Amber – answers
missing"**: nothing is answered yet. Answer as the customer would:
- Name check **Same person** · Visit **Yes** · Do you know the SO personally? **No** · Loan need **Home purchase**:
  the line now says **Validated**.
- **Show the app deciding:** switch Visit to **No** → "Validated – visit not confirmed"; back to **Yes** → "Validated".
  **Say:** "The caller never picks a status. Section 8 has the full order."
- Timeline 1–3 months · Income Salaried · Documents Partly · Next step **SO / branch visit** · Purpose Discuss
  eligibility · Own contribution Partly · Name as given · Remarks.
- **Next date:** type **Sunday 8 Nov** → "A Sunday is not a working day: pick another date" and Save is blocked.
  Pick **Monday 9 Nov**.

Press **Save try** → **"Saved: Validated"** with **GREEN**. Below: **"Next for the branch: Visit customer · 2026-11-09"**
(section 12 picks this up).

### Step 3: the lead card (7.4)
It opens because the loan need is a loan type. Fill a few fields to show the rules:
- **Loan requirement:** `40L` → **"Digits only, e.g. 4500000"**, Save blocked. Then `35,00,000` → it reads back
  **"₹35,00,000 (35 lakh)"**. **Say:** "No more '7 lacks' or '40L' in the data."
- **CIBIL score:** `950` → "Between 300 and 900; blank if the customer does not know". Then `745`.
- **Property pincode:** `52001` → "6 digits". Then `520010`.
- **TCS lead ID:** type one, then clear the loan amount → "Compulsory once a lead ID is entered". Put it back.
- **Handling branch:** blank = the SO's branch; only for a property in another branch's area.
- **Save lead card** → "Saved". **Say:** "The lead ID never closes a lead. It isn't a login and doesn't validate
  anything; only the login register confirms a login (section 11). And no more mail to the branch: the lead is on
  the branch's own list (section 12)."

Back on **My calls**: Ramesh Chowdary has left Divya's list. On Daily run, Divya's **Tries today** is now 1.

### Step 4 (optional, 30 s): a DSA/CP gets one try
New entries → **Rambabu Yadav** (DSA/Connector, Vijayawada). The card says **"DSA/CP group: 1 try, one day"**. Outcome **RNR** →
**Save try** → **"Saved: Closed – no answer"**. One unanswered try closes a DSA/CP; a Lead would stay for 9.

### Prepared examples (Geetha's window → Entries → search the name → the Calls box)
| Example | What it shows (7.1, 7.3) |
|---|---|
| **Prasad Varma** (Ravi's entry, 26 Oct) | 9 tries: two a day Tue–Fri, one on Sat, all unanswered → **Discarded – 9 unanswered**, RAG RNR |
| **Balaji Constructions** (DSA/Connector) | one try, RNR → **Closed – no answer** |
| **Rajesh Kumar** | Tue 27 Oct **Callback requested** for Thu 29 Oct; back on the list Thursday → Connected → **Validated** |
| **Sri Sai Cements** (Contact Point, Nellore) | "Needs a home loan himself?" **Yes** → the Lead questions → **Validated – converted from DSA/CP**, with a lead card |

**Rehearsal note:** the live call uses up Ramesh Chowdary (and Rambabu Yadav). Rebuild the demo data on the demo
morning, as for section 5.

## Section 8: classification (6 min)
**Say:** "Every call gets a status from fixed rules, checked in the order of your document; the first rule that
matches decides. The entry's status is the one from its latest call."

### Step 1: the order of the lead rules, live (8.1), without saving
Divya's window → My calls → New entries → **Aruna Rao** (Lead, Ravi Kumar, Saturday) → **Connected**. Change one answer at a time
and read the line "This call will be classified as …":

| Change | The line says | Rule |
|---|---|---|
| (nothing yet) | Amber – answers missing | 1: loan need blank |
| Loan need **Not looking for a loan** | Red | 2 |
| Loan need **LAP** | Not counted – LAP | 3 |
| also Relationship **Yes – the same officer** | still **Not counted – LAP** | 3 comes before 5: the first match wins |
| Loan need **Home purchase** | Amber – knows SO | 5 |
| Relationship **No**, Documents **File already logged with Aham** | Already in process | 4 |
| Documents **Yes**, Name check **Different person – same family** | Validated – different person | 6 |
| Name check **Same person**, Visit **No** | Validated – visit not confirmed | 7 |
| Visit **Yes** | Validated | 8: otherwise |

Then go back with **← My calls**. **Don't press Save try**: nothing is recorded.

### Step 2: DSA/CP (8.2), live, without saving
New entries → **Annapurna Sastry** (Contact Point) → **Connected**:
- nothing chosen → **DSA/CP – no RAG**; RAG given by caller **Green** → **DSA/CP – Green**;
- Needs a home loan himself? **Yes** → the Lead questions appear; Loan need **Home purchase** → **Validated –
  converted from DSA/CP**. Back to My calls without saving.

### Step 3: not connected (8.3)
Master owner → **Entries** → the **Status** filter (every status of 8.1–8.3 has entries):

| Last outcome | Status | Example |
|---|---|---|
| Invalid number | Discarded – invalid number | Nagaraju Rao |
| Wrong person | Amber – wrong person | Durga Prasad |
| Refused to talk | Rejected – refused to talk | Vijaya Reddy |
| DSA/CP, unanswered | Closed – no answer | Balaji Constructions |
| Lead, unanswered, under 9 | In retry | Satyanarayana Varma (8) |
| Lead, 9 unanswered | Discarded – 9 unanswered | Prasad Varma |

### Step 4: real entries, rule by rule
Entries → search the name → **Answers on the last connected call** and the **Calls** box:

| Entry | Deciding answer | Status |
|---|---|---|
| **Ravindra Babu** | Loan need LAP | Not counted – LAP |
| **Sireesha Chowdary** | Documents: File already logged with Aham | Already in process |
| **Padmavathi Achari** | Knows the SO: Yes – the same officer | Amber – knows SO |
| **Mahesh Kolli** | Name check: Different person (knows "another employee", which is not rule 5) | Validated – different person |
| **Revathi Pothula** | 3 unanswered tries, then Connected with Visit No | Validated – visit not confirmed |

**The latest call decides:**
- **Siva Kumar:** Tue 27 Oct, Loan need left blank → Amber – answers missing. Called again Thu 29 Oct →
  **Validated**.
- **Krishna Murthy:** Tue 27 Oct Validated. Wed 28 Oct "Not looking for a loan" → **Red**: a lost lead.

**8.4 (old-process verdicts):** not built. They matter only if the history before 22 Sep is imported (decisions
list, item 3).

**If asked:** "Can a caller change a status by hand?" No. Only another call changes it. The Master owner can
override the **RAG** (section 9), not the status.

## Section 9: RAG (5 min)
**Say:** "The status says exactly what happened on the call. The RAG is the one-word colour that tells the SO and
the managers what to do about it."

### Step 1: the picture
Monitor → **Dashboard** → **Last week**: the RAG mix of about 382 entries (by count date). Roughly Green 131, NA 110,
Pending 43, RNR 38, Amber 35, Red 25. **Say:** "Green: work in progress. Amber: the SO must fix something. Red: the
customer said no. RNR: we could not reach them. NA: nothing to do. Pending: not called yet."

### Step 2: the table of section 9, one real entry per row
Master owner → **Entries** → search the name (or use the **RAG** filter):

| Status | RAG | Search |
|---|---|---|
| Not called yet / waiting | **Pending** | **Naga Babu Basha** (Saturday, on Divya's list) |
| Not called (repeat, duplicate, known contact, …) | **NA** | **Suresh Babu**: his second entry, "repeat entry by same SO" |
| Red / DSA/CP – Red | **Red** | **Seshu Raju** / **Gopal Reddy** |
| Amber statuses, DSA/CP – Amber, Discarded – invalid number | **Amber** | **Durga Prasad** (wrong person), **Gopal Kolli** (DSA/CP – Amber), **Nagaraju Rao** (invalid number) |
| In retry, at least one unanswered | **RNR** | **Satyanarayana Varma** (8 unanswered) |
| In retry, none unanswered | **Green** | none right now; **Rajesh Kumar** was, from his callback request on Tuesday to Thursday's call |
| Discarded, Closed – no answer | **RNR** | **Prasad Varma**, **Balaji Constructions** |
| DSA/CP – Green / DSA/CP – NA | **Green** / **NA** | **Mahesh Prasad** / **Balaji Sand Suppliers** |
| Any other status with an open action | **Green** | **Siva Kumar**: Validated, "Visit customer" open |
| Otherwise | **NA** | **Sireesha Chowdary**: Already in process, nothing open |
| Logged in or rejected (checked first) | **NA** | **Venkata Ramana**: Validated, then logged in |

"Not called – no valid number" would be Amber, but it cannot happen: the phone refuses an invalid number.

### Step 3: the three special cases
- **A lost lead is NA, not Red. Krishna Murthy:** Validated on Tue 27 Oct; on Wed 28 Oct he said "Took a loan from a
  local bank last week" → status **Red**, RAG **NA**. **Say:** "Red is for a customer who was never real or never
  wanted a loan, which is the SO's problem. A lost lead is not the SO's fault."
- **The Master owner's override wins. Anjali Devi:** status **Red**, but the RAG shows **Amber\*** (hover: "Set by the
  master owner"). Open the **Follow-up tracker**: RAG override **AMBER**, note "Son may need a loan after the harvest;
  check in January". The automatic RAG is kept underneath; clearing the override brings Red back.
- **Logged in or rejected is NA**, before everything else: Venkata Ramana above.

### Step 4: what the SO sees
- **Amber = something to fix within 15 days of the entry.** **Durga Prasad** (Padma Priya's entry, 29 Oct): Amber –
  wrong person → the SO action **"Correct customer number"**, open until **13 Nov**. It is on Padma's phone (Today →
  the numbers to give to the BM), and the BM or RTM can correct it (section 13).
- On the phone: **My entries** shows each entry's RAG; **Today → Last 30 days** counts Green, Amber, Red, RNR, Pending
  and NA for that SO.

## Section 10: incentive flags (5 min, one live upload)
**Say:** "The app doesn't calculate money. It gives the incentive team four flags per entry, and they apply the
payout rule."

### Step 1: the four flags on one entry
Master owner → Entries → **Venkata Ramana** → **Outcome and flags**:

| Flag | Rule (section 10) | Venkata Ramana |
|---|---|---|
| **Customer validated** | A "Validated…" status (all four kinds), **or** logged in and not LAP; never a repeat by the same SO | Yes |
| **First validation for this number** | The earliest validated entry for that mobile, from any SO: paid once per customer | Yes |
| **Validated on** | The date of the call that validated it | Tue 27 Oct |
| **Counts as Sankalp success** | Section 11.3 (next section) | Yes |

### Step 2: each rule, on a real entry
| Search | Shows |
|---|---|
| **Revathi Pothula** / **Mahesh Kolli** / **Sri Sai Cements** | "Validated – visit not confirmed", "– different person", "– converted from DSA/CP": all four Validated kinds count |
| **Siva Kumar** | Validated on **Thu 29 Oct**: the call that validated him, not Tuesday's "answers missing" call |
| **Suresh Babu** (second entry) | A repeat by the same SO: never validated, so the SO can't be paid twice for one meeting |
| **Ravindra Babu** | Logged in, but a **LAP**: not validated (it is still a Sankalp success, section 11) |

### Step 3, live: paid once per customer
**Hanumantha Rao** has two entries: **Sai Teja's** (Mon 26 Oct, called and validated) and **Padma's** (Thu 29 Oct,
not called: spoken within 30 days). Show both: only Sai Teja's is validated.
1. Master owner → **Login register** (menu "Data") → choose `docs/demo-files/login-register-live.csv` (one row:
   Hanumantha Rao's number, logged in today) → **Check first**: **1 row, 2 entries matched, no errors** → upload.
2. Open both entries again:
   - **Sai Teja's:** Logged in · Customer validated **Yes** · First validation **Yes** · Sankalp success **Yes**.
   - **Padma's:** Logged in · Customer validated **Yes** (through the login) · First validation **No**.
3. **Say:** "Both SOs met a real customer who logged in, but the customer is paid for once: to the first entry."

### Step 4: the file for the incentive team
Monitor (HR & Admin) → **Takeoff export** → pick last week → **Download CSV**. One row per entry: Entry ID, credited
SO, branch, dates, status, RAG, "Repeat entry by same SO", the four flags, lead outcome, TCS ID, login date. The page
explains each flag. Last week: 384 entries, 121 validated, 10 Sankalp successes (before the live upload).

**The payout rule** (₹60 per validated lead from 5 a day) is not built; the app only gives the flags. It is on the
decisions list (item 4).

**If asked:** "Krishna Murthy was validated on Tuesday; why isn't he validated now?" His Wednesday call made him Red,
and the flag follows the latest status. Whether a later call should take a validation away is decision 1.

**Rehearsal:** the upload uses up the live moment (the two entries stay logged in). Rebuild on the demo morning; the
rebuild makes a fresh file.

## Section 11: login register and Sankalp success (4 min, one check)
**Say:** "Section 10 used logins. This is where they come from: MIS uploads the TCS login register, and the app
matches it to our entries by the customer's mobile."

### Step 1: the register MIS uploaded on Saturday
1. Open `docs/demo-files/login-register-saturday.csv` (Excel or Notepad): the file MIS (Indira N) uploaded on
   Sat 31 Oct. 12 logins. Point at:
   - **4851203:** two numbers in one cell, `6599549363 / 6327681069`;
   - **4851288:** product **LAP**;
   - **4851301** (branch walk-in) and **4851302** (DSA, `… & …`): not Sankalp customers. They match no entry, and
     that is fine.
2. Master owner → **Data → Login register**. Upload history at the bottom: Saturday's file by Indira N, 12/12 rows,
   0 problems (and your section 10 upload).
3. Choose the same file → **Check first** (saves nothing): **rows 12 · tcs ids 12 · numbers 15 · entries matched 10 ·
   errors 0**. **Say:** "12 rows held 15 numbers. Every number is cleaned like the SO's entry and matched; 10 of our
   entries logged in." No need to press Upload.

### Step 2: the three lead outcomes (11.2)
Master owner → **Entries** (the outcome is the blue line under the status; the entry shows it in **Outcome and
flags**):

| Search | Lead outcome | Why |
|---|---|---|
| **Venkata Ramana** | Logged in | TCS 4851203, login Fri 30 Oct, after his entry (Mon 26 Oct). Matched on the **second** number in the cell: his entry has 63276 81069 |
| **Lakshmi Narayana** | Logged in, TCS 4851377 **(entered by hand)** | The register had his wife's mobile, so the Master owner typed the TCS ID on the follow-up tracker (Fri 30 Oct). A typed TCS ID counts as a login; there is no login date |
| **Usha Rani** | Login on/before entry date (not counted) | Register login Mon 26 Oct (a branch walk-in); the SO met her Tue 27 Oct. Her call still validated her, but the login is not a Sankalp success |
| **Gopi Krishna** | Rejected | Master owner's tracker: "Chose another lender (SBI)" |
| **Hymavathi Chowdary** | Rejected | Branch answer R5, customer not interested |

Lead outcome applies only to lead-type entries: the Lead group, DSA/CP converted to a lead, or entries with a lead
action.

### Step 3: Sankalp success (11.3)
All three must hold: lead outcome **Logged in**; entry date on or after **Takeoff start** (22 Sep, in Settings); the
**earliest** entry for that TCS ID (same date → the lower Entry ID). One success per TCS ID.
- **Ravindra Babu:** a LAP login. Sankalp success **Yes**, Customer validated **No** (status "Not counted – LAP").
  **Say:** "LAP counts for Sankalp, not for the incentive."
- **Hanumantha Rao** (section 10): TCS 4851410 matched both entries. Success goes only to **Sai Teja's** (Mon 26 Oct),
  the earliest; **Padma's** (Thu 29 Oct) is Logged in, success No.
- Last week: 10 Sankalp successes before the section 10 upload, 11 after.

**If asked:**
- *"What if the register has the same TCS ID twice?"* The row uploaded last wins (Settings → "A TCS ID repeated in
  the login register"). The .md marks this [Aham to decide]; it is on "Rules to confirm".
- *"Three numbers, or rubbish in the cell?"* Up to 3, split on `, / & ;` or spaces. A row with no valid mobile is
  kept and listed as a row problem, for matching by hand.
- *"Two entries on the same day for one TCS ID?"* The lower Entry ID (the earlier Submit) wins. Tested, not in the
  demo data.
- *"What if the earliest entry is an Existing Customer or a DSA?"* Decision 2.

**Rehearsal:** Check first saves nothing, so repeat it freely.

## Section 12: actions and branch answers (10 min, three live steps)
**Say:** "After every call the app works out who does what next: the SO and branch, or the call centre. The branch
answers each lead with one code and one date, and the app follows that date."

### Step 1: the action after each call (12.1, 12.2)
Suresh Reddy (BM, Vijayawada) → **Open actions**: 62 open. Click through the **Action** filter:

| Action | Count | Example | Why |
|---|---|---|---|
| Visit customer | 34 | **Kavitha Devi** | The caller chose next step "SO / branch visit"; the date is the Next date |
| Collect documents | 6 | **Appa Rao Setty** | Documents "Partly" or "No" |
| Follow up lead | 4 | **Lalitha Goud** | Validated, no visit asked, documents complete |
| DSA/CP follow-up | 12 | **Sai Ram Steel Traders** | A DSA/CP rated Green |
| Correct customer number | 6 | **Durga Prasad** (open until 13 Nov) | Wrong person or invalid number: open 15 days from the entry |

**Expired unworked** is empty in the demo week: lead actions never expire, a DSA/CP follow-up runs out 14 days after
its date and "Correct customer number" 15 days after the entry. The first ones run out next week.

The call centre's side: Geetha → **Call-centre actions** (5):
- **Take case forward:** Naga Lakshmi Murthy, Kalyani Dasari. The caller's next step was "Call centre to continue".
- **Follow-up:** Venu Gopal (19 Nov), Raghu Basha, Jyothi Prasad. The branch gave a date more than 14 days away.
- **Callback** (a customer in retry who asked for a call on a date): none open now. A "Callback requested" call makes
  one.

### Step 2: Leads to answer (12.4), live
Suresh Reddy → **Leads to answer**: 46 validated leads, each with its action and date, the last answer and the RAG.
- The gold note at the top: **Missed dates: Vijayawada 13** (on Thu 5 Nov; it grows by the day). Those rows are red,
  "(date passed)", for example **Veeraiah Reddy**, A1 · 31 Oct.
- **Live 1, a date within 14 days:** **Appa Rao Setty** (Ravi's lead, Collect documents) → **Answer**.
  1. The codes are grouped: Closing, Rejected, Documents / login pending, Waiting. Choose **A2 · Documents pending:
     income proof**. A **Login date** field appears, with the 14-day note under it.
  2. Pick yesterday → Save: refused, **"The date must be today or later"**.
  3. Pick a date about a week out → Save. The row shows **Collect documents · that date** and **A2 · … · that date**.
- **Live 2, a date more than 14 days away:** **Bhanu Raju** (Ravi's lead, Visit customer) → **E2 · Customer asked for
  time: out of station** → a date three weeks out → Save.
  - The row now says **"With the call centre: Follow-up (date)"**. Geetha → **Call-centre actions**: Bhanu Raju is
    there, next to Venu Gopal (the same case, prepared: "Customer in Hyderabad until the 20th").
  - **Say:** "Beyond 14 days the branch stops chasing it; the call centre calls the customer on that date."

Prepared answers for the other codes (search in Entries):

| Code | Example | What happened |
|---|---|---|
| 1 Logged in | **Seshu Naidu** | The branch says logged in, but the lead stays open until the login register shows it |
| 2 Category wrong | **Ramu Yadav**, **Sambasiva Rao** | Sent to the monitor's Review queues (section 13) |
| 3 RNR | **Swathi Reddy**, **Mohan Krishna** | Not answering the branch: the call centre retries at once, as PRIORITY (section 6) |
| R5 | **Hymavathi Chowdary** | Rejected: the lead closes, RAG NA |

### Step 3: the green channel, live
**Say:** "For small loans the branch cannot reject on income (R2) or credit score (R3). Self-construction up to ₹8
lakh and purchase up to ₹15 lakh, on the call centre's loan amount. Head office checks first."
- **Bhaskar Rao** (₹6 lakh self-construction, Srinivas's lead): R2 on Wednesday, held. Geetha sent it **back to the
  branch** on Thursday, so it is still open as Visit customer.
- **Kavitha Devi** (₹12 lakh home purchase, Ravi's lead): R3 on Friday. Suresh Reddy's row says **"green-channel check
  pending"**.
  - **Live:** Geetha → **Green channel** → Kavitha Devi → **Back to branch**. Suresh Reddy's row loses "check
    pending", and the lead stays open with the branch.
  - "Accept reject" would close it as rejected instead.

### Step 4: a branch without a BM
Prakash Rao (RBH, private window) → **Leads to answer**: 60 leads: **Guntur 39** and **Nellore 20** (no BM there), and
one Vijayawada lead:
- **Pradeep Kumar**, "Handled by Guntur": Ravi's customer is buying in Guntur, so Guntur works it (F1, BM visit) and
  Ravi keeps the credit.
- The note shows the missed dates for all three branches: Vijayawada 13 · Guntur 12 · Nellore 6.

### Step 5: the SO sees it
Ravi Kumar's phone → **My entries** → **To follow up** (pull down to refresh): **Appa Rao Setty** now shows **Collect
documents · the date the BM gave**. **Bhanu Raju** has left the list: he is with the call centre now.

**Rehearsal:** the three live answers stay done. Rebuild on the demo morning.

## Section 13: corrections (6 min, two live steps)
**Say:** "Mistakes happen in the field: a wrong number, the wrong SO, the wrong category. Each has one person who
fixes it, the Entry ID never changes, and the history keeps the old and the new."

### Step 1: wrong customer number (13.2), live
**Mohan Krishna** first (prepared): the whole story is in his **History**:
1. Wed 28 Oct, Divya: "Wrong person" → Amber, action "Correct customer number".
2. Thu 29 Oct, Suresh Reddy: **correction: number**, old 8177822690 → new 7015197548, cycle 2.
3. Fri 30 Oct, Divya calls the new number → **Validated**. Same Entry ID throughout.

**Live:** Suresh Reddy → **Open actions** → **Correct number** filter → **Durga Prasad** (Padma's lead, "Amber – wrong
person", open until 13 Nov) → open the entry → **Correct number**.
1. Type `12345` → refused: "Enter a valid 10-digit mobile number starting with 6, 7, 8 or 9".
2. Type `90000 12345` → save. The entry is **In retry**, cycle **2**, unanswered count back to **0**, and the "Correct
   customer number" action is gone.
3. **Say:** "No new entry and no new ID. The next run puts her on Divya's list as a retry, with a fresh 9 tries,
   because Divya made the first call."

If asked: a number can be corrected only within **15 days** of the entry, by the BM or the RTM (the RBH only for a
branch with neither).

### Step 2: wrong SO (13.1)
**Narasimha Rao** (prepared): the Entry ID starts with Srinivas's code (AHFL90003), but Padma met him. History:
**correction: so** by **Anil Varma** (RTM) on Thu 29 Oct: old SO Srinivas Naidu → new SO **Padma Priya**. The entry now
shows Padma, and her counts and credit include it.
- **Say:** "The ID records who typed it; the credit follows who really met the customer."
- If asked "can the BM do it?": not in Vijayawada, which has a cluster. The BM gets "This branch has a cluster: its
  RTM corrects the SO". The monitor can also correct the SO (entry → **Correct SO**).

### Step 3: category wrong, live
The BM answered code 2 on **Ramu Yadav** on Thursday: "Has his down payment ready: a Lead, not a Prospect".
- **Live:** Hari Prasad (monitor) → **Review queues** → **Category wrong (branch code 2)**: Ramu Yadav is the only one
  → Review → Category **Lead** → save. The queue is empty, and the entry shows Lead.
- **Sambasiva Rao** was reviewed the same way on Thu 29 Oct (History: "category review", prospect → lead, "Checked
  with the branch: ready to buy now").
- The same page has **Check the time**: entries whose phone clock looked wrong.

### Step 4: the Master owner's follow-up tracker (13.3)
Geetha → **Follow-up tracker**: one row per entry, Master owner only, filtered by owner (Branch / Call centre / Done).
Four rows:

| Entry | What Geetha set | Effect |
|---|---|---|
| **Siva Kumar** | Owner Call centre, **Reopen for calling** ("Loan need not asked; call again") | Called again next day → Validated |
| **Gopi Krishna** | Owner Done, **Rejected**, reason "Chose another lender (SBI)" | Lead closed, RAG NA |
| **Lakshmi Narayana** | Owner Done, **Logged in**, TCS ID 4851377 | Counts as a login (section 11) |
| **Anjali Devi** | **RAG override Amber** ("Son may need a loan after the harvest") | Shows Amber* instead of Red (section 9) |

**Say:** "Where the tracker and a branch answer disagree, the later date wins."

**Rehearsal:** both live corrections stay done. Rebuild on the demo morning.

## Section 14: settings (2 min)
Already shown in section 0. Optionally:
- Change "Branch date threshold" from 14 to 10 and save.
- The branch answer dialog now says "within 10 days".
- Set it back to 14.
- The **Audit log** shows both changes, old → new.

## Section 15: what the Excel set-up gets wrong (3 min)
| Excel problem | Shown in |
|---|---|
| SO types or changes the Emp ID | section 4: no such field, it comes from the roster |
| Invalid mobile numbers | section 4: refused while typing, and by the server |
| SO picks another branch | section 4: branch and region come from the roster |
| One form for several people | section 4: one entry per Submit, "Add another" |
| "5 lakh" in an amount box | section 7: "40L" is refused, amounts are numbers |
| A number in the 2nd or 3rd place of the contact cell | section 11: Venkata Ramana |
| Lists cut at a fixed row count | Entries, Open actions, tracker and queues have pages and totals |

## Annex A and Annex B (2 min)
- HR & Admin (admin) → **Organization**: the 7 regions and 35 branches of Annex A. Madurai (RoTN U) and Krishnagiri
  (RoTN C) are placed as Annex A lists them, with the open question shown.
- Monitor → Entries → **Status** filter: the Annex B values, word for word. Nobody types a status.

---

## Decisions we need from Aham
**Before go-live (important)**
1. **Which calls change a lead's status** (19.1)? Today every call does. A validated lead whose follow-up call is
   unanswered goes back to "In retry", and "Customer validated" switches off until someone reaches the customer.
   - Options: keep it;
   - only connected calls change a validated lead;
   - follow-up calls never change it.
2. **Which entries compete for the Sankalp success** (23.1)? Today every entry with the matching number does. If an
   Existing Customer / Applicant or DSA/CP entry is the earliest, no entry gets the success.
3. **Last weeks' history** (since 22 Sep): import the Excel workbooks or not? The 30-day, known-contact,
   first-validation and one-success rules look back at earlier entries.
4. **The payout rule** (₹60 / 5 a day): the app gives the flags only.
5. **Data:**
   - the real branch codes;
   - the full roster;
   - Madurai and Krishnagiri;
   - the full names of RoTN C / T / U.

**Rules to confirm** (the app follows the reading in brackets)
- Same SO, two entries in the same second (the second gets "-2").
- "+91 0…" numbers (refused; retype without the 0).
- An SO with no attendance row (counted as present, "not marked").
- A frozen copy of each day's compliance (no; the report is live, and late offline entries still count).
- "Being called" also covers an entry waiting for its first call (yes).
- An offline entry that arrives after another SO's entry for the same number (the one already called keeps it).
- Unreturned new entries go to today's caller of the branch (yes).
- A third try on the same day (allowed; two are planned).
- Next date required for "SO / branch visit" (no).
- What follows "Amber – answers missing" and "Amber – knows SO" (no action today).
- RAG rows: "logged in / rejected → NA" first (yes).
- "Latest register row" means the row uploaded last (yes).
- After "Correct customer number" expires, the entry stays Amber (yes).
- Tracker date and branch date on the same day: the tracker wins (yes).
- A corrected number is called without the selection checks (yes).
- The two 15-day settings (kept equal).
- Turnaround "1 day" in calendar days, so Saturday → Monday is late (yes).
- When the monitor changes a validated lead to Existing Customer / Applicant, does its branch action close? (Today it
  stays open.)
- Should the RBH receive a sent daily summary (today: on screen only)?

**Lists to supply**
- Is the Keka photo time required?
- The full CP sub-type list.
- What each DSA/CP RAG choice means, for the callers.
- Fixed lists for the lead card (property type, purpose, vehicle).
- The exact LAP product names in the register.

---

## Phone and network
The app talks to the server on this PC over the Wi-Fi. The Wi-Fi gives the PC a new address from time to time (it
changed between 2 and 3 November), so the app lets you type the PC's current address.

**App:** `mobile/dist/aham-sankalp-1.2.0.apk`. Install it the day before; it replaces the app already there and keeps
its data. Its built-in address is `192.168.14.106` (the PC on 3 November).

**On the demo day, with the PC and the phone on the same Wi-Fi:**
1. On the PC run `ipconfig`. Under "Wireless LAN adapter Wi-Fi", note the **IPv4 address**, for example
   `192.168.14.106`.
2. On the phone:
   - **Signed out:** on the sign-in screen, under the Sign in button, tap **Change** next to "Server".
   - **Already signed in:** tap **Me**, then **Change**.
3. Type the address. Port 8000 is added, so `192.168.14.106` is enough. Tap **Check and use**.
   - "Connected to http://…:8000": done. The app remembers it.
   - "No answer from …": the phone is not on the same Wi-Fi, or the address is mistyped. A Wi-Fi that keeps devices
     apart (common for guest Wi-Fi) also gives this message; use the PC's **Mobile hotspot** instead (below).
4. Optional check from the phone's browser: http://<the address>:8000/docs opens.

**If the Wi-Fi keeps devices apart:**
1. Turn on Windows Settings → Network & internet → **Mobile hotspot** on the PC.
2. Connect the phone to it.
3. In the app, change the server to `192.168.137.1` (the PC's address on its own hotspot).

Changing the server keeps the entries waiting on the phone; they go to the new address. The older apps in
`mobile/dist/` (1.1.0) have a fixed address and are no longer needed.
