# Testing

| Suite | Command | Covers |
|---|---|---|
| Backend (64) | `cd backend && pytest` (needs the db container) | auth/refresh rotation, RBAC, tenant isolation, schema validation, idempotent + concurrent submissions, resumable uploads, checksum/type validation, photo vs submission time/location separation, outbox retry, SSE ticket/scoping, rate limit, body limits, filters/pagination, dashboard/audit, production secret check; type-of-person management and history safety, review reasons, send-back / approve / reopen, corrections as new revisions, unique references, analytics definitions and periods, map markers, geocoding selection |
| Web (28) | `cd admin-web && npm test` | no form-builder UI/routes, dashboard, role gate, login validation, SSE refetch + reconnect, server-side filters/paging, detail-page metadata separation, format helpers; Settings (type of person, reasons), review panel, performance page, field map fallback and marker styling |
| Mobile (27) + 3 integration | `cd mobile && flutter test` (Flutter 3.47.7); `flutter test integration_test/...` on an emulator | schema validation; sync engine: success, offline backoff, idempotent retry after timeout, resume, conflict, 401, max attempts; repeatable-entries widget test; upgrade of a version-1 local database to version 2 keeps every report, draft and photo. `flutter analyze`: no issues |
| Load | `python tests/perf/perf.py --admin-email ... --admin-password ...` | concurrent logins/submissions/uploads, SSE propagation, idempotent repeats, list latency |

Scenario coverage (backend tests): A online submission, C interrupted upload, D repeated request, E time/location
separation, F permissions.

### Scenario B (offline end to end) — run on an Android emulator, passed
`mobile/integration_test/offline_scenario_test.dart` drives the real app UI on a Pixel 6 / Android 15 emulator (WHPX)
against the real backend: sign in -> form downloads -> API becomes unreachable -> fill the report offline -> photo at
GPS position A -> GPS moves to B -> Submit -> "saved offline" (not accepted) -> app closed and reopened (session,
submission and photo file all survive) -> API reachable again -> sync starts by itself and the server acknowledges.
Result of the passing run (server-side, from PostgreSQL): 1 logical submission, status accepted, photo uploaded
(checksum-verified); photo captured 09:08:03Z at 14.4426,79.9865 (5 m, gps); submitted 09:08:24Z at
16.5062,80.6480; server received 09:08:52Z; accepted 12 s after the API came back (2 attempts).
Run it: start the emulator + backend, then `flutter test integration_test/offline_scenario_test.dart -d emulator-5554
--dart-define=E2E_EMAIL=... --dart-define=E2E_PASSWORD=...`. The test prints `E2E:` markers; a host driver must
(1) grant CAMERA/LOCATION via `adb shell pm grant` after install, (2) feed `adb emu geo fix` every ~0.5 s (position A
before `E2E:PHOTO_TAKEN`, B after), (3) stop the backend at `E2E:WAIT_OFFLINE`, (4) start it at `E2E:WAIT_ONLINE`.
**What this does not cover:** the system camera app (replaced by a fake image picker returning a real JPEG);
real-device GPS; Android background (WorkManager) delivery; process kill (the restart closes the app's providers and
database and reopens them, it does not kill the OS process); iOS. Observed emulator limitation: with Wi-Fi *and* mobile
data switched off, the emulator's Google Play Services fused-location provider returned no fix (status `timeout`,
no coordinates stored, Submit not blocked), so the passing run uses "API unreachable, radios on". Earlier runs that cut
the radios also passed the offline/restart/auto-sync parts (sync resumed ~14 s after Wi-Fi returned).
Bugs this found and fixed: a sync controller crash if torn down mid-sync (`providers.dart`); `workmanager` 0.5.x
did not compile on current Android tooling (now ^0.10).
**Re-run on the current build (2026-10-20; form v4, local database v2, Type of person dropdown, 1 photo):** passed.
Photo captured 19:02:04 (UTC+05:30) at 14.4426,79.9865; Submit pressed 19:02:25 at 16.5062,80.6480 (state not
"accepted" while offline, survived the restart); accepted by the server 13 s after the API returned (2 attempts). The
admin report page shows the two events, with their times and positions, separately.

### Review and correction scenario (emulator, passed)
`mobile/integration_test/correction_scenario_test.dart`: the agent submits with the managed Type of person and two photos
-> the test, acting as the reviewer, sends it back through the admin API with a reason and a flag -> the phone shows
"Needs correction" and the feedback after a sync -> the agent edits, adds a photo and resubmits -> the server holds
revision 2 of the same reference, revision 1 stays as history and the reviewer's decision is kept. Extra arguments:
`--dart-define=E2E_ADMIN_EMAIL=... --dart-define=E2E_ADMIN_PASSWORD=...`. Same limits as Scenario B (fake camera,
emulated GPS, no WorkManager, no iOS).

### Admin web pages checked in a real browser (2026-10-20)
Signed in against the running backend: Dashboard, Performance (period, branch table, type-of-person breakdown),
Field map (no browser key, so the location list fallback), Settings (type of person, rejection reasons) and a report
detail page with the review panel all load with no console errors and the right data. **Not checked:** the real Google
map (needs the browser key), clicking through every review action in the browser (covered by the web tests and the
backend API tests), narrow/phone-width layouts.

## Measured load results (2026-10-16)
Environment: Windows 11 laptop, Docker Desktop, single uvicorn process, Postgres 16 in a container, client on the
same machine, 20 agents x 10 submissions (every 4th with a ~5 KB photo).

| Metric | p50 | p95 | p99 |
|---|---|---|---|
| Submit API, excluding photo upload | 124 ms | 222 ms | 249 ms |
| Photo upload (initiate + PUT + complete) | 311 ms | 550 ms | 558 ms |
| Ack to SSE event at admin client | 260 ms | 555 ms | 572 ms |
| `GET /submissions` (page of 25, ~400 rows) | 11 ms | 16 ms | 19 ms |

200/200 submissions accepted; 200/200 SSE events received; 20 concurrent same-key posts gave 1 submission and no
errors; backend about 80 MB RAM and under 1% CPU when idle afterwards. 20 concurrent logins took about 0.8 s in total
(argon2 CPU cost). These meet the stated targets (submit p95 under 1 s, propagation p95 under 2 s) **in this
environment only**: not measured with real network latency, large photos, many SSE clients, or a production-sized
database. The load test found and fixed one bug (a 500 on concurrent same-key submissions).
