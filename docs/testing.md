# Testing

| Suite | Command | Covers |
|---|---|---|
| Backend (258) | `cd backend && pytest` (needs the db container; `TEST_DB_NAME=…` runs a second suite side by side) | **Client feedback and second review** (`test_client_feedback.py`, 25): the Takeoff master's rules (MIS column names, status only from calls that give one, tracker lists and branch actions, questions by loan need, 30-day boundary, follow-up caller, reopen until reached), one current status, exact upload errors, Excel export of any table, bulk entries, a converted lead refused, a corrected DSA/CP number called again, a third try the same day, a follow-up done once called and never left without an action, code 3 on the list at once, repeats against unselected entries, the unmarked-attendance setting. **IRR module** (`test_irr_calc.py`, `test_irr_api.py`, 23): the formula (plain average tenure) and worked example, cumulative MTD/YTD, year to date = sum of its months, rows counted (tranches twice), HL and NHL never together, the financial-year boundary, excluded and exception rows, re-upload without double counting, exact row errors, scope, exports. **Feature-review fixes** (`test_review_fixes.py`, 27): one test per fixed item of `docs/feature-review.md`, plus "Copy yesterday" on a Monday, the "Last week" period, and a branch caller changed after the run. **Rule tables, one row each** (`test_engine_rules.py`, 89): fresh conditions (5.2), the seven selection checks in order (5.3), lead logic in order (8.1), DSA/CP (8.2), not connected (8.3), RAG (9), actions and their windows (12.1–12.3), 14-day rule, green channel limits and head-office check, rejections, tracker vs branch answer (a later follow-up date wins, ties to the branch), reopen from its date, callback = latest Next date, login outcomes (no date, tracker TCS ID), LAP, repeat entries, Sankalp success ties, first validation, attempt limits. **Flows through the API** (`test_calling_flow.py`): entry → run → caller's list → tries → retry to the first caller → validated → lead card → branch answers → login register → flags and Takeoff export; selection rules with real entries; 9 unanswered and DSA/CP one-day rule; callbacks; number and SO corrections with their windows; RBH for a branch without BM; PRIORITY; category review; green channel; tracker (manual TCS ID, RAG override); register rules (several numbers, latest row wins, login before entry, LAP); compliance (present, AB, joiners, exits, scope); unassigned work. **Access** (`test_auth_rbac.py`): portal per role, Emp ID or email, wrong-portal message only after the right password, temporary password flow, role change ends sessions, exit date, SSE ticket is not an access token, permission matrix for every role, data scope for every level, company isolation. **Entries** (`test_entries.py`): identity from the roster, Entry ID from the device time, offline entry synced days later keeps its time and GPS, clock-ahead flag, Sunday/holiday count date, idempotent and concurrent retries, same-second suffix, validation, CP sub-type, photos. Uploads, settings, holidays, CP sub-types, place names |
| Web (37) | `cd admin-web && npm test` | call questions by loan need, one current status and labelled mobile numbers, IRR report and its upload errors, feature-review fixes (`review.test.tsx`: dashboard "Last week", amounts refused, Sunday dates, converted DSA/CP, PRIORITY reason and overdue, expired actions, audit old → new, who heads what, employee roster, a repeat daily run says "nothing new", a changed branch caller says how many new entries went to them), portal chooser, sign-in sends the portal and links to the right one, temporary password screen, menus per role (BM, Product Manager, MIS), menu links stay inside the portal from any page, refused page, one session per portal, live refresh on `entry.created`, classification preview (section 8 order), call screen (lead and DSA/CP questions, callback date, Next date range, lead card rule), lead conversion by region with its Total row, branch answer codes with their date, entries list, uploads "check first" |
| Mobile (25) | `cd mobile && npm test` (+ `npx tsc --noEmit`, `npx expo-doctor`) | server address as typed (an IP, IP:port or URL; anything else refused), count date (Sundays and holidays, as on the server), phone cleaning (same cases as the backend), Entry ID in IST and truncated, Keka time; sync engine with fakes: photos before the entry, byte-identical retry body, offline backoff and stop, resumable upload and offset correction, already-uploaded photos skipped, a refused entry does not block the next, signed-out stop without counting an attempt, backoff cap |

## Emulator run of the React Native app (2026-10-29, passed)
Release APK (Expo SDK 58, Hermes, R8) on the Android 15 emulator against the running backend, driven by a host script
(adb taps and text, `adb emu geo fix`, the API container stopped and started, PostgreSQL checked directly):
sign in as AHFL90001 → **API stopped** → New entry (Lead, name, mobile, description) at GPS point A (Vijayawada) →
Submit: the sheet showed Entry ID `AHFL90001-20261029-220326`, "Saved on this phone · sends automatically", GPS ±5 m,
and the header "1 waiting to send" → phone moved to point B (Nellore), 70 s wait, app force-stopped and reopened (entry
still waiting) → **API started** → the entry synced by itself.

| Check | Result |
|---|---|
| Entry ID on the phone = on the server | pass (`AHFL90001-20261029-220326`) |
| Server time = the Submit tap (16:33:26.779 UTC = 22:03:26 IST) | pass |
| Received 151 s later (after the API came back) | pass |
| Stored GPS = point A (16.506098, 80.647998), not B where the phone was when it synced | pass |
| Location status `obtained` | pass |
| "Saved on this phone" while offline; "All sent" once the server answered again | pass |

Found and fixed during these runs: the release build crashed at start (R8 removed WorkManager's Room database: keep
rules added in `app.json`); after opening offline, the app kept saying "Offline" when only the server had been down
(it now re-checks every 30 s); Windows path-length failures of the native build (see mobile-setup.md).
**Not covered:** the system camera (photos were not taken in the run; photo upload is covered by the sync-engine tests
and the backend upload tests), a real phone's GPS, background (WorkManager) delivery while the app is closed, iOS.

## Browser checks (2026-10-29)
Against the running backend with the seeded demo data and a small demo flow made through the API:
- **Management portal** as the Branch Manager: dashboard (today and this week, scoped to Vijayawada), leads to answer,
  an entry page with its device time ("synced 30 h later"), Google place name, call, answers, lead card and history.
- **Call-centre portal** as the Master owner: My calls (by caller), a connected call on the call screen (answers
  previewed as Validated, saved Validated/Green), the lead card with a Lead ID, daily run and caller per branch, runs
  history, call-centre actions, caller performance, green channel and tracker.
- **HR & Admin portal** as the monitor: dashboard (all regions), daily compliance (shortfall), queues, field map (Google
  tiles, RAG markers), uploads (roster and attendance only), Takeoff export, and the Users page refused. As MIS: only the
  login register upload. As the system admin: users & roles, organization, settings, audit log.

Found and fixed: the menu links were relative, so from any page other than the portal home they led to
`/<portal>/<page>/<page>` (React Router 7 resolves them below the current page); they are now absolute and a web test
covers it. A React key warning on the settings page. No other console errors. **Not checked in a browser:** phone-width
layouts.

## Load test
`tests/perf/perf.py` was ported to the new API (`/entries`, `/events/stream`, temporary passwords) but **not re-run**:
it creates PERF accounts and entries in the database it points at. The earlier measurements (2026-10-16, old report
API) no longer apply.
