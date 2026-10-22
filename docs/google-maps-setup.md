# Google Maps: place names and the field map

FieldSync uses Google in two different places, and **they need two different API keys**. Google restricts a key by how
it is used, and a key that works in a browser does not work from a server (and the other way round).

| What | Where it runs | API to enable | Key restriction that works |
|---|---|---|---|
| **Place names** ("12-3-4, VRC Road, Nellore") | the backend server | **Geocoding API** | API restriction = Geocoding API. Application restriction = **None** (development) or **IP addresses** = your server's public IP (production). *Not* "Websites" or "Android apps". |
| **Field map** (markers on a map) | the admin's browser | **Maps JavaScript API** | API restriction = Maps JavaScript API. Application restriction = **Websites (HTTP referrers)**: `http://localhost:5173/*` for development, `https://your-domain/*` for production. |

> **Why place names did not work for you:** the key in `.env` was rejected by Google with
> `REQUEST_DENIED: This IP, site or mobile application is not authorized to use this API key`. The key has an
> *application restriction* (websites or an app) that does not match a server calling from Docker. Fix: edit that key,
> set *Application restrictions* to **None** (and keep *API restrictions* = Geocoding API), or create a separate server key.
> Use a separate key for the map (below).

**What "exact" can mean:** Google returns the nearest known address to the GPS point. A phone's GPS is typically accurate
to 5-20 m (worse indoors or between tall buildings), so the name can be the neighbouring building or the street. The admin
pages always show the accuracy (±m); treat the name as a convenience and the coordinates as the evidence.

## 1. Create the project and enable billing (once)
1. https://console.cloud.google.com -> create a project (for example `fieldsync`).
2. Link a billing account (a card is required even though Google gives a free monthly allowance; check the current
   Geocoding and Maps JavaScript pricing).
3. Billing -> Budgets & alerts: create a monthly budget with email alerts. APIs & Services -> each API -> Quotas: set a
   daily limit you are comfortable with.

## 2. Server key: place names
1. APIs & Services -> Library -> **Geocoding API** -> Enable.
2. Credentials -> Create credentials -> API key. Open it and set *API restrictions* = Geocoding API only, and
   *Application restrictions* as in the table. (A Docker/home connection has no stable IP, so use **None** in development
   and the server's IP in production.)
3. Put it in `C:\Staunch\fieldsync\.env` (production: `.env.prod`). Never paste it in chat, email or code:
   ```
   GEOCODER=google
   GOOGLE_MAPS_API_KEY=your-server-key
   ```
4. Restart the backend: `docker compose up -d --build`.
5. Locations that failed earlier (or were named by OpenStreetMap) keep their old state. Queue them again:
   ```
   docker compose exec backend python -m app.regeocode
   ```
   The background worker redoes them; existing names stay visible until replaced.

## 3. Browser key: the field map
1. APIs & Services -> Library -> **Maps JavaScript API** -> Enable.
2. Create a second API key. *API restrictions* = Maps JavaScript API only. *Application restrictions* = Websites, with
   `http://localhost:5173/*` (development). Add your real address, for example `https://app.yourcompany.com/*`, for production.
   This key is visible in the browser by design; the website restriction is what protects it.
3. Put it in `C:\Staunch\fieldsync\admin-web\.env.local` (this file is git-ignored):
   ```
   VITE_GOOGLE_MAPS_API_KEY=your-browser-key
   ```
   Restart the admin web (`npm.cmd run dev`). For a production build, set the same variable when running `npm run build`.
4. Open **Field map**. Without the key the page still lists every recorded location (with a Google Maps link each) and
   explains what is missing.

## Check it works
- **Place names:** submit a report with Location on, open it in the admin web: a name appears above the coordinates within
  seconds. If not, `docker compose logs backend` shows `geocoding failed`; the usual causes are API not enabled, billing not
  linked, or the key's application restriction (see the box at the top).
- **Map:** markers appear, coloured by review status; clicking one shows the agent, branch, meeting date, status, accuracy and
  place, with "Open report". A grey "This page can't load Google Maps correctly" overlay means Google rejected the key
  (API not enabled, billing, or the website restriction does not include the address you opened).

## What has and has not been verified
- **Place names (verified 2026-10-20):** after the server key's application restriction was set to None, Google answered
  `OK` and the worker filled in "16/183, Anna Salai, ..., Saidapet, Chennai" for the existing reports. Google sometimes
  returns a first candidate written as "267F+X4V, <area>" (a plus code); the ranking skips those for a readable address.
- **Map (verified 2026-10-20):** with the browser key in `admin-web/.env.local`, the field map renders the Google map and
  the status-coloured markers in the admin web on `localhost:5173`. Clicking markers, the photo-location layer and the
  branch layer were not exercised in the browser by me (their logic is covered by the web tests).
- **Not verified:** the production Content-Security-Policy in `infrastructure/deployment/Caddyfile` allows Google Maps
  (following Google's guide) but has not been tried with a real key on a real HTTPS domain.
- **Keys in logs:** the backend used to log the full Google request URL (with the key). Logging now replaces any `key=`
  value with `REDACTED`, and a Google refusal is logged with its reason (for example `REQUEST_DENIED: ...`).
- The web tests ignore `admin-web/.env.local` (`vite.config.ts` pins the key to empty for tests).
