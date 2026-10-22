# Security notes

**Implemented and tested:** argon2id password hashing (off the event loop); short-lived access JWT + rotating
single-use refresh tokens (only the hash is stored); deactivation takes effect immediately; role checks on every
endpoint; company isolation on every query (cross-tenant records return 404); agent record ownership; signed
5-minute photo URLs (no public files, path-traversal-safe storage keys); checksum/type/size validation on uploads;
thumbnails re-encoded without EXIF; login-failure rate limit (5 per 15 min per IP+email, in-process); request body size
limits; SSE tickets (60 s, single purpose, company-scoped); internal form API behind a separate key and hidden from
OpenAPI; refusal to start non-development environments with weak secrets; audit log for admin changes.

**Dependency checks** (run in CI): `pip-audit`, `npm audit --omit=dev`. At the last run the findings were fixed by
upgrading FastAPI/Starlette, Pillow, PyJWT, python-multipart, pytest, axios and React Router; web production
dependencies report 0 vulnerabilities. `pip-audit` on the pinned `requirements.txt` reports no known vulnerabilities (re-run after the upgrade).

**Third-party disclosure:** with `GEOCODER=nominatim|google` the coordinates of agents' photos and submissions are sent
to OpenStreetMap / Google for place names; set `GEOCODER=none` to disable.

**Not done / needs a decision:** encryption at rest for mobile SQLite and photos; refresh-token reuse detection (a
replayed rotated token is rejected but does not revoke the whole family); shared rate limiter for multi-instance;
retention policy for photos and location data; password reset flow; MFA for admins; login limiter keys on the
connecting IP, so behind a proxy configure trusted forwarded headers.
