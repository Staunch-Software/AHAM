# Feature review against the business-logic document

A step-by-step check of *Sankalp app: business logic, from SO entry to lead ID* (v1, 28 Oct 2026) against what is
built. Nothing is changed during the review; each step lists what is **missing** or **different** (built, but not
quite as described). Items marked *Aham* need an answer from Aham, not code.

## Fixes made (2026-11-01)
All 4 bugs, 8 missing pieces and 16 differences are done; the 28 "Aham" items stay open (they need Aham's answer, not
code). Where an item needed a business choice, the app takes the reading the review suggested and it is listed in
`docs/sankalp-rules.md` ("Assumptions"), so Aham can confirm or change it. Each fix has a test: backend
`tests/test_review_fixes.py` (21), web `tests/review.test.tsx` (9), mobile `__tests__/rules.test.ts` (count date).
Database change: migration `7b3e9c41d2a8` (handling branch and expired action on entries, audit details, settings
history, unique branch and region names).

| # | What changed |
|---|---|
| 1.1 | Screen texts read the settings (`/sankalp/meta` "limits", `/me/summary`): call screen, My calls, branch answer, green channel, Takeoff, Open actions, the app's "numbers to correct" |
| 1.2 | The audit log keeps old and new values (`audit_logs.details`); the Audit page shows "setting: old → new" |
| 3.1 | HR & Admin → Data → Employee roster (everyone on the roster, role filter, joining and exit dates) |
| 3.2 | The RBH can correct a number where the branch has no BM and no RTM; refused elsewhere ("bm_or_rtm_corrects") |
| 3.3 | Organization shows each branch's BM, cluster's RTM and region's RBH, flags "No BM" / "No RBH", and warns when a branch's leads have nobody to answer them (`/org/managers`) |
| 4.1 | Adding or removing a holiday works out again the count date of entries made that day (and the Sundays before it) |
| 5.1 | The app sends its own clock reading at the last server answer; an entry made before that (clock set back) is flagged "check the time" |
| 8.1 | The app gets the holidays with its summary, counts entries still on the phone by count date too, and says on a Sunday or holiday which day today's entries count on |
| 9.2 | Compliance: region filter, search for an SO, "% met" and "met Lead/Prospect" totals; the export has Region, Day, both targets, Lead/Prospect shortfall, met entry target, met Lead/Prospect target (and follows the region / branch chosen) |
| 10.1 | (bug) Existing Customer / Applicant stay NA whatever recalculates them |
| 12.1 | Daily run: "Move today's list to" another caller (retries and PRIORITY calls included; first caller kept) |
| 12.2 | "First try overdue" on each list row, per caller and in total on the Daily run page |
| 12.3 | The PRIORITY reason is shown on each row of My calls |
| 13.1 | (bug) A DSA/CP callback date is one more calling day for that contact |
| 14.1 | A Sunday next date or callback date is refused at once on the call screen (Save stays off) |
| 15.1 | (bug) A converted DSA/CP is called with the Lead rules and questions from then on (follow-ups allowed; unanswered → In retry) |
| 16.1 | (bug) Lead card number boxes refuse anything but digits ("40L" is refused) and read the amount back as "₹40,00,000 (40 lakh)" |
| 16.2 | The handling branch works the lead: its BM (or RBH where it has no BM) sees and answers it, and its missed dates count there; credit stays with the SO's branch |
| 16.3 | Every lead card change is in the entry's history (field: old → new) |
| 21.1 | A lead that an earlier call validated and a later call finds "Not looking for a loan" (lost lead) keeps status Red but its RAG is NA |
| 22.1 | "Validated on" is the date of the first validating call |
| 24.1 | An action whose window runs out is kept on the entry as "expired" (history event too) and listed under Open actions → "Expired unworked" |
| 24.2 | Missed dates leave out a date the 14-day rule gave to the call centre and leads rejected since |
| 25.1 | Tracker: "Logged in" needs the TCS ID, "Rejected" needs the reason (server and form) |
| 25.2 | Tracker: "Return to branch – green channel" returns the waiting R2/R3 like the Green channel page; refused when none is waiting |
| 26.2 | Settings apply from the day they are saved; past days' compliance uses the settings of that day (`settings_history`) |
| 27.1 | Open actions, call-centre actions, tracker list and review queues come in pages with a total; the map says when it shows only the newest 3,000 of a period; the app's "My entries" loads older entries on request |
| 28.1 | Branch names and region names are unique per company (database and a clear message) |

## Result (review finished 2026-11-01)
Every section of the document (0–15 and Annexes A and B) was checked against the code, 29 steps in all. Every rule
the document says to build is in the app; nothing in it is missing outright. What the review found:

| Kind | Count | Meaning | Status |
|---|---|---|---|
| Bug | 4 | Built, but wrong in a case the document covers: 10.1, 13.1, 15.1, 16.1 | Fixed |
| Missing | 8 | A piece of a feature the document implies: 3.1, 3.2, 9.2, 12.1, 12.2, 12.3, 16.2, 27.1 | Done |
| Different | 16 | Built, but not quite as described (mostly small) | Done |
| Aham | 28 | Needs Aham's answer, not code; two are important: 19.1 and 23.1 | Open |

Suggested order: fix the 4 bugs first (each is small and testable on its own), then 16.2, 27.1, 3.1, 3.2 and the
12.x screen gaps; send the Aham list (all "Aham" rows below, with the assumptions in `docs/sankalp-rules.md`) in
parallel, starting with 19.1 and 23.1 because they change the incentive flags.

