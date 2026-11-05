"""JWT auth, portals, temporary passwords, the permission matrix and data scope."""
from datetime import date, timedelta

import jwt
import pytest

from app.security.rbac import PERMISSIONS, ROLES
from tests.conftest import PASSWORD, PEOPLE, as_, auth, entry_body, login, make_entry, portal_for


async def test_login_by_emp_id_or_email_at_own_portal(client, tenant_a):
    by_code = await login(client, tenant_a["so1_code"].lower(), key="so1")  # Emp ID is case-insensitive
    by_mail = await login(client, tenant_a["so1_email"])
    for t in (by_code, by_mail):
        claims = jwt.decode(t["access_token"], options={"verify_signature": False})
        assert claims["portal"] == "mobile" and claims["role"] == "sales_officer"
        assert t["portal"] == "mobile" and t["must_change_password"] is False


@pytest.mark.parametrize("key", ["so1", "bm1", "caller1", "monitor"])
async def test_each_role_signs_in_only_at_its_portal(client, tenant_a, key):
    home = portal_for(key)
    for portal in ("mobile", "manage", "callcentre", "admin"):
        r = await client.post("/api/v1/auth/login", json={"identifier": tenant_a[f"{key}_email"], "password": PASSWORD,
                                                           "portal": portal})
        if portal == home:
            assert r.status_code == 200
        else:
            assert r.status_code == 403 and r.json()["detail"]["code"] == "wrong_portal"
            assert r.json()["detail"]["portal"] == home


async def test_wrong_password_never_reveals_the_portal(client, tenant_a):
    r = await client.post("/api/v1/auth/login", json={"identifier": tenant_a["so1_email"], "password": "nope",
                                                       "portal": "admin"})
    assert r.status_code == 401 and "portal" not in r.text


async def test_protected_requires_token_and_sse_ticket_is_not_a_token(client, tenant_a):
    assert (await client.get("/api/v1/branches")).status_code == 401
    assert (await client.get("/api/v1/branches", headers={"Authorization": "Bearer junk"})).status_code == 401
    bm = await as_(client, tenant_a, "bm1")
    ticket = (await client.post("/api/v1/events/ticket", headers=bm)).json()["ticket"]
    assert (await client.get("/api/v1/branches", headers={"Authorization": f"Bearer {ticket}"})).status_code == 401


async def test_refresh_rotates_and_logout_kills_it(client, tenant_a):
    t = await login(client, tenant_a["so1_email"])
    r = await client.post("/api/v1/auth/refresh", json={"refresh_token": t["refresh_token"]})
    assert r.status_code == 200 and r.json()["portal"] == "mobile"
    assert (await client.post("/api/v1/auth/refresh", json={"refresh_token": t["refresh_token"]})).status_code == 401
    await client.post("/api/v1/auth/logout", json={"refresh_token": r.json()["refresh_token"]})
    assert (await client.post("/api/v1/auth/refresh", json={"refresh_token": r.json()["refresh_token"]})).status_code == 401


async def test_role_moving_to_another_portal_ends_old_sessions(client, tenant_a):
    so = await login(client, tenant_a["so2_email"])
    admin = await as_(client, tenant_a, "admin")
    r = await client.patch(f"/api/v1/employees/{tenant_a['so2_id']}", headers=admin,
                           json={"role": "branch_manager"})
    assert r.status_code == 200
    assert (await client.get("/api/v1/auth/me", headers=auth(so))).status_code == 401  # access token: wrong portal now
    assert (await client.post("/api/v1/auth/refresh", json={"refresh_token": so["refresh_token"]})).status_code == 401
    assert (await login(client, tenant_a["so2_email"], portal="manage"))["role"] == "branch_manager"


