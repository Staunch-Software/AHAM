# Sankalp business logic in the code

Source: *Sankalp app: business logic, from SO entry to lead ID* (version 1, 28 Oct 2026). Section numbers below are
that document's. The rules are pure functions in `backend/app/services/sankalp/engine.py` (one test per rule table in
`backend/tests/test_engine_rules.py`); the database side is `ops.py` (runs, calls, recompute) and `handoff.py` (branch
answers, corrections, tracker, login register). Status texts are kept exactly as in the document (Annex B, with its en
dash) in `rules.py`.

## Where each section lives
| Section | What | Code | Screen |
|---|---|---|---|
| 3 | Roster, branch–region map, attendance, holidays, callers, login register | `api/v1/imports.py`, `api/v1/org.py`, `api/v1/reference.py` | HR & Admin: Uploads, Organization, Settings |
| 4.1–4.2 | One entry per person met; Emp ID, branch and spoke from the roster; Entry ID `<EmpID>-<YYYYMMDD>-<HHMMSS>` (IST, truncated) | `api/v1/entries.py`, `services/calendar.py`; phone: `mobile/src/lib/rules.ts` | App: New entry |
| 4.3 | Phone cleaning and validation; submission blocked until valid | `services/phone.py` (same cases in `mobile/__tests__/rules.test.ts`) | App: New entry |
| 4.4 | Count date: Sunday or holiday → next working day | `services/calendar.py` | |
| 4.5 | Daily compliance: 10 entries per present SO, 5 Lead/Prospect, "AB" when absent, joiners N/A, exits excluded | `api/v1/reports.py` (`/compliance`) | Daily compliance (Management, HR) |
| 5 | Daily selection: call group, fresh conditions, the seven checks in order | `engine.selection_decision`, `ops.run_selection` | Call centre: Daily run |
| 6 | Caller of the day per branch, retries to the first caller, unreturned work offered again, PRIORITY first | `ops.allocate`, `api/v1/calling.py` | Daily run, My calls |
| 7 | Attempts (10 slots, 9 outcomes, 2 tries a day / 9 unanswered for leads, 1 try one day for DSA/CP), the questions, the lead card | `ops.record_attempt`, `schemas.py`, `ops.save_lead_card` | Call screen |
| 8 | Row status: lead logic (in order), DSA/CP, not connected | `engine.lead_logic`, `dsa_logic`, `row_status` | |
| 9 | RAG, master-owner override wins | `engine.rag_for`; override in the tracker | everywhere |
| 10 | Customer validated, first validation for the number, validated on, Sankalp success | `engine.derive`, `ops.recompute_phone_group`, `recompute_tcs_group` | HR: Takeoff export |
| 11 | Login register: every number of the contact cell, duplicate TCS ID rule, manual TCS ID, lead outcome, one success per TCS ID | `handoff.import_register`, `ops.best_login` | Uploads (MIS / master owner), tracker |
| 12.1–12.3 | SO / branch and call-centre actions and how long they stay open | `engine.derive` | Open actions, Call-centre actions |
| 12.4 | Branch answer codes, 14-day rule, green channel (head-office check), RBH answers where there is no BM, missed dates | `handoff.answer_lead`, `review_green_channel`, `api/v1/branch.py` | Leads to answer, Green channel |
| 13.1 | Wrong SO: Entry ID kept, SO/branch/region replaced | `handoff.correct_so` | Entry page: Correct SO |
| 13.2 | Wrong number while its action is open (15 days from the call): called again with a fresh count of tries | `handoff.correct_number` | Entry page: Correct number |
| 13.3 | Follow-up tracker; against a branch answer only a later follow-up date wins (ties: the branch) | `handoff.save_tracker`, `engine.derive` | Entry page: Follow-up tracker |
| 14 | Settings | `services/settings.py` (stored per company) | HR & Admin: Settings |

Everything an entry "is" (status, RAG, actions, lead outcome, flags) is **derived** from its calls, branch answers,
tracker row and the login register by `ops.recompute()`, which runs after every event. A daily job
(`workers/daily.py`) closes actions whose window has passed and, if a time is set in Settings, starts the selection run.

## Decisions made with Aham (this build)
- Separate login portals in one web app: Management, Call centre, HR & Admin; Sales Officers use the mobile app.
  See `docs/roles-and-portals.md`.
- The call-centre flow replaces the old report review (approve / send back). Photos stay on entries as evidence.
- RTM = Cluster Manager, RBH = Region Manager. Where a branch has no cluster, its BM does the RTM's corrections.
- The six categories are fixed; the editable list is the **CP sub-type** (asked only for a Contact Point).

