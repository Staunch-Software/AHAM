# Architecture

Modular monolith: one FastAPI process, one PostgreSQL database, photos on local disk behind `StorageBackend`.

```
AHAM Sankalp app (React Native) --REST--> FastAPI ------------> PostgreSQL (authoritative)
  SQLite: entries, photos, draft            |  \-- transactional_outbox --> outbox worker --> SSE --> web portals
  photos in app storage                     |  \-- daily worker (selection run, expiring actions)
                                            |  \-- geocode worker (place names)
Web portals (React): Management,            \-- StorageBackend (local filesystem now; S3 later)
  Call centre, HR & Admin --REST-->
```

## Key flows
- **Entry (phone):** validate (same phone rules as the server), stamp the device time at the Submit press, bounded GPS
  wait, then one SQLite transaction (entry + photos + draft removal). The Entry ID is computed on the phone the same way
  the server does.
- **Sync:** upload photos (resumable, SHA-256 verified), then `POST /entries` with the same idempotency key and body on
  every retry. A record counts as sent only after the server acknowledges it.
- **Server accept:** identity, branch and spoke from the signed-in SO's roster record; phone cleaned and validated;
  Entry ID and count date from the device time; insert entry + outbox row in one transaction (same-key requests are
  serialized by a Postgres advisory lock).
- **Calling:** the daily selection run decides each new entry (section 5) and fills the callers' lists (section 6).
  Every call, lead card, branch answer, tracker change, correction or login-register upload calls `recompute()`, which
  derives the entry's status, RAG, actions, lead outcome and incentive flags from the stored facts (pure rules in
  `services/sankalp/engine.py`). See `docs/sankalp-rules.md`.
- **Access:** JWT per portal, permissions per role, data scoped by branch, cluster or region
  (`docs/roles-and-portals.md`).
- **Place names:** a background worker reverse-geocodes entry and photo coordinates (OpenStreetMap or Google) and never
  alters the coordinates.
- **Live update:** the outbox worker publishes to SSE subscribers of that company; portals refetch on each event.

## Known limits (deliberate, documented)
- **Single API process.** The SSE hub, login rate limiter and daily worker are in-process. To scale out, move the hub to
  Postgres LISTEN/NOTIFY or Redis, the limiter to a shared store, and run the daily worker once.
- **Local-disk photo storage** needs a persistent volume and backups (backup-restore.md).
- **Device times and GPS are device reports, not proof.** Server receive times are kept beside them; an entry whose
  phone clock was ahead of the server is flagged for the monitor.
- The phone's SQLite database and photo files rely on the OS sandbox and device encryption.
- The tables of the retired form reports (`form_*`, `submission_*`, `review_*`, `report_targets`, `company_counters`)
  are still in the database, untouched and unused (test data from the earlier version). Drop them in a migration once
  nobody needs them.