## Summary of open items
| # | Step | Kind | Item | Status |
|---|---|---|---|---|
| 1.1 | 1 | Different | Screen texts state the windows and limits as fixed numbers instead of reading the settings | Done 2026-11-01 |
| 1.2 | 1 | Different | The audit log records that the settings changed, not which value changed from what to what | Done 2026-11-01 |
| 1.3 | 1 | Aham | The [Aham to decide] questions and our assumptions are written down but not yet sent to Aham | Open |
| 3.1 | 3 | Missing | The Sankalp monitor (HR) cannot see the employee roster: it uploads it but has no roster page | Done 2026-11-01 |
| 3.2 | 3 | Missing | A branch with no BM and no RTM: nobody can correct a customer number | Done 2026-11-01 |
| 3.3 | 3 | Different | Which branches have no BM (and which region has which RBH) is worked out by the system but not shown on any screen | Done 2026-11-01 |
| 3.4 | 3 | Aham | RBH "receives regional summaries": shown on the dashboard, nothing is sent | Open |
| 4.1 | 4 | Different | A holiday added after the day (or removed) does not move the count date of entries already made | Done 2026-11-01 |
| 4.2 | 4 | Aham | Real data before go-live: branch codes (placeholders today), the real roster, Madurai and Krishnagiri | Open |
| 5.1 | 5 | Different | Submission time is the phone's clock (for offline); a clock set back to backdate an entry is not detected | Done 2026-11-01 |
| 5.2 | 5 | Aham | Keka photo time is optional and typed on every entry; required or not? | Open |
| 5.3 | 5 | Aham | The full CP sub-type list from the current forms (3 starter options today) | Open |
| 6.1 | 6 | Aham | Two entries by one SO in the same second: the second gets "-2", which is our assumption, not the document's | Open |
| 7.1 | 7 | Aham | "+91 0…" (country code and a leading 0, 13 digits) is refused as invalid; confirm that is wanted | Open |
| 8.1 | 8 | Different | The SO's "Today" count on the phone mixes entry date (unsent) and count date (sent); on a holiday it drops with no reason shown | Done 2026-11-01 |
| 9.1 | 9 | Aham | No attendance row for the day ("not marked"): counted like present today; the document only defines codes | Open |
| 9.2 | 9 | Missing | Compliance export lacks the Lead/Prospect shortfall and "met" columns; page has no region filter or SO search | Done 2026-11-01 |
| 9.3 | 9 | Aham | "Publishes daily compliance": the report is live (late offline entries still change past days); is a frozen daily copy wanted? | Open |
| 10.1 | 10 | Bug | Existing Customer / Existing Applicant entries start as RAG "NA" but turn "PENDING" when recalculated (e.g. after a login register upload) | Done 2026-11-01 |
| 11.1 | 11 | Aham | Check 4 "number already being called" also counts an entry allocated and waiting for its first call, not only "In retry" | Open |
| 11.2 | 11 | Aham | "Earliest wins" works within one daily run: an entry made offline earlier but sent after another SO's entry was already selected loses | Open |
| 12.1 | 12 | Missing | No screen to move an absent caller's list (their retries and priority calls) to another caller for the day | Done 2026-11-01 |
| 12.2 | 12 | Missing | Turnaround: no "overdue" marker on the lists; only a percentage on Caller performance | Done 2026-11-01 |
| 12.3 | 12 | Missing | The PRIORITY reason is stored but not shown on each row of the caller's list | Done 2026-11-01 |
| 12.4 | 12 | Aham | Unreturned entries never called go to today's branch caller (may differ from yesterday's); our assumption | Open |
| 13.1 | 13 | Bug | "Callback requested" on a DSA/CP entry leaves it stuck In retry: every try on the callback day is refused ("one day only") | Done 2026-11-01 |
| 13.2 | 13 | Aham | Lead: 2 tries a day planned, a 3rd can be recorded; "morning and afternoon" not enforced. Confirm the meaning of the 3rd slot | Open |
| 14.1 | 14 | Different | Next date / callback date pickers still offer Sundays; the Sunday is refused only on Save | Done 2026-11-01 |
| 14.2 | 14 | Aham | Next date is optional even when Next step = "SO / branch visit" (the visit action then has no date) | Open |
| 15.1 | 15 | Bug | A DSA/CP entry converted to a lead keeps the DSA/CP call limits: call-centre follow-up calls on a later day are refused | Done 2026-11-01 |
| 15.2 | 15 | Aham | What Green / NA / Amber / Red mean for a DSA/CP contact (criteria for callers) | Open |
| 16.1 | 16 | Bug | Lead card amounts drop letters instead of refusing them: "40L" is saved as ₹40, "7 lacks" as ₹7 | Done 2026-11-01 |
| 16.2 | 16 | Missing | Handling branch is stored but not used: the lead still goes to the SO's branch | Done 2026-11-01 |
| 16.3 | 16 | Different | Lead card changes (other than the Lead ID) are not in the entry's history, e.g. who changed the loan requirement | Done 2026-11-01 |
| 16.4 | 16 | Aham | Age vs date of birth; options for property owner, approved property, property type, purpose of loan, vehicle type | Open |
| 17.1 | 17 | Aham | What happens after "Amber – answers missing" and "Amber – knows SO": no action for anyone today | Open |
| 19.1 | 19 | Aham (important) | Every call sets the status: an unanswered follow-up call on a Validated lead turns it back to "In retry", which clears "Customer validated" and the branch's lead action until the customer is reached again | Open |
| 20.1 | 20 | Aham | Import of the history since 22 Sep (and, if so, the mapping of the six old verdicts): not built | Open |
| 21.1 | 21 | Different | A lost lead found on a later call ("Not looking for a loan" now) becomes Red, but section 9 says a lost lead is NA | Done 2026-11-01 |
| 21.2 | 21 | Aham | "Logged in or rejected → NA" is applied before every other RAG row (the table gives no order); confirm | Open |
| 22.1 | 22 | Different | "Validated on" is the date of the latest validating call (moves if a later call validates again); for a login-only validation it is the login date | Done 2026-11-01 |
| 23.1 | 23 | Aham (important) | "Earliest entry for the TCS ID" counts every entry with that number, so an earlier Existing Customer / Applicant or DSA/CP entry blocks a later Lead's Sankalp success | Open |
| 23.2 | 23 | Aham | "Latest register row" read as the row uploaded last (later file, lower row), not the latest login date; one phone with two TCS IDs: the first login after the entry date is used | Open |
| 23.3 | 23 | Aham | A LAP login is recognised by "LAP" in the register's Product text: need the exact product names | Open |
| 24.1 | 24 | Different | Actions are worked out on the entry, not kept as records: no "done" or "expired" state, no list of expired actions | Done 2026-11-01 |
| 24.2 | 24 | Different | Missed dates also count a date the 14-day rule gave to the call centre, and leads rejected later from the tracker | Done 2026-11-01 |
| 24.3 | 24 | Aham | After the 15-day "Correct customer number" window the entry simply stays Amber with no action; is anything meant to happen? | Open |
| 25.1 | 25 | Different | Tracker outcome "Logged in" does nothing without a TCS ID, and the form lets it be saved without one ("Rejected" without a reason too) | Done 2026-11-01 |
| 25.2 | 25 | Different | Tracker outcome "Return to branch – green channel" has no effect of its own | Done 2026-11-01 |
| 25.3 | 25 | Aham | Tracker and branch answer on the same date: the tracker wins (our choice); a number corrected after 15 days is refused; a corrected number skips the selection checks | Open |
| 26.1 | 26 | Aham | The two 15-day settings overlap ("correct number" window shows the action, "SO Amber" window allows the correction); what does the SO Amber window cover? | Open |
| 26.2 | 26 | Different | Settings have no effective date: a changed target or window also changes past days (e.g. past compliance shortfalls) | Done 2026-11-01 |
| 26.3 | 26 | Aham | Turnaround "1 day" is counted in calendar days (a Saturday entry first called on Monday is late); calendar or working days? | Open |
| 27.1 | 27 | Missing | Silent row caps (Excel problem 7): field map 3,000; Open actions 1,000; call-centre actions, tracker list, review queues 500; SO's "My entries" 200 | Done 2026-11-01 |
| 28.1 | 28 | Different | Branch codes must be unique, but two branches could be given the same name (the roster upload matches branches by name or code) | Done 2026-11-01 |
| 28.2 | 28 | Aham | Full names of RoTN C / T / U, the real branch codes, Madurai and Krishnagiri (see 4.2) | Open |

## Step 1: Section 0, how to read the document
**Done**
- The three systems are replaced in one application:
  - Google Forms → the AHAM Sankalp mobile app.
  - Sankalp monitor (Excel) → the HR & Admin portal: identity from the roster, uploads, daily compliance, queues.
  - Takeoff master (Excel) → the call-centre portal: daily run, allocation, calling, classification, lead card,
    tracker.
- Scope: up to the lead ID, the hand-off actions, and login confirmation from the MIS login register. The incentive
  money is not calculated; the app produces the flags and the Takeoff export.
- Rule labels:
  - Unmarked rules are built.
  - [Legacy] rules are not built: UNRES IDs, name/number swap, old-process verdicts.
  - [Aham to decide] points are not decided in code. Each is a setting that keeps today's behaviour (same-day calling
    off; duplicate TCS ID: latest row wins, as the document proposes), or data Aham can change (Madurai and
    Krishnagiri are placed as Annex A lists them, and the Organization page shows the open question). The payout
    rule and the old verdicts are not built.
- Dates and settings: Takeoff start (22 Sep 2026) and every value in section 14 are stored per company in the database
  (`company_settings`), with the document's values as defaults. Only the system admin can change them (HR & Admin →
  Settings), and the rules read the stored values, so no code change is needed.

**Different**
- 1.1 Screen texts repeat the numbers instead of reading the settings. The rules follow the settings, so if Aham
  changes a window the rule changes but these texts would still show the old number:
  - Mobile home: "within 15 days of the entry" (`mobile/src/app/(app)/home.tsx`).
  - Branch answer dialog: "A date within 14 days" (`admin-web/src/features/branch/AnswerDialog.tsx`).
  - Call screen and My calls: "2 tries a day, up to 9 unanswered" (`CallScreen.tsx`, `MyCalls.tsx`).
  - Green channel: "up to ₹8 lakh … ₹15 lakh" (`GreenChannel.tsx`).
  - Takeoff export description: "within 30 days" (`Takeoff.tsx`).
  - Two status texts carry a number because Annex B spells them that way: "Not called – spoken within 30 days" and
    "Discarded – 9 unanswered". Leave as is unless Aham wants them to follow the setting.
- 1.2 Changing settings is audited ("settings.update", who and when), but the log does not keep the old and new
  values.

**Aham**
- 1.3 The open points and the assumptions are listed in `docs/sankalp-rules.md` (sections "Assumptions" and
  "[Aham to decide]") and the history question in the README. They still need to be sent to Aham and answered.

## Step 2: Section 1, the flow from field meeting to login
**Done**, every stage:
1. **Entry:** the SO records category, name, phone and description in the app; the Entry ID is made at Submit. A new
   entry is only "Pending": nothing says it was called or applied.
2. **Selection:** the daily run marks each fresh entry "Allocate" or one of the six "Not called" reasons.
3. **Allocation:** new entries go to the branch's caller of the day; retries go back to the first caller.
4. **Calling:** each try records a time slot and one of the nine outcomes; retries and limits differ for Lead and
   DSA/CP.
5. **Classification:** the caller records only the slot, outcome and answers (the API has no status field); the status
   and RAG are worked out by the rule functions in `engine.py`, which have a test per rule table. The call screen shows
   the status the answers will produce before saving.
6. **Lead card and lead ID:** the caller fills the card and types the TCS lead ID. The lead ID is stored on the lead
   card only; no rule reads it, so it never validates, closes or counts an entry. The flow test checks that the lead
   outcome stays empty after a lead ID and that the branch still gets the lead.
7. **Login confirmation:** only the MIS login register (or a TCS ID the master owner enters by hand, which section
   11.1 allows) sets "Logged in". Case A (lead ID, no login in the register) stays open; case B is marked Logged in.
- After the lead ID: the SO/branch and call-centre actions are worked out after every event, and a login or rejection
  closes them (section 12).
- The six concepts are separate fields: Entry ID (`entry_code`), call outcome (one row per try), status, RAG, lead ID
  (lead card), and login (`tcs_id`, `login_date`, `lead_outcome` from the register). The entry page shows each one
  separately, with the history of every change.

**Missing / different:** none.