## Assumptions (please confirm)
- "Genuine" Lead/Prospect (target 5 a day) counts Lead and Prospect entries that are not a repeat entry by the same SO
  and not a duplicate entry.
- The green-channel "reviewer at head office" is the master owner.
- A corrected customer number goes straight back to calling (to the first caller, or the branch's caller of the day);
  the selection checks are not run again for the new number.
- Two entries by one SO in the same second: the second Entry ID gets `-2`.
- An entry whose phone clock was more than 5 minutes ahead of the server is flagged "check the time" for the monitor.
- Only a call that gives a status sets the entry's status (Takeoff master): connected, invalid number, wrong person,
  refused to talk, or a DSA/CP closed. An unanswered try or a callback request on a lead gives none, so a validated
  lead stays validated when a later follow-up call is not answered. Until a call gives a status the entry is "In
  retry" (or "Discarded – 9 unanswered" after the last allowed try).
- On the call-centre side only a callback runs out (14 days after its date); a case taken forward and a follow-up stay
  until done (Takeoff master).

Added with the feature-review fixes (2026-11-01, `docs/feature-review.md`), each still for Aham to confirm:
- A DSA/CP gets one try: a callback request closes it ("Closed – no answer"), as in the Takeoff master.
- A DSA/CP contact who said he needs a home loan himself is called as a lead from then on (Lead questions, 2 tries a
  day, up to 9 unanswered); the conversion holds on later calls unless the caller answers "No".
- A lead that an earlier call validated and a later call finds "Not looking for a loan" keeps the status Red (8.1)
  but its RAG is NA: section 9's "a lost lead is NA, not Red". (19.1, which calls change the status at all, is
  still open.)
- "Validated on" is the date of the latest call that gave a status (Takeoff master).
- The lead card's handling branch works the lead: its BM (or its RBH where it has no BM) answers it and its missed
  dates count there; the SO's branch keeps the credit, compliance and dashboards.
- The RBH corrects a customer number where the branch has neither a BM nor an RTM (as it answers leads there).
- A branch date that the 14-day rule gave to the call centre is not a branch's missed date.
- The tracker's "Logged in" needs the TCS ID and "Rejected" needs the reason; "Return to branch – green channel"
  returns the waiting R2/R3 exactly like the Green channel page (and, as the Takeoff master, can be given without one).
- Settings apply from the day they are saved; a report for an earlier day (daily compliance) uses the settings of
  that day.
- Adding or removing a holiday moves the count date of entries already made that day.
- An entry made while the phone's clock was behind its last contact with the server (set back by hand) is flagged
  "check the time", like a clock that is ahead.

Added with the second review and the client's demo feedback (2026-11-09), each still for Aham to confirm:
- **One current status** per entry on every screen and file: the login outcome when there is one, else the latest
  call's status (with "2 unanswered" or "call back on …" for In retry), else the selection result. Earlier statuses
  stay in the entry's History.
- **A converted lead is not entered again:** an entry is refused (by any SO, on the phone while typing and on the
  server) when an earlier entry for the same mobile number has a TCS lead ID or a login. A validated lead without a
  lead ID is not a converted lead.
- **Bulk entries** (HR & Admin → Uploads, monitor and admin only): the same checks as the phone; the Entry ID comes
  from the date and time met; no GPS ("bulk upload"); a row already uploaded is not added twice.
- **A follow-up sent to the call centre** (branch date more than 14 days out, or the tracker) is done once the call
  centre has called on or after its date; the lead then goes back to the branch. If it runs out unworked, the lead
  keeps its branch action (a lead action never expires).
- **PRIORITY** (branch code 3, immediate call-back), a reopen due today and a **corrected number** go on today's
  list at once, to the caller who first handled the entry (or the branch's caller of the day).
- A lead's planned 2 tries take it off the list; up to 3 can be recorded, so it stays reachable under "Called today"
  for a third try that day. A corrected number's tries start afresh (today's tries on the old number do not count).
- The "repeat entry by same SO" check compares every earlier entry with that number, including entries never
  selected (dated before the first call date, or Existing Customer / Applicant).
- A Sankalp success tie on the same date goes to the lower Entry ID (11.3 as written). Only logged-in entries
  compete (Takeoff master).
- The call outcome "RNR" is written "Rang, no answer"; the RAG "RNR" is shown as "No answer".

