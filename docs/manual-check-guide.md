# Manual check guide: the 29 review steps

A walk through the app, one review step at a time, in the order of `docs/feature-review.md`. Each step says what the
document asks for, what to do, and what you should see. Tick the boxes as you go. Items marked **(fix 10.1)** are the
fixes made on 2026-11-01; the number points to the same item in `feature-review.md`. Items for Aham to answer are
listed at the end of each step but need no test.

Plan about half a day. A few checks need a second day (a callback date, an entry back on the list after a corrected
number): they are collected in **Next-day checks** at the end.

## Before you start

**What must be running**
- Backend and database: `docker compose up -d` in `C:\Staunch\AHAM\AHAM`. Check: http://localhost:8000/docs opens.
- Web portals: http://localhost:5173 (from `cd admin-web && npm run dev`).
- The phone app **AHAM Sankalp 1.1.0** on your phone (same Wi-Fi as the PC) or on the emulator. The server address is
  built into the app, so it must be the PC's **current** Wi-Fi address (`ipconfig`, "Wireless LAN adapter Wi-Fi",
  IPv4). On 2026-11-02 that is `192.168.14.102`: use `mobile/dist/aham-sankalp-1.1.0-192.168.14.102.apk`. The app's
  **Me** tab shows version 1.1.0 and the server it uses. If the PC's address changes, the app needs a rebuild.

**Accounts.** Every demo account uses the same password: `SEED_PASSWORD` in `C:\Staunch\AHAM\AHAM\.env`.

| Who | Emp ID | Where they sign in |
|---|---|---|
| Ravi Kumar, Sales Officer, Vijayawada | AHFL90001 | phone app |
| Lakshmi Devi, Sales Officer, Guntur | AHFL90002 | phone app |
| Suresh Reddy, Branch Manager (BM), Vijayawada | AHFL90011 | Management portal |
| Anil Varma, Cluster Manager (RTM), AP Coastal | AHFL90021 | Management portal |
| Prakash Rao, Region Manager (RBH), AP & TG | AHFL90031 | Management portal |
| Meena Iyer / Karthik Raman, Product / Business Manager | AHFL90041 / AHFL90051 | Management portal |
| Divya S, Farhan Ali, callers | AHFL90061, AHFL90062 | Call-centre portal |
| Geetha M, Master owner | AHFL90071 | Call-centre portal |
| Hari Prasad, Sankalp monitor (HR) | AHFL90081 | HR & Admin portal |
| Indira N, MIS | AHFL90091 | HR & Admin portal |
| Demo Admin, system admin | AHFL90099 | HR & Admin portal |

Portal addresses: http://localhost:5173/manage, http://localhost:5173/callcentre, http://localhost:5173/admin. Each
portal keeps its own sign-in, so you can be signed in to all three at once in one browser. For two people in the
**same** portal (for example the BM and the RBH), use a private window for the second one, or sign out first.

**Test files** (in `docs/manual-check/`): `attendance-2026-11-02.csv` and `login-register-test.csv`.

**The test entries.** In step 5 you make these entries on the phone. The rest of the guide refers to them as T1–T10.
Write each Entry ID next to it when the phone shows it.

| # | Made by | Category | Name | Mobile | Used for |
|---|---|---|---|---|---|
| T1 | AHFL90001 | Lead | Test One | 98480 70001 | the main path: call, lead card, branch answers |
| T2 | AHFL90001 | Lead | Test Two | 98480 70001 (same as T1) | "repeat entry by same SO" |
| T3 | AHFL90002 | Lead | Test Three | 98480 70001 (same as T1) | "duplicate entry" |
| T4 | AHFL90001 | DSA/Connector | Test Four | 98480 70004 | DSA/CP questions, callback (fix 13.1) |
| T5 | AHFL90001 | Contact Point (Sand / Gravel / Brick Shop) | Test Five | 98480 70005 | converted DSA/CP (fix 15.1), handling branch (fix 16.2) |
| T6 | AHFL90001 | Existing Customer | Test Six | 98480 70006 | never called, RAG NA (fix 10.1) |
| T7 | AHFL90001 | Lead | Test Seven | 98480 70007 | wrong person, corrected number |
| T8 | AHFL90001 | Lead | Test Eight | 98480 70008 | green channel (fix 25.2) |
| T9 | AHFL90001 | Prospect | Test Nine | 98480 70009 | unanswered tries, Lead logic preview |
| T10 | AHFL90001 | Lead | Clock Test | 98480 70010 | phone clock set back (fix 5.1); optional |

