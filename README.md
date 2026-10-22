# FieldSync

Field operations platform: React admin web, Flutter agent app (Android/iOS), FastAPI backend, PostgreSQL.
Photos are stored on the local filesystem behind a replaceable storage interface (S3 can be added later).

## Status
| Area | State |
|---|---|
| Backend (auth, RBAC, org APIs, form engine, submissions, local photo storage, outbox + SSE, type of person, review workflow, analytics, map data, place names) | Done. 64 tests pass; Docker image builds and runs as non-root |
| Admin web (dashboard, org, employees, submissions + review panel, performance, field map, reports, settings, audit, live SSE) | Done. 28 tests + build pass; 0 production npm vulnerabilities. AHAM-branded design (docs/design-system.md). Pages opened in a real browser against the backend, including the Google field map |
| Flutter app | Builds and passes: `flutter analyze` clean, 27 tests (incl. local-database upgrade), Android debug APK builds (Flutter 3.47.7). **Offline end-to-end and review/correction scenarios passed on an Android emulator** against the real backend. Not verified: system camera UI, real-device GPS, WorkManager background runs, iOS (never built). See docs/testing.md, docs/mobile-setup.md |
| Load test | Measured locally (docs/testing.md): submit p95 218 ms, ack-to-dashboard p95 546 ms, 200/200 accepted |
| Production stack | `docker-compose.prod.yml` (Caddy HTTPS + admin web + API proxy, backend, Postgres), `app.bootstrap` for the first admin, `backup.sh`. Verified locally over HTTP (see docs/deployment.md); real HTTPS/Let's Encrypt not yet exercised |
| CI, security docs | Written (`.github/workflows/ci.yml`, docs/). CI workflow not run on GitHub |
| Google (place names, field map) | Working: server key (Geocoding API) names the places; browser key (Maps JavaScript API) shows the field map. Two separate keys, see docs/google-maps-setup.md. Production domain/CSP not yet tried |
| Not done | Real-device run of the new build (camera/GPS/background), iOS build, S3 storage backend, answers on the unmapped workbook columns (CP type, Column 19/20/22, branch-named columns; see docs/form-schema.md), push notifications to agents, limiting a type of person to particular forms/branches, multi-instance scaling, performance re-measured after the review/reference changes |

Docs: docs/design-system.md (AHAM branding, tokens, where styles live), docs/form-schema.md (workbook mapping + open questions), docs/workflow-features.md (type of person, review, performance, map), docs/google-maps-setup.md, docs/architecture.md, deployment.md, backup-restore.md, security.md, testing.md, mobile-setup.md.

## Run (development)
```bash
cp .env.example .env
docker compose up -d db
cd backend
python -m venv .venv && .venv/Scripts/pip install -r requirements.txt   # Linux/macOS: .venv/bin/pip
.venv/Scripts/alembic upgrade head
.venv/Scripts/python -m app.seed
.venv/Scripts/uvicorn app.main:app --reload     # http://localhost:8000/docs
.venv/Scripts/python -m pytest                  # needs the db container running
```