Aligned with Aham's Takeoff master workbook (Excel, Oct 2026) on 2026-11-11, where it was silent in the document or
differed from it:
- The login register accepts the MIS file's own column names ("Applicant Contact No (Customer)", "Product Type").
- Status: only a call that gives one sets it (see above); a validated lead stays validated after an unanswered call.
- Follow-up tracker: Action type and Reject reason are the master's fixed lists. Owner = Branch gives the branch the
  action type ("Branch follow-up (mail sent)" when none) on the follow-up date, kept until the tracker changes;
  Owner = Call centre puts a follow-up on the call centre's list (on the follow-up date, or now); Owner = Done closes.
- A green-channel R2/R3 sent back to the branch (Green channel page or tracker) gives the branch "Log in under green
  channel".
- Call screen: Timeline, Income, Documents, Next step and Purpose are asked only for a loan (not LAP, BT + LAP or "Not
  looking for a loan"); Own contribution only for Home purchase, Self-construction, Plot + construction.
- "Spoken to within 30 days" means fewer than 30 days before the run date.
- A DSA/CP callback request closes it (see above).
- A call-centre follow-up goes to the tracker's caller, else the caller who created the lead ID, else the first caller.
  Retries and PRIORITY go to the first caller only.
- Reopened for calling (branch code 3, or the tracker's "Reopen for calling"): the entry is "In retry" from the reopen
  date (the branch's answer, or the tracker's follow-up date, else the day it was saved), with that date as its
  callback, until a call on or after it gives a status (or the tries run out). Branch code 3 and a reopen with the
  master owner's immediate call-back are PRIORITY; a tracker reopen alone is a normal retry. An immediate call-back on
  its own puts only a not-yet-called entry first. It goes on today's list only once its date has come.
- "Validated on" is the date of the latest call that gave a status.
- Take case forward and call-centre follow-ups do not expire; callbacks do (14 days).
- A login validates an entry ("Customer validated") only when it is the Sankalp success for that TCS ID (and not LAP,
  not a repeat). An entry validated on a call stays validated.

Second pass against the Takeoff master (2026-11-11):
- Sankalp success: the earliest **logged-in** entry per TCS ID (an earlier entry that did not log in no longer blocks it).
- A TCS ID typed on the tracker overrides the login register.
- "Login on or before entry date" closes the entry like Logged in and Rejected: no actions, RAG NA, no retries or
  PRIORITY. A register row without a login date counts as one.
- The login register matches a contact on its last 10 digits when the whole number is not valid (RIGHT(number, 10)).
- Tracker vs branch answer: the tracker applies only when its follow-up date is after the branch's response date; a
  tie, or a tracker row without a follow-up date, leaves the branch answer in force. The day a tracker row was saved
  is the company's local (IST) date.
- A lead action given on the tracker makes the entry a lead whatever the tracker's owner.
- "Correct customer number" is open for 15 days from the call that found the wrong number; the BM / RTM can correct
  it while that action is open.
- A Next date can be given on any call that does not connect; the callback date is the latest one. No callback action
  while the tracker gives the entry to an owner (branch, call centre, done).
- A call's Next date runs from tomorrow up to 30 working days ahead (Sundays and holidays not counted), never a Sunday.
- The lead card's handling branch applies once the lead has a lead ID.
- Call-centre report: "First try on time" is counted over validated entries. The dashboard shows the Sankalp lead
  conversion by region (validated leads, logged in, rejected, open, login %).
Kept as the document says (the Excel differs): a LAP login never validates (11.3); a lost lead is NA, not Red (9);
the repeat check uses the SO now on the entry, not the Emp ID in the Entry ID.

## [Aham to decide]: settings with today's behaviour as default
| Open point | Setting / place | Default |
|---|---|---|
| Same-day calling (5.2) | Settings: *Allow same-day calling* | Off |
| Duplicate TCS IDs in the register (11.1) | Settings: *A TCS ID repeated in the login register* | The latest row wins |
| An SO with no attendance row (3, 4.5) | Settings: *A Sales Officer with no attendance row that day* | Counted as present ("not marked") |
| Madurai: RoTN U or RoTN C (section 3) | Organization: move the branch | RoTN U (call-centre allocation) |
| Krishnagiri: RoTN C or Chennai (Annex A) | Organization: move the branch | RoTN C |
| Payout rule (section 10) | not built: the app produces the flags only | — |
| Old-process verdicts (8.4) | not built | — |

## [Legacy] rules not built
UNRES placeholder IDs (the Emp ID always comes from the login), swapping a name/number entered the wrong way round
(the app validates the number), the old-process single verdicts. The legacy "Date" field of the Google Forms is dropped:
the Submit time rules.