## Step 3: Section 2, people and their roles
Permissions are checked by the backend on every request (`security/rbac.py`, `require_perm`, data scope per role)
and the web menus hide what a role may not open; a test checks every role against the permission matrix and scope.

**Done**
- **Sales Officer (RO / RM / ABM as designation):** mobile app only; creates entries; sees own entries with status,
  RAG and actions, and the "Numbers to correct" list. Emp ID, branch, region and spoke come from the roster.
- **RTM / BM corrections:** BM and Cluster Manager (RTM) correct numbers (within 15 days) from "Open actions" and the
  entry page; the RTM corrects the SO, or the BM where the branch has no cluster. Each correction is kept in the
  entry's history with who and when.
- **RBH (Region Manager):** answers the leads of branches in its region that have no BM (worked out from the users:
  a branch with no active BM); dashboard, compliance and missed dates for its region.
- **Sankalp monitor (HR):** roster and attendance uploads, wrong-SO correction, category-wrong and check-the-time
  queues, daily compliance with export, entries filtered by RAG and status, Takeoff export, audit log.
- **Caller:** call-centre portal with only the entries allocated to it: contact, past tries, time slot, outcome, the
  questions that depend on the group and answers, the lead card and the TCS lead ID.
- **Master owner:** daily run and caller per branch (with "copy yesterday"), callers' workload and performance,
  priority and immediate call-back, the follow-up tracker (only this role can edit it), login register upload,
  manual TCS ID, RAG override, green-channel review.
- **Branch / BM:** "Leads to answer" for its branch with one code and one date, open actions, missed dates. Code 1
  "Logged in" does not close the lead; only the register does.
- **Credit / Ops (MIS):** an optional account that can only upload the login register; the master owner can upload it
  too, so MIS does not have to sign in.

**Missing**
- 3.1 **The monitor cannot see the roster.** HR uploads the roster but the HR & Admin portal has no page listing the
  employees (name, designation, branch, joining and exit dates). "Users & roles" is for the system admin only and
  "Team" exists only in the Management portal. The monitor already has the read permission; it lacks the page.
- 3.2 **A branch with no BM and no RTM has nobody to correct numbers.** Only the BM and the Cluster Manager may
  correct a customer number. The RBH answers leads for a branch with no BM (12.4) but cannot correct its numbers, so
  if that branch also has no cluster the SO's "Correct customer number" action simply expires after 15 days.
  Suggested fix: let the RBH correct numbers where there is no BM and no RTM, the same way it answers leads (confirm
  with Aham).

**Different**
- 3.3 The system finds branches with no BM by itself and sends their leads to the RBH, but no screen shows which
  branches those are (for example on the Organization page), so HR cannot spot a missing BM.
- 3.4 *Aham:* the RBH "receives regional summaries". Today the Region Manager sees them on the dashboard, compliance
  and missed-dates pages; nothing is sent (no daily e-mail or message). The document does not say how; ask Aham
  whether a sent summary is expected.
- Not a gap: there is no list of "entries with a wrong SO". With the Emp ID taken from the login, a wrong SO is rare
  and is fixed from the entry page by the RTM or the monitor.

## Step 4: Section 3, reference data
Reference data is kept apart from the entries. An entry points to its SO and branch and keeps a copy of the Emp ID
and spoke from the moment it was made, so a later roster change does not rewrite old entries.

**Done**
- **Employee roster (FOS Spoke):** the `users` table is the employee master (Emp ID unique per company, name,
  designation, branch, cluster or region, spoke, joining and exit dates, status). HR uploads it as CSV or XLSX with a
  template and "check first": rows are matched on Emp ID and updated, designation maps to a role (RO / RM / ABM →
  Sales Officer, editable in Settings), and a branch that is not in the region given is refused. New people can get a
  temporary password from the same upload. After the exit date the person can no longer sign in. The app never asks
  the SO for Emp ID, branch, region or spoke.
- **Branch–region map:** regions, optional clusters and branches (Organization page), seeded with the 7 regions and
  35 branches of Annex A. The RBH is the Region Manager attached to the region.
- **Attendance:** upload by Emp ID + date + code (also the wide "one column per day" layout); one row per person per
  day. P, P(MS), P(R), P(MS)(R) count as present (the list is a setting); every other code is absent.
- **Holidays:** a list in Settings; the count date skips Sundays and these dates; the Entry ID and the real time are
  never changed.
- **Callers:** caller accounts (role Caller) made in Users & roles; "active" is the account status. Only active
  callers can be chosen as a branch's caller of the day, and a retry whose first caller is no longer active goes to
  the branch's caller of the day instead. No limit on the number of callers.
- **Login register (MIS):** daily upload with all seven columns (TCS ID, contact, login date, product, final status,
  source, Emp code). The contact cell is kept as typed and also split into up to 3 cleaned numbers, each searchable;
  TCS ID is not unique, and the repeated-TCS-ID rule is a setting (latest row wins).

**Different**
- 4.1 **A holiday added late does not move entries already made.** The count date is fixed when the entry arrives.
  If HR adds a holiday after the day (an unplanned holiday, or a list uploaded late), entries made that day keep the
  old count date and count towards that day's compliance; removing a holiday does the same in reverse. Suggested fix:
  re-work the count dates of the entries on that day when a holiday is added or removed.
- See 3.3: the Organization page does not show each region's RBH or which branches lack a BM. A region with no RBH
  and a branch with no BM would leave that branch's leads with nobody to answer them, and nothing warns HR.
- To look at again under section 6: a caller who is active but off for the day still receives their own retries.

**Aham / data**
- 4.2 Before go-live: the real branch codes (the seed uses placeholders), the real roster upload, and Aham's answer
  on Madurai and Krishnagiri (placed as Annex A lists them until then; the Organization page shows the question).

## Step 5: Section 4.1, entry fields
**Done**
- **Emp ID, branch, region, spoke:** the request has no such fields (anything extra the phone sends is ignored); the
  server takes the Emp ID, branch and spoke from the signed-in user's roster record, and the region from the branch.
  An SO with no branch on the roster cannot submit ("Ask HR to fix your roster record").
- **Category:** the six fixed values, chosen with large buttons; the server accepts only these six.
- **CP sub-type:** shown only when Category = Contact Point, required then, and refused by the server for any other
  category. The list is editable (HR & Admin → Settings → CP sub-types); an option retired later is still accepted for
  an entry made offline before.
- **Name of person met** and **short description:** required on the phone and on the server (blank or spaces only is
  refused); up to 200 and 2,000 characters.
- **Mobile (WhatsApp) number:** required; checked live as typed, Submit blocked until valid; checked again by the
  server (details in 4.3).
- **Keka photo time:** a separate time field (HH:MM), stored as given, never used for the Entry ID or dates.
- **Submission timestamp:** taken by the app at the Submit tap, not editable, and sent with the entry; it gives the
  Entry ID and the entry date, also for an entry made offline and sent later. There is no "Date" field.
- **One entry per person met:** each Submit is one entry; "Save & add another" starts the next one.

**Different**
- 5.1 **A phone clock set back is not caught.** The submission time comes from the phone's clock, which is what lets
  an offline entry keep its real time (your requirement). An entry whose phone clock is more than 5 minutes ahead of
  the server is flagged "check the time", but a clock set back, for example to put today's meetings on yesterday,
  looks the same as an entry that waited offline. The entry page shows "synced N h later", but nothing flags it.
  Suggested fix: the app notes the gap between its clock and the server's at each sign-in and sync, together with the
  phone's time since start-up, and flags an entry made after the clock was changed by hand.

**Aham / data**
- 5.2 Keka photo time is optional (the document only says the current forms ask for it) and the SO types it on every
  entry, although it is one photo a day. Ask Aham whether it is required. Small improvement either way: fill it in
  from the SO's earlier entry of the same day.
- 5.3 The full CP sub-type list from the current forms. The app starts with "Sand / Gravel / Brick Shop", "Other
  Hardware Shop" and "Other"; HR can add the rest in Settings without a code change.

## Step 6: Section 4.2, Entry ID
**Done**
- **Format** `<EmpID>-<YYYYMMDD>-<HHMMSS>` from the Submit time, in India time, **truncated** to the second
  (09:07:06.999 → 090706). Built the same way on the phone (`mobile/src/lib/rules.ts`, shown to the SO at once, even
  offline) and on the server (`services/calendar.py`), with the same test cases on both sides.
- **Separate business ID:** each entry has an internal UUID; the Entry ID is a separate column, unique per company.
  Calls, the lead card, branch answers, the tracker and the history all point to the internal ID.
- **Permanent:** no screen or API changes an Entry ID after it is made (checked in the code).
- **Wrong SO (13.1):** the RTM or the monitor picks the right SO; the Entry ID stays, the SO, branch and spoke change
  (the region follows the branch). Compliance, dashboards and the Takeoff export ("Emp ID (credited SO)") follow the
  new SO. The entry keeps the original Emp ID and original SO, and its history records old and new.
- **UNRES placeholder IDs ([Legacy]):** not built; the Emp ID always comes from the login.
- **Never overwritten:** the database refuses a second entry with the same Entry ID, and a retry of the same entry
  (same idempotency key) returns the first one instead of making a copy.