async def test_temporary_password_must_be_replaced_first(client, tenant_a):
    admin = await as_(client, tenant_a, "admin")
    r = await client.post("/api/v1/employees", headers=admin, json={
        "employee_code": f"new{tenant_a['tag']}", "full_name": "New SO", "role": "sales_officer",
        "designation": "RO", "branch_id": str(tenant_a["b1"])})
    assert r.status_code == 201, r.text
    temp, code = r.json()["temporary_password"], r.json()["employee_code"]
    assert code == code.upper() and r.json()["must_change_password"] is True
    t = await login(client, code, temp, portal="mobile", key="x")
    assert t["must_change_password"] is True
    h = auth(t)
    assert (await client.get("/api/v1/auth/me", headers=h)).status_code == 200
    blocked = await client.post("/api/v1/entries", json=entry_body(), headers=h)
    assert blocked.status_code == 403 and blocked.json()["detail"]["code"] == "password_change_required"
    bad = await client.post("/api/v1/auth/change-password", headers=h, json={"current_password": "x", "new_password": "longenough1"})
    assert bad.status_code == 400
    ok = await client.post("/api/v1/auth/change-password", headers=h,
                           json={"current_password": temp, "new_password": "my-own-pass-1"})
    assert ok.status_code == 200 and ok.json()["must_change_password"] is False
    assert (await client.post("/api/v1/auth/refresh", json={"refresh_token": t["refresh_token"]})).status_code == 401
    assert (await client.post("/api/v1/entries", json=entry_body(), headers=auth(ok.json()))).status_code == 201
    # admin reset: a new temporary password, old sessions gone, change required again
    reset = await client.post(f"/api/v1/employees/{r.json()['id']}/temporary-password", headers=admin)
    assert reset.status_code == 200
    assert (await client.post("/api/v1/auth/refresh", json={"refresh_token": ok.json()["refresh_token"]})).status_code == 401
    again = await login(client, code, reset.json()["temporary_password"], portal="mobile", key="x")
    assert again["must_change_password"] is True


async def test_placement_is_required_by_role(client, tenant_a):
    admin = await as_(client, tenant_a, "admin")
    for role, field in (("sales_officer", "branch"), ("cluster_manager", "cluster"), ("region_manager", "region")):
        r = await client.post("/api/v1/employees", headers=admin, json={
            "employee_code": f"P{role[:3]}{tenant_a['tag']}", "full_name": "X", "role": role})
        assert r.status_code == 422 and field in r.json()["detail"]


async def test_exit_date_in_the_past_blocks_sign_in(client, tenant_a):
    admin = await as_(client, tenant_a, "admin")
    await client.patch(f"/api/v1/employees/{tenant_a['so3_id']}", headers=admin,
                       json={"exit_date": str(date.today() - timedelta(days=2))})
    r = await client.post("/api/v1/auth/login", json={"identifier": tenant_a["so3_email"], "password": PASSWORD,
                                                       "portal": "mobile"})
    assert r.status_code == 401


async def test_me_shows_role_portal_permissions_and_place(client, tenant_a):
    me = (await client.get("/api/v1/auth/me", headers=await as_(client, tenant_a, "so1"))).json()
    assert me["role_label"] == "Sales Officer" and me["portal"] == "mobile"
    assert me["branch_name"] == "Branch One" and me["cluster_name"] == "Cluster One" and me["region_name"] == "Region One"
    assert "entries.create" in me["permissions"]


# ---- permission matrix: every role against the endpoints that guard each permission ----
GUARDED = [
    ("users.manage", "POST", "/api/v1/employees/{so1_id}/temporary-password"),
    ("org.manage", "POST", "/api/v1/regions"),
    ("settings.manage", "PATCH", "/api/v1/settings"),
    ("cp_subtypes.manage", "GET", "/api/v1/cp-subtypes"),
    ("reference.import", "POST", "/api/v1/holidays"),
    ("entries.create", "POST", "/api/v1/entries"),
    ("entries.read", "GET", "/api/v1/entries"),
]


@pytest.mark.parametrize("perm,method,path", GUARDED)
async def test_permission_matrix(client, tenant_a, perm, method, path):
    url = path.format(**{k: v for k, v in tenant_a.items() if isinstance(v, (str,)) or k.endswith("_id")})
    for key, role, *_ in PEOPLE:
        if key in ("caller2", "so2", "so3", "bm3"):
            continue  # same role as another person in the list
        h = await as_(client, tenant_a, key)
        r = await client.request(method, url, headers=h, json={})
        allowed = perm in PERMISSIONS[role]
        assert (r.status_code != 403) == allowed, f"{role} {method} {url}: {r.status_code} {r.text[:120]}"


