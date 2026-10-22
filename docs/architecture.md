# Architecture

Modular monolith: one FastAPI process, one PostgreSQL database, photos on local disk behind `StorageBackend`.

```
Flutter agent app --REST--> FastAPI --> PostgreSQL (authoritative)
  SQLite/Drift outbox         |  \-- transactional_outbox --> outbox worker --> in-process hub --SSE--> React admin
  photos in app storage       \-- StorageBackend (local filesystem now; S3 later)
```

## Key flows
- **Submit (mobile):** validate, stamp device time, bounded GPS wait, then one SQLite transaction (submission +
  outbox state + photo attach + draft delete). The UI says "Saved offline"; the sync engine delivers later.
- **Sync:** per submission, upload photos (resumable, SHA-256 verified), then `POST /submissions` with the same
  idempotency key on every retry. A record counts as accepted only after the server acknowledges it.
- **Server accept:** validate user/branch/form version/answers/photos, insert submission + outbox row in one
  transaction (same-key requests are serialized by a Postgres advisory lock), return the receipt.
- **Place names:** a background worker reverse-geocodes photo/submission coordinates (OpenStreetMap or Google, see
  deployment.md), stores the name next to the coordinates and never alters them.
- **Live update:** the outbox worker publishes to SSE subscribers of that company only; the web client treats the
  event as a signal and refetches from the REST API (also on every reconnect).

## Known limits (deliberate, documented)
- **Single API process.** The SSE hub and login rate limiter are in-process. Run one uvicorn worker (the Docker image
  does). To scale out, replace `Hub` with a shared bus (Postgres LISTEN/NOTIFY or Redis) and the limiter with a shared one.
- **Local-disk photo storage** needs a persistent volume and backups (see backup-restore.md). Implement
  `StorageBackend` for S3 to move off it; callers do not change.
- **Device times, GPS and EXIF are device reports, not proof.** Server receive/accept times are authoritative.
- Mobile SQLite and photo files are not encrypted at rest (OS sandbox and device encryption only).
- Form definitions are managed only via `database/seed` scripts or the key-protected `/api/v1/internal/forms`
  endpoint (disabled unless `INTERNAL_API_KEY` is set, hidden from OpenAPI). There is no form-builder UI.
- Open items: Excel columns 19/20/22 and the CP-type fields are not mapped (meaning unconfirmed); contact category
  is free text until the allowed values are provided.