**Aham**
- 6.1 **Same SO, same second.** The document's format cannot tell two such entries apart and does not say what to do.
  Today the second one gets "-2" (`AHFL01810-20261015-090706-2`); the phone shows its own ID at Submit and switches
  to the server's once sent. This is listed as our assumption and needs Aham's yes or another rule. In practice it
  can only happen if an SO completes two separate forms within one second, since a double tap or a resend is the
  same entry and keeps the first ID.

## Step 7: Section 4.3, phone cleaning and validation
The same rules run on the phone (`mobile/src/lib/rules.ts`) and on the server (`backend/app/services/phone.py`), with
the same test cases on both sides; the login register (section 11) uses the server copy.

**Done**
- **Rule 1, clean:** a trailing ".0" is removed first (so `9876543210.0` → `9876543210`, not `98765432100`), then
  everything that is not a digit 0-9: spaces, "+", "-", brackets, invisible Unicode marks.
- **Rule 2, prefix:** 11 digits starting with 0 → drop the 0; 12 digits starting with 91 → drop the 91.
- **Rule 3, valid:** exactly `[6-9]\d{9}` after cleaning.
- **Rule 4, block:** the app shows the problem while the SO types ("A mobile number has 10 digits" / "starts with 6,
  7, 8 or 9") and Submit stays off until it is valid; the server checks again and refuses an invalid number, so no
  entry ever has a bad number. "Not called – no valid number" can therefore not happen for new entries.
- **Rule 5, name/number swap ([Legacy]):** not built; the number field must hold a valid number.
- **Audit trail:** the number as typed is kept next to the cleaned 10-digit number, which is used for calling and
  matching.

**Aham**
- 7.1 **"+91 0…"** (for example `+91 09876543210`) cleans to 13 digits, which neither prefix rule covers, so the app
  refuses it as invalid and the SO must retype it without the 0. No extra rule was added. Ask Aham whether that is
  right or whether "91 + 0 + 10 digits" should also be accepted.

## Step 8: Section 4.4, which day an entry counts on
**Done**
- Three separate stored values: the Submit time (`submitted_at_device`), the **entry date** (its date in India time)
  and the **count date**. The count date never overwrites the entry date, and the Entry ID keeps the real date and
  time (a Sunday entry is `…-20261025-103045` and counts on Monday).
- Count date = entry date on a working day; otherwise the next working day, checking again until one is found, so a
  Sunday followed by a holiday Monday counts on Tuesday (`services/calendar.py`, tested with exactly that case).
- Working day = not a Sunday and not on the holiday list. **Saturday is a working day**: no Saturday rule was added.
  If some Saturdays are off (for example the 2nd and 4th), HR adds them to the holiday list; no code change.
- Daily compliance and the SO's daily count on the server use the count date, so 7 entries on Monday plus 3 on the
  Sunday before make 10 for Monday.

**Different**
- 8.1 **The phone's "Today" number mixes the two dates.** The home screen adds the server's count for today (by count
  date) to the entries still waiting on the phone (by entry date). So on a Sunday the number rises while entries
  wait offline, then falls back once they are sent (they count on Monday). The screen explains this on Sundays, but
  the phone does not know the holiday list, so on a holiday the number drops with no reason shown. Suggested fix: the
  app gets the holiday list with the profile, counts waiting entries by count date as well, and shows "counts on
  Mon 26 Oct" on a Sunday or holiday.
- See 4.1: a holiday added after the day does not move entries already made.

## Step 9: Section 4.5, daily compliance
Built in `backend/app/api/v1/reports.py` (`/compliance`, `/compliance/export.csv`) and the "Daily compliance" page
(Management and HR & Admin portals; each role sees its own scope).

**Done**
- **10 entries per present SO per day**, all six categories, counted on the **count date**; both targets are settings.
- **5 genuine Lead/Prospect**, counted separately and shown as "n (−short)". "Genuine" leaves out "repeat entry by
  same SO" and "duplicate entry" (our assumption, listed for Aham in 1.3).
- **Shortfall** = target − entries, never below 0 (11 entries show 0, not −1); **"AB"** when the attendance code is
  not one of P, P(MS), P(R), P(MS)(R).
- **Joiners:** "N/A" (shown "Not joined yet") before the joining date; the target applies from the joining date.
- **Exits:** listed up to and including the exit date, left out from the next day.
- Page: pick a day and a branch; totals for SOs (present / absent / not marked), entries, met the target, joiners;
  one row per SO with attendance, entries, shortfall and Lead/Prospect. CSV export for a date range (up to 62 days)
  for HR, Product and Business Managers.

**Missing (small)**
- 9.2 The CSV export has entries, Lead/Prospect and shortfall, but not the Lead/Prospect shortfall, "met the
  target" or "met the Lead/Prospect target" columns. The page filters by day and branch only: no region filter (for
  HR and the Product / Business Managers) and no search for one SO. The totals show "met the target" as a count, not
  as a percentage, and do not count how many met the Lead/Prospect target.

**Aham**
- 9.1 **No attendance row for the day.** The document defines present and absent by code, but not a missing row
  (attendance not uploaded yet, or the SO missing from the file). Today such an SO is shown "not marked" and gets a
  number shortfall, as if present. Ask Aham whether that is right, or whether a missing row is absent ("AB").
- 9.3 **"Publishes daily compliance".** The report is live: an entry made offline and sent days later still counts on
  its count date, so a past day's figures can change. Ask whether HR needs a frozen copy of each day once published
  (and whether late entries should still count).

## Step 10: Sections 5.1 and 5.2, call group and fresh entries
**Done**
- **5.1 Call group:** Lead and Prospect → Lead; DSA/Connector and Contact Point → DSA/CP; Existing Customer and
  Existing Applicant → not called (`rules.CALL_GROUP`). Stored on the entry when it arrives and updated if the
  monitor changes the category (branch code 2). Existing Customer / Applicant entries are never selected, whatever
  their number.
- **5.2 Fresh**, all five conditions (`engine.is_fresh`, and the same conditions in the daily run's query):
  has an Entry ID; never selected before (an entry cannot be called until the run selects it, so "never selected"
  is "never called"); has a call group; entry date on or after the **first call date** setting (24 Sep 2026); entry
  date **before** the run date.
- **Same-day calling** is the [Aham to decide] setting "Allow same-day calling", **off** by default, so entries are
  called from the next day. Turning it on changes "before the run date" to "on or before".

**Bug**
- 10.1 **Existing Customer / Existing Applicant RAG.** These entries get RAG "NA" when they arrive (not called, as
  section 9 says). But the RAG rule used for every later recalculation (`engine.rag_for`) treats "never selected"
  as "waiting to be called" and gives "PENDING". So the RAG flips to PENDING when the entry is recalculated: a login
  register upload that contains its number (likely for an existing customer or applicant), a wrong-SO correction,
  or a category review. Fix: the RAG rule returns NA for the "not called" call group, with a test. Related, smaller:
  an entry dated before the first call date can never become fresh, so it stays "PENDING" for ever; it only matters
  if old entries are imported or the first call date is moved later.

## Step 11: Section 5.3, decision for each fresh entry
Built in `engine.selection_decision` (the order) and `ops.run_selection` (the facts it needs); one test per row of
the table in `test_engine_rules.py`, plus flow tests with real entries.

**Done**
- **Order:** the seven checks run in the document's order and the first that applies decides; a later check cannot
  overwrite it.
- **Check 1, no valid number** → "Not called – no valid number" (Amber, SO action "Correct customer number"). Uses
  the same phone rule as 4.3; it cannot happen for new entries because the app blocks them.
- **Check 2, repeat by same SO (Lead group):** same SO, same cleaned number, an earlier entry (by Submit time, so
  two entries on the same day are ordered correctly) within the repeat window (setting, 30 days).
- **Check 3, duplicate:** fresh entries are handled in Submit-time order; a later one with a number already seen in
  this run is "duplicate entry", so the earliest wins whichever SO made it.
- **Check 4, being called:** see 11.1.
- **Check 5, spoken within 30 days (Lead group):** a Connected call on any entry with that number, by any SO, within
  the window counted back from the run date.
- **Check 6, known contact (DSA/CP group):** a Connected call on that number at any time.
- **Check 7:** otherwise "Allocate", and the entry goes to allocation (section 6) in the same run.
- **Final:** the run only looks at entries never decided before, so a "Not called" result is never re-evaluated.
  Running the same day again only adds what is missing.
- **"Spoken to" = a Connected call only.** The [Legacy] meanings (a verdict, or any remark that is not a no-answer
  phrase) are not used.
- Each decision is stored with its run date and written to the entry's history.

**Aham**
- 11.1 **Check 4 is a little wider than the text.** The document says "the number is currently In retry on another
  entry". The app also counts an entry with that number that is **allocated and waiting for its first call** (for
  example a list the caller did not finish yesterday). Without that, the new entry would be allocated too and two
  callers could ring the same customer. Ask Aham to confirm.
