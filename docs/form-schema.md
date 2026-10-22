# Form schema and the Field Meeting Report

## Schema format
JSON, versioned, pure data (no code or expressions). Validated on the server before a version is stored
(`backend/app/services/form_schema.py`) and again by the mobile app before it renders one
(`mobile/lib/features/dynamic_form_renderer/form_schema.dart`); the two implementations are kept in step and unit-tested.

```jsonc
{ "form_id": "field_meeting_report", "version": 2, "title": "...",
  "sections": [ { "id": "meeting_details", "title": "...", "repeatable": true, "min_items": 1, "max_items": 10,
    "fields": [ { "key": "contact_name", "label": "...", "type": "text", "required": true,
                  "validation": { "max_length": 200 },                      // min_length max_length min max pattern
                  "visible_if": { "field": "x", "op": "eq", "value": "y" },  // eq | neq | in | not_empty (same entry)
                  "options": [ { "value": "a", "label": "A" } ],             // dropdown / radio / multi_select
                  "allow_gallery": false } ] } ] }                           // photo fields: gallery only if true
```
Field types: text, multiline_text, integer, decimal, date, time, datetime, dropdown, radio, checkbox, multi_select,
phone, email, photo, photos, location, readonly_text, heading. Anything else is rejected. Keys are lower_snake_case and
stable: they identify a field across versions and in validation errors. Versions are immutable and must increase; older
versions stay deliverable and accepted (offline drafts) until a version is retired.

Answers: `{ "<section id>": {…} }` or, for repeatable sections, `{ "<section id>": [ {…}, {…} ] }`. A photo field holds a
photo UUID; the photo itself (file, checksum, capture time and GPS) is a separate record.

## Publishing (internal only)
There is no form builder in the web app. Versions are published by `python -m app.seed` (reads
`database/seed/field_meeting_report.v*.json`) or by `POST /api/v1/internal/forms` with `X-Internal-Key` (disabled unless
`INTERNAL_API_KEY` is set; not in OpenAPI).

## Field Meeting Report — source: "Aham Sankalp AP & TG" workbook
The workbook (`Form Responses 1`) has 36 header columns, no response rows, no dropdown options and no descriptions.
Column-by-column decisions are in `database/seed/field_meeting_report.mapping.json` (checked by a backend test so it
cannot drift from the form). Summary:

| Original | Handling |
|---|---|
| Timestamp | System: device submit time + server received/accepted times |
| Select you branch name ? | System: branch from the agent's assignment (branch master) |
| Enter your employee id ? | System: the signed-in agent; never typed or trusted from the client |
| Category, name, WhatsApp, date, description, Keka photo time (and their 2nd/3rd copies) | **One repeatable "Meeting Details" section** (v2: `contact_category`, `contact_name`, `contact_whatsapp`, `meeting_date`, `meeting_description`, `keka_photo_time`, `meeting_photo`); up to 10 meetings |
| Photo evidence | New `meeting_photo` field; its capture time and GPS are recorded automatically and kept separate from `keka_photo_time`, which is the time the agent enters from Keka |

(v2 added `keka_photo_time` to v1; v3 removes it again, see below.) Required: category, name, date, description. Optional: WhatsApp, Keka time, photo.
(Required/optional is **assumed** — the export does not say.)

### v3: automatic time/location, several photos
- **No typed times.** `keka_photo_time` is gone. The app records, by itself and at the moment it happens, the time and
  GPS fix (with accuracy and status) of **each photo** and of **the Submit press**; the admin web shows them as
  "Photo capture event" and "Submission event". Meeting **Date** is pre-filled with today (`"default": "today"`,
  editable).
- **Several photos per meeting:** `meeting_photos` (type `photos`, camera only, `validation.max` = 5 photos; for photo
  lists `min`/`max` are counts). Each photo keeps its own capture time and location.
- Older versions (v1, v2) remain valid for offline drafts made earlier.

### v4 (current): managed "Type of person" dropdown
`contact_category` is now a **dropdown** (`"options_source": "person_types"`) labelled "Type of person". Its options are not
stored in the form: they are the company's managed list (Settings > Type of person in the admin web), injected when the
form is downloaded, so editing the list needs no new form version. Answers store the option's **stable id**; the server also
saves the label as it was at submission, so renaming "Dealer" to "Retail Dealer" never rewrites old reports. Whether the
field is required and whether "Other" (a custom value, stored as `other:<text>`) is allowed are also company settings.
Reports made on v1-v3 keep their free-text category. See `docs/workflow-features.md`.


## Not implemented — left out by decision
Decision (product owner): *if unsure, leave those fields out.* So the current form (v4) and the items below stay out
until someone confirms them; nothing else needs to change for the form to be usable. They were left out rather than guessed:
1. **"What type of CP?" (4 columns: S, V, X, AD).** What does CP mean, what are its values, and does each meeting have
   one? In the sheet the CP questions sit between the meeting blocks, so their relationship to the meetings is unclear.
2. **"Column 19", "Column 20", "Column 22" (T, U, W).** Untitled questions in the original form. What are they?
3. **Nine branch-named columns (Nellore … Siddipet).** All empty; they look like follow-up questions shown per branch.
   What does each ask? (The branch list itself belongs in the branch master: Nellore, Guntur, Vijayawada, Rajahmundry,
   Anakapalli, Visakhapatnam, LB Nagar, Warangal, Siddipet — seeded from `database/seed/branches.json` with **placeholder codes** (NLR, GNT, VJA, RJY, AKP, VSKP, LBN, WGL, SDPT); replace them with the real codes in the admin web under Organization > Branches.)
4. **"What category is the person met ? 2" (AJ).** The category question appears twice but there are three
   name/phone/date blocks. The form asks a type of person per meeting; confirm that is right.
5. **Starting list of person types** (seeded: Customer, Dealer, Distributor, Supplier, Business Partner; admins can change it)
   and whether any other field should be required.
6. **Maximum meetings per report** (3 blocks exist in the workbook; the form allows 10).

When these are answered: edit the mapping file, add `field_meeting_report.v5.json`, run `python -m app.seed`.
