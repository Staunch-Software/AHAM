# Getting started (for new developers)

How to get AHAM Sankalp running on your own machine after cloning the repository. Everything below was checked on
Windows 11 (PowerShell); macOS/Linux notes are given where the commands differ.

## What is in the repository
| Folder | What it is |
|---|---|
| `backend/` | FastAPI server, Alembic database migrations, backend tests |
| `admin-web/` | The three web portals (React, Vite, TypeScript, Tailwind): Management, Call centre, HR & Admin |
| `mobile/` | AHAM Sankalp app for Sales Officers (React Native, Expo SDK 58) |
| `archive/mobile-flutter/` | The previous Flutter app, kept for reference only (not built) |
| `database/seed/` | Regions and branches (Annex A) used by the seed and bootstrap commands |
| `infrastructure/` | Dockerfiles, production proxy config (Caddy), backup script |
| `docs/` | Business rules, roles, architecture, deployment, testing, security, design system |
| `tests/perf/` | Load-test script (written for the earlier report API; needs updating) |

How the pieces fit: a Sales Officer makes an entry on the phone (saved in SQLite, synced over HTTP); the server keeps it
in **PostgreSQL** and photos on disk; the call centre calls the person, the branch works the lead, and the login register
closes the loop. Read `docs/sankalp-rules.md` first, then `docs/roles-and-portals.md` and `docs/architecture.md`.

## 1. Install the tools
| Tool | Version we use | Needed for |
|---|---|---|
| Git | 2.4x+ | everything |
| **Docker Desktop** | 28.x (Compose v2) | the database and the API (required) |
| Node.js | 22 (npm 10) | web portals and mobile app |
| Python | 3.10 or 3.11 | only to run backend tests/tools outside Docker (the container uses 3.11) |
| JDK 17 + Android SDK | from Android Studio | building the Android app |

You do **not** need to install PostgreSQL. The project runs its own PostgreSQL 16 inside Docker (published on port
**5433**). If you already have PostgreSQL on your machine (port 5432), leave it alone; it is not used.

## 2. Backend and database (everyone)
```bash
git clone <repository-url>
cd fieldsync
```
Create your settings file from the template (the real `.env` is never committed):
```bash
# Windows PowerShell
Copy-Item .env.example .env
# macOS / Linux
cp .env.example .env
```
Open `.env` and change at least:
- `JWT_SECRET` and `FILE_URL_SECRET`: any long random text, e.g. `python -c "import secrets; print(secrets.token_urlsafe(48))"`
- `GEOCODER_USER_AGENT`: your real email (OpenStreetMap asks for a contact). Google place names: `docs/google-maps-setup.md`.
- `SEED_PASSWORD`: the password you want for all demo accounts (development only).

Start the database and the API (the first run downloads images and takes a few minutes):
```bash
docker compose up -d --build
```
The API container applies the database migrations every time it starts. Check it:
```bash
curl.exe http://localhost:8000/ready
```
(`curl` on macOS/Linux.) It must answer `200`. The API docs are at http://localhost:8000/docs.

**Create the demo data once:** the AHAM company, its 7 regions and their branches (placeholder codes), one cluster
("AP Coastal": Vijayawada, Guntur, Nellore), the CP sub-types and one account per role:
```bash
docker compose exec backend python -m app.seed
```
All demo accounts use `SEED_PASSWORD` from your `.env` (if it is empty, a random one is printed once). Sign in with the
Emp ID:

| Emp ID | Role | Where |
|---|---|---|
| AHFL90001, AHFL90002 | Sales Officer (Vijayawada, Guntur) | mobile app |
| AHFL90011 | Branch Manager, Vijayawada | Management portal |
| AHFL90021 | Cluster Manager (RTM), AP Coastal | Management portal |
| AHFL90031 | Region Manager (RBH), AP & TG | Management portal |
| AHFL90041 / AHFL90051 | Product Manager / Business Manager | Management portal |
| AHFL90061, AHFL90062 | Callers | Call-centre portal |
| AHFL90071 | Master owner | Call-centre portal |
| AHFL90081 | Sankalp monitor (HR) | HR & Admin portal |
| AHFL90091 | MIS | HR & Admin portal |
| AHFL90099 | System admin | HR & Admin portal |

These are development accounts only. A real deployment creates its first admin with `app.bootstrap` and everyone else
through the roster upload (`docs/deployment.md`).

## 3. Web portals
```bash
cd admin-web
npm ci
npm run dev
```
(In PowerShell, if scripts are blocked, use `npm.cmd`.) Open http://localhost:5173: it shows the three portals; each has its
own sign-in. The dev server forwards `/api` to `localhost:8000`, so the backend must be running.

**Optional, for the Google map:** create `admin-web/.env.local` with `VITE_GOOGLE_MAPS_API_KEY=your-own-browser-key`
(restricted to `http://localhost:5173/*`, see `docs/google-maps-setup.md`). Without it the Field map lists the locations.

