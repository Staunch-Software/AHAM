# Type of person, review workflow, performance analytics, field map

## 1. Type of person (managed dropdown)
- **Admin:** Settings > Type of person. Add, rename, activate/deactivate, reorder; choose whether agents *must* pick one and
  whether "Other" (custom text) is allowed. Duplicate **active** names are refused (case-insensitive).
- **Agents** get the active options on their next successful sync and keep the last downloaded list offline.
- **History is safe:** reports store the option's stable id *and* the label at submission. Renaming or deactivating an option
  never changes old reports. A report made offline with a since-deactivated option is still accepted.
- Each meeting's type is also stored as a row used by filters (Submissions, Field map) and the analytics breakdown.
- Not implemented: limiting an option to particular forms or branches (the list is company-wide).

## 2. Review and correction workflow
```
Agent submits (revision 1) -> reviewer: Approve | Send back (reason + message + optional flags)
   -> agent sees "Needs correction" + feedback after the next sync -> corrects -> resubmits (revision 2, same reference)
   -> back in the review queue; revision 1 stays in the history
```
- **Reference** `FS-<year>-<n>` per company, unchanged across revisions. Revisions are new records; nothing is overwritten.
- **Reasons** are configurable (Settings > Rejection reasons); the message is pre-filled and editable; "Other" requires text.
  A missing GPS location is not a rejection reason unless your process makes it one.
- **Flags** point the agent at a specific meeting or photo field; the phone highlights them in the correction form.
- **Approval is final** for that version. To review it again an admin uses **Reopen** with a written reason (recorded).
  Only the newest revision can be reviewed; earlier ones are read-only.
- **Safeguards on the server:** a correction must name the revision it corrects; if the report changed meanwhile, or is not
  waiting for correction, the server refuses it with an explanation (`report_changed` / `report_not_rejected`); the
  idempotency key makes a repeated send harmless; photos already uploaded are reused, photos of other reports are refused.
- **Offline:** the agent can correct without internet; the correction is saved on the phone and counts as resubmitted only
  when the server acknowledges it.
- **Notification:** the reviewer's dashboard and queue update live when a correction arrives. The agent sees the decision on
  the Home screen, History and the report after the next sync (there are no push notifications yet).
- **Review history** (every decision across all revisions, who, when, reason, message) is shown on the report and kept.

## 3. Branch and agent performance (admin > Performance)
Periods: today, this week (Mon-Sun), this month, custom, in the company time zone (default Asia/Kolkata).

| Metric | Definition |
|---|---|
| Reports | Reports **first submitted** in the period (revision 1). A corrected resubmission is not counted again. |
| Pending / needs correction / approved | Current state of those reports (their newest revision). |
| Rejection rate | rejections / (approvals + rejections) among **decisions made in the period**. Pending reports never count. Shown as "-" when nothing was reviewed. |
| Target achievement | reports / target x 100, for **week and month** views and only where a target is set. Targets are optional and set inline (weekly or monthly, per branch or per agent). |
| Trend | reports vs the previous equivalent period; "-" when the previous period had none. |
| Active / assigned agents | agents who reported / active agents assigned to the branch. |

Branch rows drill down to agents; every number links to the Submissions list filtered the same way. A low agent count can
also mean reports still waiting to sync on the phone, so the page says so. Not implemented: per-organization scoping of
what an admin can see (an admin sees the whole company).

## 4. Field map (admin > Field map)
Markers are the GPS positions **recorded when Submit was pressed** (optionally also each photo's position). This is *not*
live tracking; the app never follows agents. Filters: date range, branch, agent, form, review status, type of person,
earlier versions. Colour = review status; **hollow markers = accuracy over 100 m or unknown**; clicking a marker shows agent,
branch, meeting date, status, accuracy, place, and a link to the report; a circle shows the accuracy radius. Branch locations
(from Organization > Branches coordinates) are drawn separately. Reports without GPS are counted but cannot be placed.
The map needs a Google browser key (see google-maps-setup.md); without it the page lists all locations with map links.
Not implemented: comparing a recorded location with an "intended meeting location" (the forms do not capture one).