- 11.2 **Offline entries and "earliest wins".** Check 3 compares entries within one daily run. If SO A meets a
  customer offline on Monday but the entry only arrives on Wednesday, while SO B's entry for the same number arrived
  on Tuesday and was already allocated, A's earlier entry gets "Not called – number already being called" and B's is
  the one called (and credited). Google Forms never had this case. Ask Aham whether the earliest Submit time should
  still win in that case (it would mean moving the call and the credit from B's entry to A's).

## Step 12: Section 6, allocation to callers
Built in `ops.allocate` (run right after the selection, in the same daily run) and the call-centre portal pages
"Daily run & allocation" and "My calls".

**Done**
- **Caller of the day per branch:** the master owner picks one active caller per branch for a date, with "copy
  yesterday". Each change is in the audit log.
- **New entries** go to their branch's caller of the day. A branch with no caller set leaves the work "unassigned":
  the run says how many, and the master owner assigns them on the same page.
- **Retries** go to the caller who made the first call (`first_caller_id`), not to the branch's caller of the day.
  A caller named on the follow-up tracker wins; if the first caller's account is no longer active, the retry goes to
  the branch's caller of the day.
- **A retry is due today** when it is In retry, has no callback date or one on or before the run date, was not
  called today, and is not logged in (nor rejected).
- **Unreturned work:** at the next run, every list item from an earlier day that was not worked is closed as
  "unreturned" and the work is offered again (count shown on the run).
- **Turnaround target:** a setting (1 day); "Caller performance" shows the share of first tries made on time.
- **PRIORITY:** set by branch answer code 3 (customer not answering the branch), by the tracker outcome "Reopen for
  calling", or by the master owner's "Immediate call-back". Priority entries are listed first (then retries due,
  follow-ups, new); several priority entries are in Submit-time order. The flag clears after the next try.

**Missing**
- 12.1 **Absent caller.** Retries and priority calls go to the first caller even when that person is off for the
  day; the only way to move them is one entry at a time through the follow-up tracker. The server can move any open
  list item to another caller, but the screen only offers it for unassigned items. Suggested: "move today's list of
  caller X to caller Y" on the Daily run page. (Aham may also want to say whether retries should wait for the first
  caller or go to the branch's caller of the day.)
- 12.2 **Turnaround on the lists.** The 1-day target is only measured afterwards (a percentage). Nothing marks an
  entry on a caller's list or on the Daily run page as "first try overdue".
- 12.3 **Priority reason.** The reason ("Branch: customer not answering", "Master owner: immediate call-back",
  "Reopened for calling") is stored, but the list only shows the PRIORITY group, not the reason on each row.

**Aham**
- 12.4 **Unreturned entries that were never called** go to the branch's caller of **today**, who may differ from
  yesterday's; unreturned retries stay with their first caller. The document does not say which; this is our
  assumption.

## Step 13: Section 7.1, attempts
Built in `ops.record_attempt`, `engine.row_status` and `engine.attempt_allowed`; the call screen in the call-centre
portal.

**Done**
- **Lead group:** unanswered tries are counted per calling cycle; the 9th gives "Discarded – 9 unanswered" and the
  entry gets no more retries (a corrected number starts a new cycle with a fresh 9). Two tries are planned a day:
  after the second the entry leaves today's list. Up to three can be recorded in one day (see 13.2). Both numbers
  are settings.
- **DSA/CP group:** one try, on one calling day only; an unanswered try gives "Closed – no answer" (no retries).
- **Unanswered** = RNR, Busy, Switched off, Not reachable only. Invalid number, Wrong person, Refused to talk and
  Callback requested have their own results and do not count towards the 9.
- **10 time slots** (09-10 … 06-07) and **9 outcomes**; a try cannot be saved without both.
- **Callback requested:** the caller must pick a Next date (not in the past, not a Sunday); the entry stays In retry,
  leaves the lists until that date, then comes back as a retry (and shows as the call-centre action "Callback").
- **History:** every try is its own row (`call_attempts`): entry, caller, date, slot, outcome, next date, the answers,
  the status it produced, the cycle and the exact time it was saved. The entry page and call screen show them all,
  with the unanswered count.

**Bug**
- 13.1 **DSA/CP + "Callback requested" gets stuck.** The callback puts the entry In retry for the chosen date, but on
  that date the DSA/CP rule "called on one day only" refuses every try (unless the entry is PRIORITY). The entry
  comes back on the caller's list every day and can never be called or closed. The document gives DSA/CP one
  calling day and does not say what a callback means for it, so Aham should choose: allow the callback day as the
  one extra day, or close the entry ("Closed – no answer"). Either way it needs a fix and a test.

**Aham**
- 13.2 **The third slot.** The app's reading: two tries are planned per day (morning and afternoon), and a third can
  still be recorded on the same day (for example the customer rings back). The app does not check that the two
  tries fall in the morning and the afternoon; any two slots are accepted. Ask Aham to confirm.

## Step 14: Section 7.2, Lead questions once connected
**Done**
- All **13 fields** with exactly the document's options (`rules.py`, checked by the server, which refuses any other
  value): name check, name as given, visit, relationship, loan need (9 types), timeline, income, documents ready,
  next step, next date, purpose, own contribution, remarks. They appear on the call screen only for a Connected
  call, and the server refuses answers on any other outcome.
- Answers may be left blank; classification handles it (a blank Loan need gives "Amber – answers missing", 8.1).
- **Name as given** is stored with the call; the name the SO typed stays unchanged on the entry.
- **Next date** must not be a Sunday (server check); holidays are not excluded, as the document only says Sundays.
- Only the rules of section 8.1 use the answers (loan need, documents, relationship = same officer, name check,
  visit); "Yes – another employee", timeline, income, purpose and own contribution have no rule of their own, as in
  the document. Next step, next date and documents feed the actions of section 12.
- **History:** the answers are kept with each call (one record per call), so a second connected call adds new
  answers and never overwrites the first. The entry's status follows the latest call that produced one.

**Different**
- 14.1 The date pickers for Next date and Callback date are ordinary calendars that still offer Sundays; choosing a
  Sunday is refused only when the caller presses Save. The document says working days are "offered", so the
  picker should skip Sundays or warn at once.

**Aham**
- 14.2 Next date is optional. With Next step = "SO / branch visit" and no date, the branch gets "Visit customer"
  with no date (12.1 says "on the Next date"). Ask whether Next date should be required for "SO / branch visit" (and
  for "Call centre to continue").

## Step 15: Section 7.3, DSA/CP questions once connected
**Done**
- The two questions with the document's options: **RAG given by caller** (Green, NA, Amber, Red) and **Needs a home
  loan himself?** (Yes, No). Shown on the call screen only for a DSA/CP entry.
- **Yes:** the call screen opens the 13 Lead questions and the **Lead logic (8.1) is applied** (`engine.dsa_logic`);
  only a "Validated…" result becomes "Validated – converted from DSA/CP". Answering Yes alone does not validate:
  a blank loan need gives "Amber – answers missing", "Not looking for a loan" gives Red, and so on.
- **No:** status from the caller's RAG: "DSA/CP – Green / NA / Amber / Red", and **"DSA/CP – no RAG" when left
  blank** (not NA).
- The entry's **category is not changed** by the conversion; the converted status marks it. A converted entry is
  treated as a lead afterwards for the lead card, the SO/branch lead actions and the login outcome (11.2).
- Answers are kept with each call (history), as for the Lead questions.

**Bug**
- 15.1 **A converted entry keeps the DSA/CP calling limits.** The entry's call group stays DSA/CP, so the rule "a
  DSA/CP entry is called on one day only" still applies. When the converted lead needs a call-centre follow-up on a
  later day ("Call centre to continue" → "Take case forward", or a follow-up date from a branch answer or the
  tracker), the caller cannot record the call; only a PRIORITY entry gets past the rule. And if such a call were
  unanswered it would give "Closed – no answer" (DSA/CP) instead of a lead retry. Fix: once an entry is converted,
  use the Lead group's calling rules for it (keeping its category). Same area as 13.1.

**Aham**
- 15.2 The document lists the four RAG choices for a DSA/CP contact but not what each means. Callers need Aham's
  criteria (for example Green = active referrer, NA = no follow-up needed); once given, a short guide can be shown
  next to the choice on the call screen.

## Step 16: Section 7.4, lead card
Built in `schemas.LeadCardIn`, `ops.save_lead_card` and the lead card on the call screen.

**Done**
- **Opens** once the latest connected call's Loan need shows a loan type (any of the eight, LAP and BT + LAP
  included); not for a blank need or "Not looking for a loan" (the server refuses it too).
- **All fields** of the document: handling branch, age, date of birth, address, city, property and business
  pincode, payslip or ITR, job profile, individual and family monthly income, vehicle (yes/no and type), CIBIL,
  EMI or cheque bounce in the last 6 months (one field), property owner, property area, approved property,
  property type, purpose of loan, loan requirement, Lead ID.
- **Handling branch:** picked from the branch list; blank means the SO's branch; stored apart from the SO's branch,
  which is never changed.