def test_every_role_has_a_portal_and_permissions():
    for key, r in ROLES.items():
        assert r.portal in ("mobile", "manage", "callcentre", "admin") and PERMISSIONS[key]
    # the designation hierarchy, low to high
    ladder = sorted((r.level, k) for k, r in ROLES.items() if r.level)
    assert [k for _, k in ladder] == ["sales_officer", "branch_manager", "cluster_manager", "region_manager",
                                      "product_manager", "business_manager"]


# ---- data scope ----
async def test_entry_scope_follows_the_hierarchy(client, tenant_a):
    t = tenant_a
    made = {k: (await make_entry(client, await as_(client, t, k)))["entry_code"] for k in ("so1", "so2", "so3")}

    async def seen(key):
        r = await client.get("/api/v1/entries?page_size=200", headers=await as_(client, t, key))
        assert r.status_code == 200, r.text
        return {i["entry_code"] for i in r.json()["items"]}

    assert await seen("so1") == {made["so1"]}  # own only
    assert await seen("bm1") == {made["so1"]}  # Branch One
    assert await seen("bm3") == {made["so3"]}
    assert await seen("cm1") == {made["so1"]}  # Cluster One = Branch One
    assert await seen("rm1") == {made["so1"], made["so2"]}  # Region One = Branch One + Two
    for key in ("pm", "bizm", "master", "monitor", "admin"):
        assert await seen(key) == set(made.values())
    assert await seen("caller1") == set()  # nothing allocated yet
    # a single entry outside the scope is a 404, not a 403
    other = (await client.get("/api/v1/entries", headers=await as_(client, t, "pm"))).json()["items"]
    so3_entry = next(i["id"] for i in other if i["entry_code"] == made["so3"])
    assert (await client.get(f"/api/v1/entries/{so3_entry}", headers=await as_(client, t, "bm1"))).status_code == 404


async def test_team_list_is_scoped(client, tenant_a):
    r = await client.get("/api/v1/employees?page_size=200", headers=await as_(client, tenant_a, "bm1"))
    names = {u["employee_code"] for u in r.json()["items"]}
    assert tenant_a["so1_code"] in names and tenant_a["so2_code"] not in names and tenant_a["so3_code"] not in names


async def test_company_isolation(client, tenant_a, tenant_b):
    a, b = await as_(client, tenant_a, "admin"), await as_(client, tenant_b, "admin")
    r = await client.post("/api/v1/branches", headers=a, json={"name": "Nellore", "code": "NLR", "region_id": str(tenant_a["r1"])})
    assert r.status_code == 201
    bid = r.json()["id"]
    assert "Nellore" not in [x["name"] for x in (await client.get("/api/v1/branches", headers=b)).json()]
    assert (await client.patch(f"/api/v1/branches/{bid}", headers=b, json={"name": "hacked"})).status_code == 404
    # B cannot place its people in A's branch
    r = await client.post("/api/v1/employees", headers=b, json={"employee_code": "X1", "full_name": "X",
                                                               "role": "sales_officer", "branch_id": bid})
    assert r.status_code == 404
    e = await make_entry(client, await as_(client, tenant_a, "so1"))
    assert (await client.get(f"/api/v1/entries/{e['id']}", headers=await as_(client, tenant_b, "pm"))).status_code == 404


async def test_branch_cluster_region_consistency(client, tenant_a):
    admin = await as_(client, tenant_a, "admin")
    r = await client.post("/api/v1/branches", headers=admin, json={
        "name": "Wrong", "code": "W1", "region_id": str(tenant_a["r2"]), "cluster_id": str(tenant_a["c1"])})
    assert r.status_code == 422  # cluster C1 is in region R1
    r = await client.post("/api/v1/branches", headers=admin, json={"name": "Auto", "code": "W2", "cluster_id": str(tenant_a["c1"])})
    assert r.status_code == 201 and r.json()["region_id"] == str(tenant_a["r1"])  # region follows the cluster