Three entries already in the database are used too: `AHFL90001-20261028-100000` (Validated), `AHFL90001-20261028-101700`
(Validated on 2026-10-29) and `AHFL90002-20261028-112500` (Validated, waiting for a "Take case forward" call).

---

## Step 1: Section 0, how to read the document
**What it means.** The app replaces Google Forms (phone app), the Sankalp monitor workbook (HR & Admin portal) and the
Takeoff master (call-centre portal). The numbers in section 14 are settings, not code.

**Check** (HR & Admin portal, as AHFL90099)
1. Open **Settings**. Look at "Sankalp settings (section 14)".
   - [ ] "Takeoff start date" 22 Sep 2026, "First entry date the call centre calls" 24 Sep 2026, and the other values
     of section 14 (30, 9, 2, 1, 1 day, 14, 15, 15, 14, 10, 5, ₹8 lakh, ₹15 lakh).
   - [ ] "Allow same-day calling" is Off. "A TCS ID repeated in the login register": "The latest row wins".
2. **(fix 1.1)** Change "Maximum unanswered tries (lead)" from 9 to 8 and press **Save settings**. In the Call-centre
   portal (as AHFL90061) open **My calls**.
   - [ ] The line under the title says "up to 8 unanswered".
3. **(fix 1.2)** Back in HR & Admin open **Audit log**.
   - [ ] The newest row is "settings.update", with "What changed": "max unanswered lead: 9 → 8".
4. Set it back to 9 and save. The audit log gets a second row "8 → 9".

Aham (no test): 1.3, sending the open questions to Aham.

## Step 2: Section 1, the flow from field meeting to login
**What it means.** Seven stages: entry, selection, allocation, calling, classification, lead card and lead ID, login.
Six things are kept apart: Entry ID, call outcome, status, RAG, lead ID and login.

**Check** (Call-centre portal, as AHFL90071)
1. **Entries** → search `AHFL90001-20261028-100000` → open it.
   - [ ] "The entry" shows the Entry ID; **Calls** lists the tries; the status and RAG are shown on their own;
     **Lead card** (if filled) holds the lead ID; **Outcome and flags** shows the login fields (still empty).
   - [ ] **History** lists every change with who and when.

You will walk the whole flow with T1 in steps 5–24.

## Step 3: Section 2, people and their roles
**What it means.** Each role signs in at its own portal and sees only its own data.

**Check**
1. Sign in at http://localhost:5173/manage as **AHFL90001** (a Sales Officer).
   - [ ] Refused: "This account signs in at the Sales Officer app, not here."
2. Sign in at each portal with its accounts (table above) and look at the menu:
   - [ ] BM (AHFL90011): Dashboard, Leads to answer, Open actions, Entries, Daily compliance, Field map, Team; only
     Vijayawada data.
   - [ ] Caller (AHFL90061): My calls; only the entries on Divya's list.
   - [ ] Master owner (AHFL90071): My calls, Daily run & allocation, Follow-up tracker, Green channel, Call-centre
     actions, Dashboard, Caller performance, Entries, Login register.
   - [ ] MIS (AHFL90091): only the login-register upload.
3. **(fix 3.1)** HR & Admin as the monitor **AHFL90081** → **Employee roster**.
   - [ ] Everyone on the roster, with a role filter and the joining and exit ("Left") dates.
4. **(fix 3.3)** HR & Admin as **AHFL90099** → **Organization**.
   - [ ] Each branch shows its BM; Vijayawada shows Suresh Reddy; Guntur and Nellore show "No BM: RBH answers".
   - [ ] Each cluster shows its RTM (AP Coastal: Anil Varma); each region shows its RBH (AP & TG: Prakash Rao);
     regions with no RBH show "No RBH".
   - [ ] A warning at the top: "Nobody answers the leads of N branches" (branches with no BM in a region with no RBH).

**(fix 3.2)** The RBH may correct a number where the branch has neither a BM nor an RTM. With the demo data no SO works
in such a branch, so this is covered by the automated test only.

Aham (no test): 3.4, whether the RBH should receive a sent summary.

## Step 4: Section 3, reference data
**What it means.** Roster, branches and regions, attendance, holidays, callers and the login register are kept apart
from the entries.