- **Checks:** pincodes exactly 6 digits; incomes and loan requirement whole rupees; **CIBIL 300–900 or blank**.
- **Loan requirement compulsory once a Lead ID is entered** (screen and server); no other field is required.
- **Lead ID:** typed by the caller after creating the lead in TCS, stored with the entry, its time recorded and
  written to the entry's history. It never validates, closes or counts the entry (checked in step 2).

**Bug**
- 16.1 **Amounts are not forced to be numbers.** The amount boxes keep only the digits of what is typed instead of
  refusing text: "40L" is saved as **₹40**, "7 lacks" as ₹7, "35.5 lakh" as ₹355. This is exactly the Excel problem
  the document wants removed, and the loan requirement decides the green channel (₹8 lakh / ₹15 lakh), so a wrong
  amount can wrongly hold a branch's R2/R3 rejection for head office. Same for the income boxes. Fix: refuse
  anything but digits (commas allowed), and show the amount back as "₹40,00,000 (40 lakh)" so the caller can see
  it is right.

**Missing**
- 16.2 **Handling branch is not used.** It is stored and shown, but the lead still goes to the SO's branch: that
  BM's "Leads to answer", the branch actions and the branch's figures. The document's meaning is that the other
  branch works the lead when the property is in its area. Confirm with Aham, then route the lead (answers, actions,
  missed dates) to the handling branch while credit stays with the SO.

**Different**
- 16.3 Saving the lead card writes only the Lead ID to the entry's history. Changes to other fields, including the
  loan requirement that decides the green channel, are not recorded (who, when, old and new value).

**Aham**
- 16.4 Age and date of birth are both free (the app does not work one out from the other); age is limited to
  18–100, which is our check. Property owner, approved property, property type, purpose of loan and vehicle type
  are free text because the document gives no options; Aham may want fixed lists (and whether purpose of loan
  should follow Loan need).

## Step 17: Section 8.1, Lead logic
**Done**
- The eight rules in the document's order, first match wins, in their own pure function (`engine.lead_logic`), not
  in the API: blank loan need → "Amber – answers missing"; "Not looking for a loan" → Red; LAP or BT + LAP → "Not
  counted – LAP" (Balance transfer alone is not caught); "File already logged with Aham" → "Already in process";
  "Yes – the same officer" → "Amber – knows SO"; name check starting "Different person" → "Validated – different
  person"; Visit = No → "Validated – visit not confirmed"; otherwise Validated. A blank name check or visit cannot
  break the rule.
- Tests (`test_engine_rules.py`) check each rule and the order where two rules match (LAP before "already logged",
  "already logged" before "knows SO", "different person" before "visit No"), and that "Don't recall" and "Yes –
  another employee" stay Validated.
- The caller's answers and the status are kept apart: answers and the status they produced are stored with each
  call (with the time), the entry carries the current status and the time it changed. The call screen shows the
  status the answers will give before the caller saves, but the caller cannot choose it.

**Aham**
- 17.1 The document does not say what follows these two statuses, and the app gives no action for them: the RAG is
  Amber, but there is no SO action (section 12.1 has none for them) and no call-centre action.
  - **Amber – answers missing** is a caller slip (Loan need not filled). Today only the master owner can fix it, by
    reopening the entry for calling from the follow-up tracker. Should the caller be able to correct the answers, or
    should the entry come back for a call automatically?
  - **Amber – knows SO**: is anyone meant to act (the monitor, the RTM), or is it simply not counted?

## Step 18: Section 8.2, DSA/CP connected
Same code as step 15 (`engine.dsa_logic`), re-checked against this section.

**Done**
- **Yes:** the Lead questions appear on the same call screen (a conditional part of the form, not a separate
  process) and the **same** `lead_logic` function is used, not a copy of the eight rules. Only a result starting
  "Validated" becomes "Validated – converted from DSA/CP"; Amber, Red, "Not counted – LAP" and "Already in process"
  stay as the Lead rules give them. Tested, including Yes + "Not looking for a loan" → Red.
- **No** (or the question left blank): the caller's RAG gives "DSA/CP – Green / NA / Amber / Red", and a blank RAG
  gives **"DSA/CP – no RAG"**, never NA. Tested for all five.
