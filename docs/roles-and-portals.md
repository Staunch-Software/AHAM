# Roles, portals and data scope (RBAC)

Defined in one place: `backend/app/security/rbac.py`. Every API checks a **permission** (`require_perm`) and lists are
cut to the user's **scope** (`backend/app/services/scope.py`). A role belongs to exactly one portal; signing in at another
portal is refused with a message naming the right one (the password is checked first, so the portal is never revealed
to someone without it).

## Designation hierarchy (low to high)
Sales Officer → Branch Manager → Cluster Manager (RTM, not every branch has one) → Region Manager (RBH) →
Product Manager → Business Manager. Sales Officer designations RO, RM and ABM are kept as the roster designation.

| Role | Portal | Sees | Can also |
|---|---|---|---|
| Sales Officer | Mobile app | own entries | make entries |
| Branch Manager | Management | own branch (plus any extra branches assigned) | answer leads (12.4), correct numbers, correct the SO if the branch has no cluster, IRR report |
| Cluster Manager (RTM) | Management | branches of the cluster | correct numbers and SOs, IRR report |
| Region Manager (RBH) | Management | branches of the region | answer leads of branches with no BM; correct numbers where a branch has neither BM nor RTM; IRR report |
| Product Manager | Management | all | export compliance, IRR report |
| Business Manager | Management | all | export compliance, IRR report |
| Caller | Call centre | entries on their list | record calls, lead card |
| Master owner | Call centre | all | daily run, caller of the day, assign work, tracker, RAG override, manual TCS ID, green channel, login register |
| Sankalp monitor (HR) | HR & Admin | all | roster / attendance / holidays / bulk entries (and the employee roster page), category reviews, correct SOs, compliance and Takeoff exports, audit log |
| MIS (Credit / Ops) | HR & Admin | — | upload the login register; IRR: upload the Disbursement Register, fix exceptions, settings, report |
| System admin | HR & Admin | all (read) | users and roles, organization, settings, CP sub-types, uploads (bulk entries too), audit log, IRR (all of it) |

Every table on every page has **Export: CSV · Excel** (a paged list exports all its rows). The IRR module
(`docs/irr-module.md`) uses two permissions of its own: `irr.view` (BM, RTM, RBH, Product and Business Manager, MIS,
System admin, each in their own scope) and `irr.manage` (MIS, System admin).

Scope is by **branch**: an entry belongs to the branch of its SO (from the roster) and its region follows the branch, so
moving a branch to another region moves its entries' scope with it.

## Authentication (JWT)
- `POST /api/v1/auth/login` with `identifier` (Emp ID or email), `password` and `portal`. Returns a 15-minute HS256
  access token (claims: user, company, role, portal) and a 30-day refresh token (stored only as a hash, single-use,
  tied to the portal).
- Every request re-checks that the user is active and that the role still belongs to the token's portal, so a role
  change or deactivation takes effect at once; changing a role or deactivating also ends all sessions.
- New accounts (created in Users & roles, or by the roster upload with *temporary passwords*) must replace the
  temporary password at the first sign-in; until then every API except `/auth/me` and `/auth/change-password`
  answers `403 password_change_required`.
- Roster accounts without a temporary password cannot sign in at all until HR issues one.
- After the roster exit date the account can no longer sign in.
- The web keeps one session per portal (so two portals can be open in two tabs); the app keeps its refresh token in
  the phone's secure storage and the access token in memory only.