**Check** (HR & Admin, as AHFL90081 or AHFL90099)
1. **Uploads** → the "Employee roster (FOS Spoke)" card → **Template**. Open the file: columns Emp ID, Name,
   Designation, Region, Cluster, Branch, Spoke, Joining date, Exit date, Email, Phone, Role.
2. **Uploads** → the "Daily attendance" card → choose `docs/manual-check/attendance-2026-11-02.csv` → **Check first**.
   - [ ] The check reports 2 rows and no errors. Press **Upload**. (Checked in step 9.)
3. **(fix 4.1)** **Settings** → **Holidays** → add **2026-10-29**, name "Test holiday".
   - Open the Entries list, search `AHFL90001-20261029` and open one of them.
   - [ ] "When and where" shows **Counts on 2026-10-30** (the entry date stays 2026-10-29).
   - Delete the test holiday and reload the entry.
   - [ ] Counts on is **2026-10-29** again.

Aham (no test): 4.2, the real branch codes, the real roster, Madurai and Krishnagiri.

## Step 5: Section 4.1, entry fields
**What it means.** The SO types only category, name, mobile and description (and the Keka photo time). Emp ID, branch,
region, spoke and the time come from the roster and the phone.

**Check** (phone, signed in as AHFL90001)
1. Tap **New entry**.
   - [ ] No Emp ID, branch, region, spoke or date field.
   - [ ] Six category buttons. "CP sub-type" appears only when you pick Contact Point.
   - [ ] Submit stays off until name, a valid mobile and the description are filled.
2. Make **T1** (type the mobile as `+91 98480-70001`), then T2, T4–T9 as in the table. Use **Save & add another**
   between them. Write down each Entry ID the phone shows.
3. Sign out, sign in as **AHFL90002** and make **T3**. Sign back in as AHFL90001.
   - [ ] The **Me** tab shows Emp ID, branch, cluster and region from the roster.
4. **(fix 5.1, optional)** Phone clock set back by hand:
   - On the phone: Settings → Date & time → turn off automatic time and set the clock **2 hours back**.
   - In the app make **T10** and submit it.
   - Turn automatic time back on. Open the app and pull Home down so it syncs.
   - In HR & Admin → **Review queues** → **Check the time**:
   - [ ] T10 is listed. Its Entry ID carries the time 2 hours back.

Aham (no test): 5.2, whether the Keka photo time is required; 5.3, the full CP sub-type list.

## Step 6: Section 4.2, Entry ID
**What it means.** `<EmpID>-<YYYYMMDD>-<HHMMSS>`, India time, made at the Submit tap, never changed.

**Check**
1. In any portal open **Entries** and search T1's Entry ID.
   - [ ] The ID is exactly the one the phone showed.
2. Wrong SO (Management portal as the RTM **AHFL90021**): open `AHFL90001-20261028-103400` → **Correct SO** → pick
   Lakshmi Devi → **Move entry**.
   - [ ] The Entry ID has not changed. The SO is now Lakshmi Devi and the branch is Guntur.
   - [ ] History shows old and new SO and branch, who and when.

Aham (no test): 6.1, two entries by one SO in the same second ("-2" suffix).

## Step 7: Section 4.3, phone cleaning and validation
**What it means.** The number is cleaned (spaces, +, -, a leading 0 or 91 removed) and must be 10 digits starting
6–9.

**Check** (phone, New entry, **do not submit**; clear the box between tries)

| Type | You should see |
|---|---|
| `98480 70001` | accepted |
| `+91 98480-70001` | accepted |
| `098480 70001` | accepted |
| `919848070001` | accepted |
| `12345` | "A mobile number has 10 digits"; Submit off |
| `5848070001` | "starts with 6, 7, 8 or 9"; Submit off |
| `+91 09848070001` | refused (open question 7.1) |

- [ ] All as above.
- [ ] On the web entry page of T1, the number is shown as typed (`+91 98480-70001`) next to the cleaned `9848070001`.

Aham (no test): 7.1, whether "+91 0…" should be accepted.

## Step 8: Section 4.4, which day an entry counts on
**What it means.** A Sunday or holiday entry counts on the next working day. Saturday is a working day.

**Check**
1. **(fix 8.1)** HR & Admin → **Settings** → **Holidays** → add **today (2026-11-02)**, name "Test holiday".
   - On the phone, pull Home down to refresh.
   - [ ] Home says "Today is a Sunday or a holiday: the N entries made today count on Tue, Nov 3."
   - [ ] On the web, T1's entry page shows Counts on **2026-11-03** (fix 4.1 again).
