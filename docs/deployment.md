# Deployment

Production topology (`docker-compose.prod.yml`): **Caddy** (automatic HTTPS, serves the admin web, proxies `/api`)
-> **backend** (FastAPI, one process) -> **PostgreSQL**. Only Caddy publishes ports (80/443). Photos live on a Docker
volume (local-disk storage; S3 is a later swap, see architecture.md).

## 1. Prerequisites
- A Linux host with Docker + Compose, a DNS name pointing at it, ports 80 and 443 open.
- Secrets: `openssl rand -hex 32` for each of `JWT_SECRET` and `FILE_URL_SECRET`, and a strong `POSTGRES_PASSWORD`.
  The backend **refuses to start** with `APP_ENV=production` if the two secrets are default or shorter than 32
  characters, and the compose file refuses to start if any required value is missing.

## 2. Configure and start
```bash
cp .env.production.example .env.prod      # fill in SITE_ADDRESS, PUBLIC_ORIGIN and the three secrets (never commit it)
docker compose -f docker-compose.prod.yml --env-file .env.prod up -d --build
```
`alembic upgrade head` runs automatically when the backend starts. Caddy obtains the Let's Encrypt certificate for
`SITE_ADDRESS` on first request. The stack uses its own compose project name (`fieldsync-prod`), so it never shares
volumes with the development stack.

## 3. Create the first company and administrator (no demo data)
```bash
docker compose -f docker-compose.prod.yml --env-file .env.prod exec -e BOOTSTRAP_ADMIN_PASSWORD='<12+ chars>' backend \
  python -m app.bootstrap --company-name "Acme Ltd" --company-code acme \
  --admin-name "Jane Admin" --admin-email jane@acme.com --with-branches
```
Publishes the form versions from `database/seed/` and, with `--with-branches`, the nine branches with **placeholder
codes** (edit them in the admin web, Organization > Branches). It refuses to run if the company code or email exists.
Do **not** run `python -m app.seed` in production (it creates demo users). Then sign in at `https://<SITE_ADDRESS>`,
create employees/agents and assign their branch.

## 3b. Place names for locations
The admin web shows a place name (for example "VRC Road, Vaddipalem, Nellore, Andhra Pradesh") beside every photo and
submission location, plus an "Open in Google Maps" link. Names are looked up by the **server** in the background after a
report is accepted (never during Submit), stored once, and never replace the coordinates.
- `GEOCODER=nominatim` (default): free OpenStreetMap lookups. **Light use only**: at most 1 request/second (enforced),
  results cached, and OpenStreetMap's usage policy requires `GEOCODER_USER_AGENT` to contain a real contact email
  (production refuses to start without one). Not suitable for heavy production traffic.
- `GEOCODER=google` with `GOOGLE_MAPS_API_KEY`: Google Geocoding API (needs a Google Cloud project with billing), the
  better choice for exact addresses in India. Setup steps: google-maps-setup.md. The code path is unit-tested against
  sample responses only; it has not been run against Google with a real key.
- `GEOCODER=none`: no place names (the admin page then shows coordinates only).
Privacy: the coordinates of agents' photos and submissions are sent to the chosen provider (OpenStreetMap or Google).
Mention this in your privacy notice. After 3 failed lookups a location stays without a name (coordinates unaffected).

## 4. Mobile app
Build with the production API URL: `flutter build apk --release --dart-define=API_BASE_URL=https://<SITE_ADDRESS>`
(release builds are HTTPS-only; plain HTTP is allowed in debug builds only). Signing and iOS: see mobile-setup.md.

## 5. Operations
- **Backups:** `infrastructure/deployment/backup.sh [dir]` (database dump, then photo archive). Restore: backup-restore.md.
- **Update:** `git pull` (or copy the new release), then rerun the `up -d --build` command. Migrations run on start.
- **New form version (internal):** keep the JSON in `database/seed/` for the record, then publish it with the internal
  API: set `INTERNAL_API_KEY` in `.env.prod`, restart the backend, `POST /api/v1/internal/forms` with header
  `X-Internal-Key` and body `{"company_code": "...", "schema": <the JSON>}` (version must exceed the latest), then
  remove the key and restart. The endpoint is hidden from OpenAPI and returns 404 while no key is set.
- **Health:** `/health`, `/ready` (also proxied). JSON request logs on stdout with `correlation_id` and `duration_ms`;
  alert on `/ready` failures, 5xx rate, and a growing count of `transactional_outbox` rows with `processed_at IS NULL`.
- **One backend replica only** (in-process SSE hub and login limiter; see architecture.md).

## What was verified (local run of this exact stack, 2026-10-16, HTTP-only on localhost)
Build and start of all three images; bootstrap command (and its refusal on a second run); SPA deep links; security
headers (HSTS, CSP, nosniff, frame deny); admin login and dashboard in a browser under the CSP with no console errors;
SSE streaming through Caddy (30/30 events); 2 MB request rejected (413); login rate limit holds even when the client
spoofs `X-Forwarded-For`; internal API 404 while unkeyed; backup script + restore with identical counts; compose
refuses to start without secrets.
**Not verified:** real Let's Encrypt issuance and HTTP/2-3 (needs a public DNS name), behaviour under real internet
latency, and restoring the photo archive onto a fresh volume (the archive was only listed).