**A typical day to try it:** as AHFL90001 make entries in the app (dated before today, or switch on *same-day calling* in
Settings); as AHFL90071 set the caller of the day for Vijayawada and press *Run*; as AHFL90061 open *My calls* and record
calls; as AHFL90011 answer the lead under *Leads to answer*; as AHFL90091 upload a login register (template on the
Uploads page) with the customer's number.

## 4. Mobile app (only if you work on it)
```bash
cd mobile
npm ci
npm test
```
Run it on the Android emulator (the emulator reaches your PC at `10.0.2.2`, the default address):
```bash
npx expo run:android
```
For a **real phone** on the same Wi-Fi as the PC: find the PC's IPv4 with `ipconfig`, allow port 8000 through the Windows
Firewall on a **Private** network once (administrator PowerShell:
`New-NetFirewallRule -DisplayName "Sankalp dev API" -Direction Inbound -Protocol TCP -LocalPort 8000 -Action Allow -Profile Private`),
then build an APK with that address baked in (`docs/mobile-setup.md`):
```bash
npx expo prebuild --platform android --clean
```
and in `mobile/android` (PowerShell): `$env:EXPO_PUBLIC_API_BASE_URL="http://<PC-IP>:8000"; .\gradlew.bat assembleRelease`.
Install `android/app/build/outputs/apk/release/app-release.apk` on the phone. The address changes when the network
changes: rebuild with the new one.

## 5. Running the tests
| Part | Commands | Expected |
|---|---|---|
| Backend (database container up) | `cd backend`, `python -m venv .venv`, activate it, `pip install -r requirements.txt`, `pytest` | 176 pass |
| Web portals | `cd admin-web`, `npm test`, `npm run build` | 18 pass, build succeeds |
| Mobile | `cd mobile`, `npm test`, `npx tsc --noEmit`, `npx expo-doctor` | 22 pass, no type errors, 20/20 checks |

Activate Python with `.venv\Scripts\activate` (Windows) or `source .venv/bin/activate`. The backend tests create and
migrate their own `fieldsync_test` database; your demo data is not touched. GitHub Actions runs the same checks
(`.github/workflows/ci.yml`).

## 6. Everyday work
| I want to... | Do this |
|---|---|
| start work | open Docker Desktop, `docker compose up -d`, then `npm run dev` in `admin-web` |
| see API logs | `docker compose logs -f backend` |
| apply a backend code change | `docker compose up -d --build backend` (no hot reload in the container) |
| run the API with hot reload | `docker compose stop backend`, then in `backend` with the venv active: `uvicorn app.main:app --reload` |
| change the database | edit the models, `cd backend`, `alembic revision --autogenerate -m "what changed"`, read the file, `alembic upgrade head`, commit it |
| change a business rule | `backend/app/services/sankalp/engine.py` (pure) with a row in `tests/test_engine_rules.py`; the phone's copies of the phone and Entry ID rules are in `mobile/src/lib/rules.ts` |
| change a window or target | HR & Admin > Settings (no code change) |
| change the phone's local database | `mobile/src/lib/db.ts`: raise `VERSION` and add a migration step |
| look at the database | `localhost`, port **5433**, database `fieldsync`, user `fieldsync`, password from your `.env` |
| wipe everything | `docker compose down -v`, then repeat section 2. **This deletes all local data and photos** |

**Where your local data lives:** in two Docker volumes, `fieldsync_pgdata` (PostgreSQL) and `fieldsync_storage` (photos,
`/data/storage` in the API container). They survive restarts and rebuilds; `docker compose down -v` removes them.

## 7. Rules for working in this repository
- **Never commit secrets.** `.env`, `admin-web/.env.local` and `.env.prod` are git-ignored. Use your own Google keys.
- Each developer has a **private local database**; demo data is not shared through git.
- Keep the repository private: it contains company branding and internal business rules.
- Do not edit `mobile/android/` by hand: it is generated from `mobile/app.json` (`npx expo prebuild`).
- Run the three test suites before opening a pull request.

## 8. When something goes wrong
| Symptom | Likely cause and fix |
|---|---|
| Web sign-in fails with "500" and the terminal shows `ECONNREFUSED` | The backend is not running: start Docker Desktop, `docker compose up -d` |
| "This account signs in at the … portal" | The role belongs to another portal: use the link shown |
| `port is already allocated` for 5433 or 8000 | Something else uses the port. Stop it, or change `POSTGRES_PORT` (and `DATABASE_URL`) |
| A database tool shows no Sankalp tables | You connected to your own PostgreSQL on 5432. Ours is on **5433** |
| The phone says it cannot reach the server | Not on the same network, an old address baked into the APK, the network set to Public, or the backend down. Open `http://<PC-IP>:8000/ready` in the phone's browser |
| Nobody gets calls after the run | No caller of the day for the branch: set it on *Daily run & allocation*, or assign the unassigned work there |
| Place names stay empty | The geocoder is not configured or the key is refused: `docs/google-maps-setup.md` |
| The first Android build is very slow | Normal: Gradle downloads its dependencies once |