2. Delete the holiday. Refresh Home: the note is gone and T1 counts on 2026-11-02 again.

## Step 9: Section 4.5, daily compliance
**What it means.** 10 entries per present SO per day, of which 5 genuine Lead/Prospect; shortfall, "AB" when absent.

**Check** (HR & Admin as AHFL90081 → **Daily compliance**, day 2026-11-02)
- [ ] Ravi Kumar: present, his entries of today, the shortfall to 10, and the Lead/Prospect count with its shortfall.
- [ ] Lakshmi Devi: **AB** (from the attendance file).
- **(fix 9.2)**:
  - [ ] There is a **Region** filter and a **Search Sales Officer** box.
  - [ ] The totals show "Met the target" with a %, and a "Met Lead/Prospect" card.
  - [ ] **Export** (a date range) gives a CSV with Region, Day, both targets, Lead/Prospect shortfall, met entry target
    and met Lead/Prospect target, and follows the region or branch you picked.
- [ ] As the BM (Management portal) the same page shows only Vijayawada.

After step 11, T2 (repeat) no longer counts as a genuine Lead.

Aham (no test): 9.1, an SO with no attendance row; 9.3, a frozen copy of each day.

## Step 10: Sections 5.1 and 5.2, call group and fresh entries
**What it means.** Lead and Prospect are called as leads, DSA/Connector and Contact Point as DSA/CP. Existing Customer
and Existing Applicant are never called. Entries are called from the next day unless same-day calling is on.

**Check**
1. HR & Admin as AHFL90099 → **Settings** → turn **Allow same-day calling** On → **Save settings**. (Needed so today's
   test entries can be called today. You turn it off again at the end.)
2. After the run in step 11, open T6.
   - [ ] T6 has no selection result, is on nobody's list, and its RAG is **NA**.
   - [ ] **(fix 10.1)** After the login-register upload in step 23, T6's RAG is still **NA** (it used to turn PENDING).

## Step 11: Section 5.3, decision for each fresh entry
**What it means.** The daily run checks each fresh entry in a fixed order: no valid number, repeat by same SO,
duplicate, being called, spoken within 30 days, known contact, otherwise Allocate.

**Check** (Call-centre portal as the Master owner AHFL90071 → **Daily run & allocation**)
1. Under "1 · Caller of the day per branch" set **Vijayawada → Divya S** and press **Save**. (You can also try **Copy
   yesterday**.)
2. Under "2 · Run the selection" press **Run for 2026-11-02**.
3. Open the entries (Entries list, or search) and look at the selection result of each:
   - [ ] T1, T4, T5, T7, T8, T9 (and T10): **Allocate**.
   - [ ] T2: **Not called – repeat entry by same SO** (same SO, same number, within 30 days).
   - [ ] T3: **Not called – duplicate entry** (T1 was earlier).
   - [ ] The entries of 29 Oct: three numbers allocated; of the three entries with 9123400001, the first is allocated
     and the later ones are "repeat entry by same SO".
4. Press **Run** again.
   - [ ] Nothing new is decided: a "Not called" result is final.

Aham (no test): 11.1, "being called" also covers an entry waiting for its first call; 11.2, an offline entry that
arrives after another SO's entry for the same number.

## Step 12: Section 6, allocation to callers
**What it means.** New entries go to the branch's caller of the day; retries go back to the first caller; PRIORITY
entries come first.

**Check**
1. Call-centre portal as **AHFL90061** (Divya) → **My calls**.
   - [ ] The test entries and the follow-up `AHFL90002-20261028-112500` (Take case forward) are listed.
   - [ ] **(fix 12.2)** The entries of 29 Oct show **First try overdue** (target: first try within 1 day).
2. As the Master owner, **Daily run & allocation**:
   - [ ] **(fix 12.2)** The "First try overdue" card, and the Callers table with an overdue column.
   - [ ] **(fix 12.1)** In the Callers table, use **Move today's list to** to move Divya's list to Farhan Ali.
     Farhan's My calls (pick him in the Caller box) now holds it. Move it back to Divya.
3. **(fix 12.3)** As the Master owner open `AHFL90001-20261028-101700` → **Follow-up tracker** → tick **Immediate
   call-back** → **Save**. Go to Daily run and press **Run** again.
   - [ ] In Divya's My calls this entry is **first**, marked PRIORITY, with the reason "Master owner: immediate call-back".
   - Leave it there: step 22 uses it.

