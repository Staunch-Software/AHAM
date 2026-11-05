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
| 13.2 | Wrong number within 15 days: called again with a fresh count of tries | `handoff.correct_number` | Entry page: Correct number |
| 13.3 | Follow-up tracker; later date wins against a branch answer | `handoff.save_tracker`, `engine.derive` | Entry page: Follow-up tracker |
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
- Every call produces a row status (section 8 literally): a later unanswered follow-up call on a validated lead puts
  it back "In retry" until the customer is reached again.
- A call-centre action (callback, take case forward, follow-up) stays open 14 days from its date.

Added with the feature-review fixes (2026-11-01, `docs/feature-review.md`), each still for Aham to confirm:
- A DSA/CP contact who asks to be called back gets that date as one more calling day (7.1 vs "one day only").
- A DSA/CP contact who said he needs a home loan himself is called as a lead from then on (Lead questions, 2 tries a
  day, up to 9 unanswered); the conversion holds on later calls unless the caller answers "No".
- A lead that an earlier call validated and a later call finds "Not looking for a loan" keeps the status Red (8.1)
  but its RAG is NA: section 9's "a lost lead is NA, not Red". (19.1, which calls change the status at all, is
  still open.)
- "Validated on" is the date of the first call that validated the entry.
- The lead card's handling branch works the lead: its BM (or its RBH where it has no BM) answers it and its missed
  dates count there; the SO's branch keeps the credit, compliance and dashboards.
- The RBH corrects a customer number where the branch has neither a BM nor an RTM (as it answers leads there).
- A branch date that the 14-day rule gave to the call centre is not a branch's missed date.
- The tracker's "Logged in" needs the TCS ID and "Rejected" needs the reason; "Return to branch – green channel"
  returns the waiting R2/R3 exactly like the Green channel page.
- Settings apply from the day they are saved; a report for an earlier day (daily compliance) uses the settings of
  that day.
- Adding or removing a holiday moves the count date of entries already made that day.
- An entry made while the phone's clock was behind its last contact with the server (set back by hand) is flagged
  "check the time", like a clock that is ahead.

## [Aham to decide]: settings with today's behaviour as default
| Open point | Setting / place | Default |
|---|---|---|
| Same-day calling (5.2) | Settings: *Allow same-day calling* | Off |
| Duplicate TCS IDs in the register (11.1) | Settings: *A TCS ID repeated in the login register* | The latest row wins |
| Madurai: RoTN U or RoTN C (section 3) | Organization: move the branch | RoTN U (call-centre allocation) |
| Krishnagiri: RoTN C or Chennai (Annex A) | Organization: move the branch | RoTN C |
| Payout rule (section 10) | not built: the app produces the flags only | — |
| Old-process verdicts (8.4) | not built | — |

## [Legacy] rules not built
UNRES placeholder IDs (the Emp ID always comes from the login), swapping a name/number entered the wrong way round
(the app validates the number), the old-process single verdicts. The legacy "Date" field of the Google Forms is dropped:
the Submit time rules.
