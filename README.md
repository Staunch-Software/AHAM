# AHAM Sankalp

Field-to-lead platform for AHAM Housing Finance. Sales Officers record every person they meet in the **AHAM Sankalp app**
(React Native, works offline); the **call centre** calls them, classifies the lead and fills the lead card; the **branch**
works the lead to login; the **MIS login register** closes the loop and produces the incentive flags. Built on FastAPI
and PostgreSQL, with three web portals (React) and photos on local disk behind a replaceable storage interface.

The business rules follow *Sankalp app: business logic, from SO entry to lead ID* (v1, 28 Oct 2026): see
**[docs/sankalp-rules.md](docs/sankalp-rules.md)** for where each section lives, the assumptions made and the open
[Aham to decide] points (all settings, defaulting to today's behaviour).

## Status
| Area | State |
|---|---|
| Backend: JWT auth per portal, RBAC (11 roles, branch/cluster/region scope), roster/attendance/holiday/login-register uploads, entries, daily selection and allocation, calls and classification, RAG, lead card, actions, branch answers and green channel, corrections, follow-up tracker, login matching, incentive flags, compliance, settings | Done. 201 tests pass (84 of them check the rule tables one row at a time, 25 the feature-review fixes); Docker image builds and runs |
| Web: Management, Call-centre and HR & Admin portals | Done. 32 tests + build pass. All three portals checked in a browser against the running backend, with the demo account of each role (docs/testing.md) |
| Mobile: AHAM Sankalp (Expo SDK 58) | Built: offline entries with the Submit time and GPS, Entry ID on the phone, photos with their own time and GPS, resumable idempotent sync, background sync. 25 unit tests and the type check pass (expo-doctor: six newer Expo patch releases available). **Emulator run passed** (release APK): an entry made with the API down kept its Submit time, Entry ID and GPS when it synced 2.5 minutes later from another place (docs/testing.md). **Version 1.1.0** (with the feature-review fixes) built 2026-11-01 as `mobile/dist/aham-sankalp-1.1.0.apk` for the API at `http://192.168.1.14:8000` (this PC on its Wi-Fi); installed over 1.0.0 on the emulator: entries kept, still signed in, Sunday count-date note, version and server shown on the Me screen. **Version 1.2.0** (`mobile/dist/aham-sankalp-1.2.0.apk`): the server address can be changed in the app (sign-in screen or Me → Server → Change), because the PC's Wi-Fi address changes |
| Not done | Real-phone run of the new app, iOS, the payout rule (Aham/HR to confirm), S3 storage, push notifications, load test re-measured for the new API, dropping the old report tables. **To ask Aham:** whether to import the entries and calls made since Takeoff start (22 Sep) from the Excel workbooks. The business-logic document does not ask for it, but the 30-day repeat and spoken-to checks, "known contact", first validation per number and one success per TCS ID all look back at earlier entries |

Feature review against the business-logic document, item by item, with what was fixed and what Aham must answer:
**[docs/feature-review.md](docs/feature-review.md)**. Client demo, section by section, with a week of realistic demo
data (`python -m app.demo_data`): **[docs/client-demo.md](docs/client-demo.md)**.

Docs: [getting-started](docs/getting-started.md) (set up and run), [sankalp-rules](docs/sankalp-rules.md),
[roles-and-portals](docs/roles-and-portals.md), [architecture](docs/architecture.md), [mobile-setup](docs/mobile-setup.md),
[testing](docs/testing.md), [deployment](docs/deployment.md), [backup-restore](docs/backup-restore.md),
[security](docs/security.md), [design-system](docs/design-system.md), [google-maps-setup](docs/google-maps-setup.md).

## Run (development)
Full guide for a new developer: **[docs/getting-started.md](docs/getting-started.md)**. The short version:
```bash
cp .env.example .env                        # then edit the secrets and SEED_PASSWORD (PowerShell: Copy-Item)
docker compose up -d --build                # PostgreSQL + API; migrations run automatically
docker compose exec backend python -m app.seed   # AHAM regions, branches and one demo account per role (once)
cd admin-web && npm ci && npm run dev       # http://localhost:5173: choose a portal (API docs: http://localhost:8000/docs)
```
The mobile app: `cd mobile && npm ci && npx expo run:android` (Android emulator), or build an APK for a phone as in
docs/mobile-setup.md.
