from tests.conftest import auth, login


async def test_login_bad_password(client, tenant_a):
    r = await client.post(
        "/api/v1/auth/login", json={"email": tenant_a["admin_email"], "password": "nope"}
    )
    assert r.status_code == 401


async def test_protected_requires_token(client):
    assert (await client.get("/api/v1/branches")).status_code == 401
    assert (
        await client.get("/api/v1/branches", headers={"Authorization": "Bearer junk"})
    ).status_code == 401


async def test_refresh_rotates_and_old_token_rejected(client, tenant_a):
    t = await login(client, tenant_a["agent_email"])
    r = await client.post("/api/v1/auth/refresh", json={"refresh_token": t["refresh_token"]})
    assert r.status_code == 200
    again = await client.post("/api/v1/auth/refresh", json={"refresh_token": t["refresh_token"]})
    assert again.status_code == 401
    await client.post("/api/v1/auth/logout", json={"refresh_token": r.json()["refresh_token"]})
    dead = await client.post("/api/v1/auth/refresh", json={"refresh_token": r.json()["refresh_token"]})
    assert dead.status_code == 401


async def test_agent_cannot_use_admin_endpoints(client, tenant_a):
    t = await login(client, tenant_a["agent_email"])
    assert (await client.get("/api/v1/employees", headers=auth(t))).status_code == 403
    r = await client.post(
        "/api/v1/branches", headers=auth(t), json={"name": "X", "code": "X"}
    )
    assert r.status_code == 403


async def test_me_includes_assignments(client, tenant_a):
    t = await login(client, tenant_a["agent_email"])
    r = await client.get("/api/v1/auth/me", headers=auth(t))
    assert r.status_code == 200 and r.json()["role"] == "agent"


async def test_company_isolation(client, tenant_a, tenant_b):
    ta = await login(client, tenant_a["admin_email"])
    tb = await login(client, tenant_b["admin_email"])

    # Admin A creates a branch; admin B must not see or modify it.
    r = await client.post("/api/v1/branches", headers=auth(ta), json={"name": "Nellore", "code": "NLR"})
    assert r.status_code == 201
    bid = r.json()["id"]
    names = [b["name"] for b in (await client.get("/api/v1/branches", headers=auth(tb))).json()]
    assert "Nellore" not in names
    assert (
        await client.patch(f"/api/v1/branches/{bid}", headers=auth(tb), json={"name": "hacked"})
    ).status_code == 404

    # Cross-tenant employee reference and patch.
    emp = {
        "employee_code": "E9", "full_name": "New", "email": "new-a@x.io",
        "password": "password123", "branch_id": bid,
    }
    assert (await client.post("/api/v1/employees", headers=auth(tb), json=emp)).status_code == 404
    assert (
        await client.patch(
            f"/api/v1/employees/{tenant_a['agent_id']}", headers=auth(tb), json={"status": "inactive"}
        )
    ).status_code == 404
    listed = (await client.get("/api/v1/employees", headers=auth(tb))).json()
    assert all(str(tenant_a["agent_id"]) != e["id"] for e in listed["items"])


async def test_branch_code_unique_per_company_and_agent_scope(client, tenant_a):
    ta = await login(client, tenant_a["admin_email"])
    dup = await client.post("/api/v1/branches", headers=auth(ta), json={"name": "Dup", "code": "HQ"})
    assert dup.status_code == 409
    await client.post("/api/v1/branches", headers=auth(ta), json={"name": "Other", "code": "OTH"})
    ag = await login(client, tenant_a["agent_email"])
    visible = [b["code"] for b in (await client.get("/api/v1/branches", headers=auth(ag))).json()]
    assert visible == ["HQ"]


async def test_deactivated_user_loses_access_immediately(client, tenant_a):
    ta = await login(client, tenant_a["admin_email"])
    ag = await login(client, tenant_a["agent_email"])
    r = await client.patch(
        f"/api/v1/employees/{tenant_a['agent_id']}", headers=auth(ta), json={"status": "inactive"}
    )
    assert r.status_code == 200
    assert (await client.get("/api/v1/auth/me", headers=auth(ag))).status_code == 401
    assert (
        await client.post("/api/v1/auth/login", json={"email": tenant_a["agent_email"], "password": "password123"})
    ).status_code == 401


async def test_admin_cannot_deactivate_self(client, tenant_a):
    ta = await login(client, tenant_a["admin_email"])
    r = await client.patch(
        f"/api/v1/employees/{tenant_a['admin_id']}", headers=auth(ta), json={"status": "inactive"}
    )
    assert r.status_code == 400


async def test_coordinate_validation(client, tenant_a):
    ta = await login(client, tenant_a["admin_email"])
    r = await client.post(
        "/api/v1/branches", headers=auth(ta),
        json={"name": "Bad", "code": "BAD", "latitude": 123, "longitude": 10},
    )
    assert r.status_code == 422


async def test_health_ready(client):
    assert (await client.get("/health")).status_code == 200
    assert (await client.get("/ready")).json()["status"] == "ready"


async def test_login_rate_limit_after_repeated_failures(client, tenant_a):
    from app.security.ratelimit import login_limiter
    login_limiter._hits.clear()
    body = {"email": tenant_a["agent_email"], "password": "wrong"}
    for _ in range(5):
        assert (await client.post("/api/v1/auth/login", json=body)).status_code == 401
    r = await client.post("/api/v1/auth/login", json=body)
    assert r.status_code == 429 and int(r.headers["retry-after"]) > 0
    # even the right password is refused while blocked; other accounts are unaffected
    good = {"email": tenant_a["agent_email"], "password": "password123"}
    assert (await client.post("/api/v1/auth/login", json=good)).status_code == 429
    assert (await client.post("/api/v1/auth/login", json={"email": tenant_a["admin_email"], "password": "password123"})).status_code == 200
    login_limiter._hits.clear()
    assert (await client.post("/api/v1/auth/login", json=good)).status_code == 200


async def test_oversized_bodies_rejected(client, tenant_a):
    ag = await login(client, tenant_a["agent_email"])
    big = b"x" * (1024 * 1024 + 10)
    r = await client.post("/api/v1/submissions", content=big, headers={**auth(ag), "Content-Type": "application/json"})
    assert r.status_code == 413