Aham (no test): 12.4, which caller gets yesterday's unreturned new entries.

## Step 13: Section 7.1, attempts
**What it means.** Each try has a time slot and an outcome. Lead: 2 tries a day, up to 9 unanswered. DSA/CP: one
calling day.

**Check** (Call-centre as Divya AHFL90061 → My calls → open the entry)
1. **T9**: pick a slot and **RNR** → **Save try**.
   - [ ] Status **In retry**, RAG **RNR**, "Tries so far" shows 1 unanswered.
   - Make a second RNR try (another slot).
   - [ ] T9 leaves today's list (2 tries a day).
   - [ ] **Save try** stays off without a slot or an outcome.
2. **T4** (DSA/CP): first do the step 18 checks on it (Connected, **without saving**): once its callback is saved, T4
   leaves today's list. Then pick **Callback requested**.
   - [ ] **(fix 14.1)** A **Sunday** date (2026-11-08) is refused at once ("A Sunday is not a working day") and Save
     stays off.
   - Pick **2026-11-03** → **Save try**.
   - [ ] Status In retry; the call-centre action is "Callback" on 2026-11-03.
   - **(fix 13.1)** Tomorrow the try can be recorded (see Next-day checks).

Aham (no test): 13.2, the third try in one day.

## Step 14: Section 7.2, Lead questions once connected
**What it means.** On a Connected call the caller asks 13 questions. The status comes from the answers, not from the
caller.

**Check** (Divya → **T1**)
1. Pick a slot and **Connected**.
   - [ ] The 13 questions appear; they are not there for other outcomes.
2. Answer: Name check "Same person", Visit "Yes", Relationship "No", Loan need "Home purchase", Documents "Yes", Next
   step "SO / branch visit".
   - [ ] **(fix 14.1)** A Sunday **Next date** is refused at once. Pick **2026-11-05**.
   - [ ] The line "This call will be classified as **Validated**" shows before saving.
3. **Save try**.
   - [ ] T1: status **Validated**, RAG **GREEN**, SO action **Visit customer** on 2026-11-05.

Aham (no test): 14.2, whether Next date is required for "SO / branch visit".

## Step 15: Section 7.3, DSA/CP questions once connected
**What it means.** A DSA/CP contact is asked for a RAG and "Needs a home loan himself?". "Yes" switches to the Lead
questions.

**Check** (Divya → **T5**)
1. **Connected**.
   - [ ] Two questions: "RAG given by caller" and "Needs a home loan himself?".
2. Pick **Yes**.
   - [ ] The Lead questions open.
   - Answer them as for T1 (Loan need "Home purchase", Next step "SO / branch visit", next date 2026-11-05).
   - [ ] Preview: **Validated – converted from DSA/CP**. **Save try**.
3. **(fix 15.1)** Open T5's call screen again.
   - [ ] "Converted from DSA/CP: called as a lead, 2 tries a day, up to 9 unanswered", and the Lead questions show at
     once.

Aham (no test): 15.2, what each DSA/CP RAG choice means.

## Step 16: Section 7.4, lead card
**What it means.** After a validated call the caller fills the lead card and types the TCS lead ID. The lead ID never
closes the lead.

**Check** (Divya → **T1** → Lead card)
1. **(fix 16.1)** Loan requirement: type `40L`.
   - [ ] "Digits only, e.g. 4500000" and **Save lead card** off.
   - Type `40,00,000`.
   - [ ] It reads back "₹40,00,000 (40 lakh)".
2. CIBIL `250` or a 5-digit pincode.
   - [ ] Refused. Correct them, or leave them blank.
3. Type a TCS lead ID `LEAD-T1` with the loan requirement empty.
   - [ ] Refused; the loan requirement is needed once a lead ID is typed.
   - Fill it and **Save lead card**.
   - [ ] T1 stays Validated, with no login.
4. **(fix 16.3)** Change the loan requirement to `45,00,000` and save.
   - [ ] T1's entry page → History: a lead-card line with "changes: loan requirement 4000000 → 4500000".