- The original category stays; the call group and the answers (needs home loan, caller's RAG, Lead answers) are
  stored with the call; the status records the conversion.
- **Yes with the Lead questions left incomplete:** the Lead rules run on what was answered, so a blank loan need
  gives "Amber – answers missing". The form does not force the Lead questions to be filled; whether it should is
  part of question 17.1.

**Missing / different:** nothing new. See 15.1 (a converted entry keeps the DSA/CP call limits) and 15.2 (meaning
of the DSA/CP RAG choices).

## Step 19: Section 8.3, not connected
**Done** (`engine.row_status`, one test per row)
- Invalid number → "Discarded – invalid number" (both groups); Wrong person → "Amber – wrong person" (both groups,
  SO action "Correct customer number" for 15 days, 12.1); Refused to talk → "Rejected – refused to talk" (both
  groups).
- Unanswered (RNR, Busy, Switched off, Not reachable): DSA/CP → "Closed – no answer"; Lead → "In retry" until the
  9th unanswered try of the cycle, which gives "Discarded – 9 unanswered".
- Callback requested (from 7.1) → "In retry" with the callback date; it does not count as unanswered.
- "Not called – no valid number" (selection, before any call) and "Discarded – invalid number" (the caller found the
  number dead) are separate statuses.
- Attempt history is separate from the entry's current status; the unanswered count is worked out from the history
  for the current cycle, and the entry's status is updated after every call.

**Aham (important)**
- 19.1 **Which calls change the status?** The document says an entry's status is the row status of its latest call
  "that produced one", which suggests some calls do not produce one; it does not say which. The app's assumption
  (listed in `docs/sankalp-rules.md`) is that **every** call produces one. The consequence for a lead that is
  already Validated and gets another call (a call-centre follow-up, "Take case forward", or a PRIORITY call after
  the branch's code 3):
  - the call is unanswered → the status becomes "In retry", so **"Customer validated" turns off**, the branch's lead
    action ("Visit customer" / "Collect documents" / "Follow up lead") disappears, and the RAG becomes RNR, until a
    later call reaches the customer again;
  - the call connects and is Validated again → "Validated on" moves to the date of this later call, not the first
    validation;
  - the call connects and the customer now says "Not looking for a loan" → Red.

  Example: validated on 5 Oct, follow-up on 20 Oct is RNR → on the Takeoff export the entry is no longer "Customer
  validated" until someone reaches the customer. Options for Aham: (a) keep as is; (b) after a lead is validated,
  only a connected call changes the status (unanswered follow-ups leave it Validated); (c) follow-up calls never
  change the status. Either way "Validated on" should probably stay the date of the first validating call. This
  affects the incentive flags, so it needs Aham's answer before go-live.

## Step 20: Section 8.4, old-process verdicts ([Legacy])
**Done (as the document asks)**
- The six old verdicts ("Green – send to branch", "Green – call centre to follow up", "Logged in with Aham",
  "Amber – wrong / invalid number", "Red – not genuine", "NA – nothing pending") are **not** in the app: new calls
  are classified only by sections 8.1–8.3, and no old verdict is mapped to a new status. Listed as not built in
  `docs/sankalp-rules.md`.

**Aham**
- 20.1 The document says the old verdicts are probably needed only to import history, and this is the same open
  question as the README's "history since 22 Sep". If Aham wants the entries and calls from the Excel workbooks
  brought in (useful because the 30-day, "known contact", first-validation and one-success-per-TCS-ID rules look
  back at earlier entries), the import should keep each old verdict as it was, in its own field, and use a mapping
  table that Aham confirms row by row. Nothing should be converted automatically (old Green is not the new
  Validated). Not built until Aham decides.

## Step 21: Section 9, RAG
Built in `engine.rag_for` (15 test rows in `test_engine_rules.py`) and worked out again after every event and by the
daily job (actions that expire).

**Done**
- Every row of the table, with the overlaps resolved so the specific row wins: "Not called – no valid number" →
  AMBER while every other "Not called" → NA; not yet called / waiting → PENDING; Red and DSA/CP – Red → RED; any
  "Amber…", DSA/CP – Amber and "Discarded – invalid number" → AMBER (checked before "Discarded (any) → RNR"); In
  retry → RNR with an unanswered try, GREEN with none (e.g. after a corrected number); other Discarded and "Closed –
  no answer" → RNR; DSA/CP – Green → GREEN; DSA/CP – NA → NA; any other status with an open SO or call-centre
  action → GREEN; otherwise NA; logged in or rejected → NA.
- **Manual override:** the master owner sets it on the follow-up tracker. It is stored apart from the automatic RAG
  (both kept), wins everywhere it is shown, filtered and counted, and the entry is marked "overridden". Clearing it
  brings back the automatic RAG.
- The SO sees the RAG of each entry and the last-30-days counts in the app.

**Different**
- 21.1 **Lost lead.** Section 9 says a lost lead (the need has passed, or a loan taken elsewhere) is NA, not Red.
  The app gives NA when the branch rejects it (R4 "loan taken elsewhere", R5 "not interested") or the master owner
  marks it rejected. But if a later call finds the customer no longer needs the loan, the caller can only answer
  "Not looking for a loan", which the Lead rules make **Red**, the SO's "nobody met me / does not want a loan"
  colour. Linked to 19.1 (whether later calls change the status at all); options: a later call cannot turn a
  Validated lead Red, or a "need has passed / loan taken elsewhere" answer that gives NA.

**Aham**
- 21.2 The table does not say in which order its rows apply. The app checks "logged in or rejected → NA" first
  (so a logged-in lead is NA whatever its last call said), then the rows top to bottom. Ask Aham to confirm.
- See 10.1 (bug): Existing Customer / Applicant entries can show PENDING instead of NA.

## Step 22: Section 10, incentive flags
Worked out by `engine.derive` after every event; "first validation" by `ops.recompute_phone_group`. Tested in
`test_engine_rules.py` (`test_login_outcomes_and_validation`, `test_success_and_first_validation`).

**Done**
- **Customer validated:** status starts with "Validated" (all four), **or** lead outcome Logged in and not LAP; in
  both cases **not** "Not called – repeat entry by same SO".
- **First validation for this number:** among all entries with the same cleaned number, from any SO, only the
  earliest validated one (by Submit time) gets it; worked out again whenever any of them changes, including when a
  number is corrected (old and new number).
- **Validated on** and **Counts as Sankalp success** (section 11.3) are stored as their own fields, apart from the
  status.
- The **Takeoff export** (HR & Admin, CSV for a date range) carries, per entry: Entry ID, credited SO, branch,
  region, dates, category, phone, selection, status, RAG, repeat entry by same SO, customer validated, first
  validation for this number, validated on, lead outcome, TCS ID, login date, Sankalp success.
- **Money:** not calculated; the ₹60 / 5-a-day rule is not in the code ([Aham to decide]).

**Different**
- 22.1 **Validated on** is the date of the **latest** call whose status is Validated. If a later follow-up call
  validates the lead again, the date moves to that later call; if the lead is validated only through a login (no
  validating call), the login date is used. The document says "the date of the call that validated it". Linked to
  19.1: since a later unanswered call can switch "Customer validated" off, "First validation for this number" can
  also move to another SO's entry for a while. Suggested: keep the date of the first validating call.

## Step 23: Section 11, login register, lead outcome, Sankalp success
Upload in HR & Admin → Uploads (MIS, master owner, system admin) with "check first"; matching in `ops.best_login`;
outcome in `engine.lead_outcome`; success in `ops.recompute_tcs_group`. Flow test `test_login_register_rules`.

**Done**
- **11.1 Matching:** the contact cell is split on `,` `/` `&` `;` (and on spaces when the part is not one number),
  each part cleaned with the same function as the entries (4.3), and **every** number is stored and searchable; an
  entry matches a row on any of them. Every uploaded row is kept with its file and row number (audit).
- **Repeated TCS ID:** one row wins per TCS ID; the rule is the [Aham to decide] setting, "latest row" by default
  ("first row" available).
- **Manual route:** the master owner types a TCS ID on the follow-up tracker when the phone cannot be matched; it
  counts as a login (shown as "manual").
- **11.2 Lead outcome** (lead-type entries only: Lead group, converted DSA/CP, entries with a lead action): Logged in
  when a TCS ID is found and the login date is after the entry date, or the TCS ID was entered by hand; Rejected when
  the master owner or the branch rejected it; "Login on/before entry date (not counted)" when the login date is on or
  before the entry date. A login wins over a rejection. A register row with no login date does not count as a login.
- **11.3 Sankalp success:** Logged in, entry date on or after Takeoff start (setting, 22 Sep 2026), and the earliest
  entry for that TCS ID (ties: lower Entry ID). One success per TCS ID, worked out again whenever the group changes.
- **LAP:** a LAP login can be a Sankalp success but is not "Customer validated" (separate flags).
- The entry keeps the TCS ID, login date and how it was found (register or manual).

**Aham**
- 23.1 **Which entries compete for "earliest entry for the TCS ID"?** Every entry whose number matches the login gets
  the TCS ID, including Existing Customer, Existing Applicant and DSA/CP entries, which can never be "Logged in"
  themselves (lead outcome only applies to lead-type entries). If one of them is the earliest, **no entry gets the
  success**. Example: SO A records the person as "Existing Applicant" on 1 Oct, SO B records them as a Lead on
  5 Oct, the lead is validated and logs in on 20 Oct: no Sankalp success. That may be right (they were already an
  applicant) or not; Aham should say whether only lead-type entries compete.
- 23.2 **"The latest register row wins"** is read as the row uploaded last (a later file, or lower in the same file),
  not the row with the latest login date. And if one phone matches two different TCS IDs, the app uses the first
  login after the entry date (or, if none, the most recent one). The document does not cover either; confirm.
- 23.3 **LAP login:** recognised when the register's Product text contains "LAP". Aham should give the exact product
  names used in the register so this is reliable.

## Step 24: Section 12, actions and branch answers
Actions are worked out in `engine.derive` after every event and by the daily job; branch answers in
`handoff.answer_lead` and `review_green_channel`; screens: "Leads to answer", "Open actions", "Green channel",
"Call-centre actions", the entry page, and the SO's entries in the app.

**Done**
- **12.1 SO / branch action:** none once logged in or rejected; "Correct customer number" for Amber – wrong person,
  Discarded – invalid number and Not called – no valid number; "DSA/CP follow-up" for DSA/CP – Green; for any
  Validated or Not counted – LAP: Next step "SO / branch visit" → "Visit customer" on the Next date, "Call centre to
  continue" → no branch action, otherwise Documents Partly / No → "Collect documents", otherwise "Follow up lead".
- **12.2 Call-centre action:** In retry with a callback date → "Callback" on that date; "Call centre to continue" →
  "Take case forward"; sent by the master owner (tracker) or by a branch date beyond 14 days → "Follow-up" on that
  date. These entries come onto the callers' lists on their date (section 6).
- **12.3 How long:** lead actions (visit, documents, follow up lead) never expire, only login or rejection closes
  them; "Correct customer number" 15 days from the entry date; every other action 14 days from its date (settings).
  The daily job drops expired ones.
- The SO sees the action and its date on each entry in the app, with a "needs action" filter, and the numbers to
  correct on the home screen; managers see "Open actions" for their scope.
- **12.4 Branch answer:** all 24 codes with their meaning and the date each one asks for (Login date / Follow-up
  date / Visit date), refused without it, and never in the past. One code and one date per lead: a new answer
  replaces the last one, and every answer stays in the history.
  - Code 1 does not close the lead (only the register does); code 2 → the monitor's "category wrong" queue;
    code 3 → PRIORITY retry by the call centre; R1–R6 → rejected.
  - **14-day rule:** a date up to 14 days after the answer keeps the lead with the branch (its action moves to that
    date); a later date sends it to the call centre as a follow-up on that date. The 14 days is a setting.
  - **Green channel:** self-construction or improvement up to ₹8 lakh, home purchase or plot + construction up to
    ₹15 lakh (settings), judged on the **call centre's** loan requirement. An R2 or R3 on such a lead is not taken as
    a rejection: it waits in "Green channel" for the head-office reviewer (assumed: the master owner), who sends it
    back to the branch to log in (the default) or accepts the rejection.
  - **No BM:** the RBH sees and answers the leads of its branches that have no BM.
  - **Missed dates:** counted per branch (answers whose date has passed with no login and no newer answer), shown
    for the branch's scope.

**Different**
- 24.1 **Actions are not separate records.** Each entry carries its current SO/branch action and call-centre action
  (with dates), worked out from the calls, answers and tracker. There is no "done" or "expired" state, nothing for
  the SO to tick off (the branch updates through its answer codes), and no report of actions that expired unworked
  (for example "Correct customer number" windows that ran out). The entry's history shows each change.
- 24.2 **Missed dates** count the latest branch answer's date. That also counts a date that the 14-day rule passed
  to the call centre (the call centre's date, not the branch's), and a lead that the master owner later rejected
  on the tracker while the branch answer still holds a past date.

**Aham**
- 24.3 After the 15-day window, "Correct customer number" closes but the entry stays Amber (wrong person / invalid
  number) with no action for anyone. The document does not say what should follow (for example closing it as NA).
- The head-office green-channel reviewer is assumed to be the master owner (already in the assumptions list). The
  codes keep the document's wording ("IMD", "pre-PD"); Aham may want fuller labels for branch staff.

## Step 25: Section 13, corrections
Built in `handoff.correct_so`, `handoff.correct_number`, `handoff.save_tracker` and `engine.derive`; buttons on the
entry page ("Correct SO", "Correct number", "Follow-up tracker").

**Done**
- **13.1 Wrong SO** (checked in step 6): the RTM, or the monitor (or the BM where the branch has no cluster) picks
  the right SO from the roster; the Entry ID stays; the SO, branch and spoke change and the region follows the
  branch; counts, compliance and credit follow the new SO. The history keeps old and new SO and branch, who and when.
- **13.2 Wrong number:** the BM or RTM types the right number (from "Open actions" or the entry page) while the
  entry has the "Correct customer number" action, up to 15 days after the entry date (setting). The new number must
  be valid and different. The entry keeps its Entry ID, starts a **new calling cycle with a fresh 9 tries** and goes
  back on a caller's list at the next run (its first caller, else the branch's caller of the day). The old calls
  stay in the history, marked as the earlier cycle, and the history records old and new number, who and when.
- **13.3 Follow-up tracker:** one row per entry with all nine fields (owner, action type, caller, follow-up date,
  outcome, TCS ID, reject reason, RAG override, notes) plus "immediate call-back". **Master owner only**, checked by
  the server. What each part does:
  - "Reopen for calling" or immediate call-back → PRIORITY call; Caller → retries go to that caller.
  - "Rejected" → lead outcome Rejected; TCS ID → counts as a login ("manual"); RAG override → wins (section 9).
  - Owner "Call centre" with a date → call-centre Follow-up on that date; owner "Done" → closes the open actions.
  - **Later date wins** against a branch answer: tracker follow-up date (or the day it was saved, if it has no date)
    against the branch's response date.

**Different**
- 25.1 Tracker outcome **"Logged in"** has no effect by itself: only a TCS ID makes the entry logged in (11.1's
  manual route). The form still lets the master owner save "Logged in" with no TCS ID, which looks done but changes
  nothing. Likewise "Rejected" can be saved without a reject reason. Suggested: require the TCS ID for "Logged in"
  and the reason for "Rejected".
- 25.2 Tracker outcome **"Return to branch – green channel"** does nothing of its own. A green-channel R2/R3 is
  returned from the "Green channel" page; on the tracker the outcome only works indirectly, because a tracker row
  with a later date overrides the branch's rejection. It should either return the lead the same way as the Green
  channel page or not be offered.

**Aham**
- 25.3 Three points the document leaves open: (a) when the tracker's date and the branch's response date are the
  same day, the app lets the tracker win; (b) a correct number given after the 15 days is refused (the BM sees "Numbers
  can be corrected within 15 days of the entry"); (c) a corrected number goes straight back to calling without the
  selection checks, so if the new number is already being called on another entry or was spoken to in the last 30
  days it is called again (our assumption, in the list). See also 3.2: a branch with no BM and no RTM has nobody to
  correct numbers.

## Step 26: Section 14, settings
**Done**
- Every value in the table is a setting, in one record per company (`services/settings.py`, stored in
  `company_settings`, checked on save), with the document's values as defaults: Takeoff start 22 Sep 2026, first
  call date 24 Sep 2026, repeat / spoken-to window 30, max unanswered (Lead) 9, tries per day Lead 2 / DSA-CP 1
  (plus "up to 3 recorded per day"), first-attempt target 1 day, non-lead action window 14, correct-number window
  15, SO Amber window 15, branch-date threshold 14, daily target 10 of which 5 Lead/Prospect, green channel ₹8 lakh
  (self-construction and improvement) and ₹15 lakh (purchase and plot + construction).
- Also settings: the present attendance codes, designation → role, the clock-ahead flag, the automatic run time,
  and the two [Aham to decide] switches (same-day calling, repeated TCS ID).
- Changed in HR & Admin → Settings by the system admin, without a code change; each save is in the audit log. The
  rules read the stored values (step 1).
- The 30-day window feeds two separate checks (repeat by the same SO; spoken to by anyone) that stay separate rules;
  the 9 applies to the Lead group only.

**Different**
- 26.2 **No effective dates.** A setting change applies at once and to the past as well: raising the daily target
  from 10 to 12 changes the shortfalls shown for past days, and changing an action window opens or closes existing
  actions the next time the entries are worked out. The audit log records who and when, not the old and new value
  (see 1.2). If Aham expects changes to apply only from a date, settings need an "effective from" date.

**Aham**
- 26.1 **The two 15-day settings.** "Correct customer number window" decides how long the SO's action stays open;
  "SO Amber correction window" decides how long the BM / RTM may enter the right number. Both are 15, so they agree
  today; if only one is changed, the action could stay open after corrections are refused (or the reverse). The SO
  Amber window is used only for number corrections; other Amber statuses ("knows SO", "answers missing") have no
  window (see 17.1). Ask Aham what the SO Amber window is meant to cover, or merge the two settings.
- 26.3 **Turnaround target "1 day"** is counted in calendar days (first try date minus entry date). Entries are
  called from the next day and never on Sundays, so a Saturday entry first called on Monday counts as late. Calendar
  days or working days?
- See 1.1: some screen texts still state these numbers instead of reading the settings.

## Step 27: Section 15, what the Excel set-up gets wrong (acceptance checklist)
| # | Check | Result |
|---|---|---|
| 1 | Can an SO change or type the Emp ID? | **Pass.** No such field; the server takes it from the signed-in user and ignores anything sent (step 5) |
| 2 | Can an invalid mobile number be submitted? | **Pass.** Blocked on the phone and refused by the server (step 7) |
| 3 | Can an SO choose another branch? | **Pass.** Branch, region and spoke come from the roster (step 5) |
| 4 | Can one form hold several people? | **Pass.** One entry per Submit; "Save & add another" for the next person (step 5) |
| 5 | Can "Five Lakhs" / "5 lakh" go into the loan amount? | **Partly.** Stored as a whole number of rupees on the server; "Five Lakhs" is refused, but **"5 lakh" is saved as ₹5** because the box keeps only the digits (bug 16.1) |
| 6 | Is a number in the 2nd or 3rd place of the contact cell found? | **Pass.** Every number is split, cleaned and matched; repeated TCS IDs follow the setting (step 23, tested) |
| 7 | Do lists show records beyond a fixed limit? | **Partly.** See 27.1 |

**Done (point 7)**
- The entries list, users list and audit log are paged by the server with filters and a total count; the Takeoff
  export has no cap; the caller's list has no cap; the compliance export refuses a range over 62 days with a message
  (not silently).

**Missing**
- 27.1 **Silent caps.** Several lists stop at a fixed number of rows with nothing on screen to say more exist, which
  is the Excel problem the document asks the app not to copy:
  - Field map: the newest 3,000 entries of the period (a month for the whole company would be cut).
  - Open actions (SO / branch): 1,000.
  - Call-centre actions, follow-up tracker list, monitor review queues: 500 each.
  - The SO's "My entries" in the app: the newest 200 (about 20 working days at 10 a day); older entries cannot be
    seen on the phone.
  Fix: page these lists (or "load more") and show "showing X of Y" when a cap is reached.

## Step 28: Annex A, branches by region
Seed file `database/seed/aham_org.json`, loaded by `python -m app.seed`; managed afterwards in HR & Admin →
Organization. Compared with Annex A by a script (2026-11-01).

| Check | Result |
|---|---|
| Every Annex A branch exists | **Pass.** 35 of 35, none missing, none extra |
| Each branch is in its Annex A region | **Pass.** All 35 match (7 regions: AP & TG, Chennai 1, Chennai 2, Karnataka, RoTN C, RoTN T, RoTN U) |
| SO branch and region from the roster | **Pass** (step 5); the region always follows the branch |
| Caller allocation by branch | **Pass.** One caller per branch per day (step 12); nothing assigns a caller to a whole region |
| Madurai / Krishnagiri confirmed by Aham | **Open.** Placed as Annex A lists them (RoTN U / RoTN C); the Organization page shows the question; moving a branch is a data change, not code |
| No duplicate or conflicting mappings | **Pass** in the seed (no repeated name or code); see 28.1 for what the database allows later |

Regions and branches each have an active / inactive status; a branch can sit in an optional cluster (RTM).

**Different**
- 28.1 The database refuses two branches with the same **code** but not with the same **name**. The roster upload
  finds a branch by name or code, so a second branch with an existing name (typed by mistake in Organization)
  would make roster rows ambiguous. Suggested: names unique per company as well.

**Aham / data**
- 28.2 The full names of RoTN C, RoTN T and RoTN U (the app shows the short names, which can be edited), the real
  branch codes (the seed uses placeholders), and the Madurai and Krishnagiri answers (4.2).

## Step 29: Annex B, status list
Compared by a script that reads Annex B from the document and looks for each value in `services/sankalp/rules.py`
(2026-11-01).

| Group | In Annex B | In the code, same text |
|---|---|---|
| Selection | 6 | 6 |
| Calling | 5 | 5 |
| Lead logic | 10 | 10 |
| DSA/CP | 5 | 5 |
| Lead outcome | 3 | 3 |
| **Total** | **29** | **29** |

**Done**
- All 29 values exist character for character (including the en dash "–"), as named constants used by the rules,
  the screens' filters (sent by `/sankalp/meta`) and the tests. "Allocate" (5.3, check 7) is the one extra selection
  result.
- Nobody types a status: selection results are set by the daily run, statuses by the call rules, lead outcomes by
  the login rules. The caller picks answers and outcomes from fixed lists that the server checks.
- The groups are kept apart on the entry: selection result, status, lead outcome, and the RAG on top.

**Different (small)**
- The values are controlled by the server code, not by the database: the status columns are plain text without a
  database check, so a hand-made database change could store another value. Not a problem in use; a database
  check could be added if Aham's IT wants one.