5. **T8** lead card: first record a Connected call on T8 (Loan need "Self-construction", Next step "SO / branch
   visit", next date 2026-11-05). Then fill the lead card with loan requirement `5,00,000` and save. (Used in step 24.)
6. **(fix 16.2)** **T5** lead card: Handling branch **Guntur**, loan requirement `25,00,000`, save.
   - [ ] Management portal as the BM AHFL90011 → **Leads to answer**: T5 is **not** there.
   - [ ] As the RBH **AHFL90031** (Guntur has no BM): T5 is listed, "Handled by Guntur".
   - [ ] T5 still belongs to Ravi Kumar, Vijayawada, for credit and compliance.

Aham (no test): 16.4, fixed lists for some fields; age and date of birth.

## Step 17: Section 8.1, Lead logic
**What it means.** Eight rules in order; the first that matches gives the status.

**Check** (Divya → **T7**, still uncalled; pick **Connected** and change the answers, **without saving**; watch the
preview line. T7 gets its real try in step 19.)

| Answers | Preview |
|---|---|
| Loan need left blank | Amber – answers missing |
| Loan need "Not looking for a loan" | Red |
| Loan need "LAP" or "BT + LAP" | Not counted – LAP |
| Documents "File already logged with Aham" (any loan need) | Already in process |
| Relationship "Yes – the same officer" | Amber – knows SO |
| Name check "Different person" | Validated – different person |
| Visit "No" | Validated – visit not confirmed |
| Everything else filled normally | Validated |

- [ ] All as above.
- [ ] Order: "LAP" + "File already logged" gives LAP; "File already logged" + "same officer" gives Already in process.
- [ ] Reload the page: nothing was saved.

Aham (no test): 17.1, what should follow "Amber – answers missing" and "Amber – knows SO".

## Step 18: Section 8.2, DSA/CP connected
**Check** (done on **T4** in step 13, before its callback was saved: **Connected**, without saving)
- [ ] Needs a home loan "No" and caller RAG Green / NA / Amber / Red: "DSA/CP – Green", "DSA/CP – NA", "DSA/CP –
  Amber", "DSA/CP – Red".
- [ ] RAG left blank: **DSA/CP – no RAG** (not NA).
- [ ] "Yes" with Loan need "Not looking for a loan": **Red** (not converted).
- [ ] T5 (step 15) shows the converted case: "Yes" with a validated answer gives "Validated – converted from DSA/CP".

## Step 19: Section 8.3, not connected
**Check** (Divya → **T7**)
1. **Wrong person** → **Save try**.
   - [ ] Status **Amber – wrong person**, RAG **AMBER**.
   - [ ] SO action **Correct customer number**, open 15 days from the entry date.
   - [ ] On the phone (My entries): T7 shows the action; Home lists the number to correct.
2. Other outcomes (record them only on entries you don't need any more):
   - Invalid number gives "Discarded – invalid number".
   - Refused to talk gives "Rejected – refused to talk".
   - On DSA/CP, an unanswered try gives "Closed – no answer" (see `AHFL90001-20261028-105100`).

Aham (important, no test): 19.1, whether a later call on a validated lead may change its status.

## Step 20: Section 8.4, old-process verdicts ([Legacy])
- [ ] On the call screen the outcomes are only the nine of section 7.1. None of the old verdicts ("Green – send to
  branch", "Red – not genuine" …) can be picked anywhere.

Aham (no test): 20.1, importing the Excel history.

## Step 21: Section 9, RAG
**What it means.** RAG is worked out from the status and the actions; the Master owner can override it.

**Check**
1. Entries list → **RAG** filter: GREEN, AMBER, RED, RNR, PENDING, NA.
   - [ ] T1 GREEN, T7 AMBER, T9 RNR, T6 NA, T2/T3 NA.
2. Override: Master owner → T9 → **Follow-up tracker** → RAG override **Amber** → Save.
   - [ ] T9 shows AMBER, marked overridden.
   - Clear the override: T9 is back to RNR.
3. **(fix 21.1)** Lost lead: Divya → `AHFL90002-20261028-112500` (Validated, on today's list as "Take case forward").
   - Record **Connected** with Loan need **Not looking for a loan** → Save.
   - [ ] Status **Red**, but RAG **NA** (a lost lead, not Red).

Aham (no test): 21.2, the order of the RAG rows.

## Step 22: Section 10, incentive flags
**What it means.** Customer validated, First validation for this number, Validated on, and Sankalp success.

**Check**
1. **(fix 22.1)** Divya → `AHFL90001-20261028-101700` (PRIORITY from step 12). Record **Connected** with answers that
   give Validated → Save.
   - [ ] The entry page **Outcome and flags**: **Validated on 2026-10-29** (the first validating call), not today.
   - [ ] The PRIORITY mark is gone after the try.
2. T1 → **Outcome and flags**.
   - [ ] Customer validated **Yes**, First validation for this number **Yes**, Validated on today.
   - [ ] T2 and T3 (same number): not "First validation".
3. HR & Admin → **Takeoff export** → **Download CSV** for October–November.
   - [ ] Columns: Entry ID, credited SO, branch, region, dates, category, phone, selection, status, RAG, repeat entry,
     customer validated, first validation, validated on, lead outcome, TCS ID, login date, Sankalp success.

## Step 23: Section 11, login register, lead outcome, Sankalp success
**What it means.** The MIS register confirms logins. Every number in the contact cell is matched.

**Check**
1. HR & Admin as MIS **AHFL90091**: the menu has only **Uploads**, with only the "Login register (MIS)" card. Choose
   `docs/manual-check/login-register-test.csv` → **Check first**, then **Upload**.
2. `AHFL90001-20261028-100000` (9848012345, the **second** number in its cell):
   - [ ] Lead outcome **Logged in**, TCS ID **TCS900001**, login date **2026-10-31** (TCS900001 is in the file twice;
     the latest row wins).
   - [ ] **Counts as Sankalp success: Yes**; the SO and branch actions are closed.
3. `AHFL90001-20261028-101700` (login date 2026-10-27, before its entry date of 28 Oct):
   - [ ] Lead outcome **Login on/before entry date (not counted)**; not a success.
4. T6 and `AHFL90001-20261028-114200` (existing customers):
   - [ ] They get TCS900003 but stay **NA** (fix 10.1) and are not "Logged in".
5. Manual route (Master owner): a TCS ID typed on the tracker counts as a login "manual" (step 25).

Aham (important, no test): 23.1, which entries compete for the success; 23.2, "latest row"; 23.3, LAP product names.

## Step 24: Section 12, actions and branch answers
**What it means.** The branch answers each lead with one code and one date. A date more than 14 days away hands the
lead to the call centre. A green-channel R2 or R3 waits for head office.

**Check** (Management portal as the BM **AHFL90011** → **Leads to answer**)
1. T1 → **Answer** → code **C3** (login pending: date of login), Login date **2026-11-10** → **Save answer**.
   - [ ] The date is required, and a past date is refused.
   - [ ] T1 stays with the branch; its action moves to 2026-11-10.
2. T1 → Answer again → code **E2** (out of station), Follow-up date **2026-11-25** (more than 14 days away).
   - [ ] **(fix 1.1)** The dialog says "within 14 days" from the setting.
   - [ ] T1 goes to the call centre: Master owner → **Call-centre actions** shows T1 "Follow-up" on 2026-11-25.
3. T8 → Answer → **R2** (eligibility or income).
   - [ ] T8 is **not** rejected. Master owner → **Green channel** lists it (Self-construction, ₹5,00,000, within ₹8
     lakh).
   - Leave it: step 25 returns it.
4. **(fix 24.1 / 27.1)** **Open actions**.
   - [ ] Views **Open** / **Expired unworked**, kind filter (Lead actions, Correct number, DSA/CP follow-up), a pager
     with the total.
   - [ ] T7 is under Correct number.
   - Expired entries appear only after a window runs out (Next-day checks).
5. **(fix 24.2)** The "Missed dates" note on Leads to answer counts only branch dates that have passed. The 25 Nov date
   handed to the call centre will never count. You can only see this once a date has passed.

Aham (no test): 24.3, what follows an expired "Correct customer number".

## Step 25: Section 13, corrections
**Check**
1. Correct number (BM **AHFL90011** → Open actions → Correct number → **T7** → **Correct number**): type `98480 70017`
   → **Save number**.
   - [ ] History: old → new number, who, when; a new calling cycle with a fresh 9 tries.
   - [ ] T7 goes back on Divya's list at the next run **tomorrow**, because it was already called today.
2. **(fix 25.1)** Master owner → T1 → **Follow-up tracker**:
   - [ ] Outcome **Logged in** with no TCS ID: "Type the TCS ID…" and Save stays off.
   - [ ] Outcome **Rejected** with no reject reason: Save stays off.
   - Cancel.
3. **(fix 25.2)** Master owner → T8 → **Follow-up tracker** → Outcome **Return to branch – green channel** → Save.
   - [ ] **Green channel** no longer lists T8, and T8 is back with the branch, not rejected.
   - [ ] The same outcome on an entry with nothing waiting (for example T9) is refused: "No green-channel R2/R3
     rejection is waiting for this lead".
4. Later date wins: a tracker follow-up date later than the branch's answer date takes over the lead (owner Call
   centre). An earlier one does not.
5. Wrong SO: done in step 6.

Aham (no test): 25.3, the same-day tie, numbers after 15 days, no selection checks after a correction.

## Step 26: Section 14, settings
**Check** (HR & Admin as AHFL90099 → **Settings**)
1. **(fix 26.2)** Change "Daily entry target per SO" from 10 to **12** → Save.
   - [ ] Daily compliance for **today**: target 12, shortfalls bigger.
   - [ ] Daily compliance for **2026-10-29**: still target 10. A setting applies from the day it is saved.
2. Set it back to 10 and save.
   - [ ] **Audit log** shows both changes with old → new values.

Aham (no test): 26.1, the two 15-day settings; 26.3, turnaround in calendar or working days.

## Step 27: Section 15, the acceptance checklist
| # | Check | Where you saw it |
|---|---|---|
| 1 | The SO cannot type the Emp ID | step 5 |
| 2 | An invalid number cannot be submitted | step 7 |
| 3 | The SO cannot choose another branch | step 5 |
| 4 | One form = one person | step 5 |
| 5 | "5 lakh" / "40L" cannot go into an amount (fix 16.1) | step 16 |
| 6 | A number in the 2nd or 3rd place of the contact cell is found | step 23 |
| 7 | Lists show everything (fix 27.1) | below |

- [ ] Open actions, Call-centre actions, Follow-up tracker and Review queues have pagers with a total.
- The map's "showing the newest 3,000" notice and the phone's "Load older entries" appear only above 3,000 entries
  (map) or 200 entries (phone). The demo data is too small, so these two are covered by the automated tests.

## Step 28: Annex A, branches by region
**Check** (HR & Admin as AHFL90099 → **Organization**)
- [ ] 7 regions (AP & TG, Chennai 1, Chennai 2, Karnataka, RoTN C, RoTN T, RoTN U) and the 35 branches of Annex A.
- [ ] Madurai under RoTN U, Krishnagiri under RoTN C, with the open question shown.
- [ ] **(fix 28.1)** Add a **Branch** named `Vijayawada` (any region and code): refused, the name exists. Cancel.

Aham (no test): 28.2, the full region names, real branch codes, Madurai and Krishnagiri.

## Step 29: Annex B, status list
**Check** (any Entries list → the **Status** filter)
- [ ] The filter holds 26 values, each with the Annex B text (en dash "–"): the 6 "Not called…" results, the 5
  calling statuses (In retry, Discarded ×2, Closed – no answer, Rejected – refused to talk), the 10 Lead logic statuses
  and the 5 DSA/CP values.
- [ ] The 3 lead outcomes (Logged in, Rejected, Login on/before entry date) are a separate field, shown under the
  status in the list: for example "Logged in" on `AHFL90001-20261028-100000` after step 23.
- [ ] Nobody can type a status anywhere: the caller picks outcomes and answers only.

---

## Next-day checks (2026-11-03 or later)
On the next day, Master owner → **Daily run & allocation** → set Vijayawada's caller → **Run**.
- [ ] **(fix 13.1)** T4 (DSA/CP callback for 3 Nov) is on Divya's list and a try **can be saved** (it used to be
  refused).
- [ ] T7 (corrected number) is on Divya's list as a retry, with 0 of 9 unanswered.
- [ ] **(fix 15.1)** T5 (converted): any later follow-up call is allowed, and an unanswered try gives **In retry**,
  not "Closed – no answer".
- [ ] Branch code **3** on a lead called the day before → at the next run it is first on the list, PRIORITY,
  "Branch: customer not answering".
- [ ] **(fix 24.1)** Once an action's window runs out (for example "Correct customer number" 15 days after the entry
  date), the entry shows "Expired: … · date" and is listed under Open actions → **Expired unworked**.

## Clean-up when you finish
- Settings: **Allow same-day calling** back to **Off**. "Maximum unanswered" 9 and "Daily entry target" 10 (if
  changed).
- Settings → Holidays: no "Test holiday" left.
- Phone: automatic date and time on.
- The test entries and the uploaded register rows stay in the dev database. They do no harm. A fresh database is
  `docker compose down -v` followed by the seed, which also removes the earlier demo data.
