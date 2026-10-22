"""Reproducible load + propagation check against a running API.

    python tests/perf/perf.py --base http://localhost:8000 --admin-email ... --admin-password ... \
        --agents 20 --per-agent 10

Creates (idempotently) perf agents, logs them in concurrently, submits concurrently, keeps one admin SSE
stream open, and reports measured latencies. Only measured numbers are printed; interpret them with the
environment in mind (client and server on one machine, Docker Desktop VM, single API process).
"""
import argparse
import asyncio
import hashlib
import io
import json
import statistics
import time
import uuid

import httpx
from PIL import Image


def pct(xs, p):
    if not xs:
        return float("nan")
    xs = sorted(xs)
    return xs[min(len(xs) - 1, int(round(p / 100 * (len(xs) - 1))))]


def summarize(name, ms):
    print(f"{name:<34} n={len(ms):<4} p50={pct(ms,50):7.1f}  p95={pct(ms,95):7.1f}  p99={pct(ms,99):7.1f}  max={max(ms, default=float('nan')):7.1f} ms")


def jpeg() -> bytes:
    b = io.BytesIO()
    Image.new("RGB", (640, 480), (30, 120, 200)).save(b, "JPEG", quality=80)
    return b.getvalue()


def body(photo_id=None, key=None):
    e = {"contact_category": "Dealer", "contact_name": "Perf", "meeting_date": "2026-10-16", "meeting_description": "load test"}
    if photo_id:
        e["meeting_photo"] = photo_id
    return {
        "idempotency_key": key or uuid.uuid4().hex, "client_submission_id": uuid.uuid4().hex,
        "form_id": "field_meeting_report", "form_version": 1, "answers": {"meeting_details": [e]},
        "submitted_at_device": "2026-10-16T10:15:00Z", "device_tz_offset_min": 330,
        "location": {"latitude": 16.5, "longitude": 80.6, "accuracy_m": 10, "fix_at_device": "2026-10-16T10:15:01Z", "status": "obtained"},
    }


async def main():
    a = argparse.ArgumentParser()
    a.add_argument("--base", default="http://localhost:8000")
    a.add_argument("--admin-email", required=True)
    a.add_argument("--admin-password", required=True)
    a.add_argument("--agent-password", default="PerfAgent#2026")
    a.add_argument("--agents", type=int, default=20)
    a.add_argument("--per-agent", type=int, default=10)
    a.add_argument("--photo-every", type=int, default=4, help="every Nth submission carries a photo")
    args = a.parse_args()
    B = args.base.rstrip("/") + "/api/v1"
    limits = httpx.Limits(max_connections=200)
    async with httpx.AsyncClient(timeout=60, limits=limits) as c:
        t = (await c.post(f"{B}/auth/login", json={"email": args.admin_email, "password": args.admin_password})).json()
        ah = {"Authorization": f"Bearer {t['access_token']}"}
        branch = (await c.get(f"{B}/branches", headers=ah)).json()[0]["id"]
        for i in range(args.agents):
            await c.post(f"{B}/employees", headers=ah, json={
                "employee_code": f"PERF{i:03d}", "full_name": f"Perf Agent {i}", "email": f"perf{i}@fieldsync-demo.com",
                "password": args.agent_password, "role": "agent", "branch_id": branch, "branch_ids": [branch]})  # 409 on reruns is fine

        # --- concurrent logins ---
        async def login(i):
            s = time.perf_counter()
            r = await c.post(f"{B}/auth/login", json={"email": f"perf{i}@fieldsync-demo.com", "password": args.agent_password})
            return (time.perf_counter() - s) * 1000, r
        res = await asyncio.gather(*[login(i) for i in range(args.agents)])
        login_ok = sum(r.status_code == 200 for _, r in res)
        summarize(f"login ({args.agents} concurrent)", [ms for ms, _ in res])
        heads = [{"Authorization": f"Bearer {r.json()['access_token']}"} for _, r in res if r.status_code == 200]

        # --- SSE listener (admin) ---
        tk = (await c.post(f"{B}/events/ticket", headers=ah)).json()["ticket"]
        arrivals: dict[str, float] = {}
        ready = asyncio.Event()

        async def sse():
            async with c.stream("GET", f"{B}/events/submissions", params={"ticket": tk}, timeout=None) as r:
                ready.set()
                async for line in r.aiter_lines():
                    if line.startswith("data: "):
                        arrivals[json.loads(line[6:])["submission_id"]] = time.perf_counter()

        sse_task = asyncio.create_task(sse())
        await asyncio.wait_for(ready.wait(), 10)
        await asyncio.sleep(0.3)

        # --- concurrent submissions (photo upload is timed separately) ---
        data = jpeg()
        sub_ms, photo_ms, acks, fails = [], [], {}, []

        async def agent(h, n):
            for k in range(args.per_agent):
                pid = None
                if args.photo_every and k % args.photo_every == 0:
                    pid = str(uuid.uuid4())
                    s = time.perf_counter()
                    init = {"photo_id": pid, "mime_type": "image/jpeg", "size_bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}
                    r1 = await c.post(f"{B}/uploads/initiate", json=init, headers=h)
                    r2 = await c.put(f"{B}/uploads/{pid}", content=data, headers=h)
                    r3 = await c.post(f"{B}/uploads/{pid}/complete", headers=h)
                    photo_ms.append((time.perf_counter() - s) * 1000)
                    if not all(r.status_code == 200 for r in (r1, r2, r3)):
                        fails.append(("photo", r3.status_code))
                        continue
                s = time.perf_counter()
                r = await c.post(f"{B}/submissions", json=body(pid), headers=h)
                done = time.perf_counter()
                sub_ms.append((done - s) * 1000)
                if r.status_code == 201:
                    acks[r.json()["id"]] = done
                else:
                    fails.append(("submit", r.status_code, r.text[:120]))

        wall = time.perf_counter()
        await asyncio.gather(*[agent(h, i) for i, h in enumerate(heads)])
        wall = time.perf_counter() - wall
        await asyncio.sleep(3)  # let remaining events arrive
        total = len(heads) * args.per_agent
        print(f"{'submissions':<34} ok={len(acks)}/{total} success={100*len(acks)/max(1,total):.1f}% in {wall:.1f}s ({len(acks)/wall:.1f}/s) failures={fails[:3]}")
        summarize("submit API (excl. photo upload)", sub_ms)
        summarize("photo upload (init+put+complete)", photo_ms)

        # --- dashboard propagation: SSE arrival relative to the client receiving the ack ---
        lat = [(arrivals[i] - acks[i]) * 1000 for i in acks if i in arrivals]
        missed = len(acks) - len(lat)
        early = sum(1 for x in lat if x < 0)
        print(f"{'SSE events received':<34} {len(lat)}/{len(acks)} missed={missed} (events that beat the ack read: {early})")
        summarize("ack -> SSE arrival (clamped >=0)", [max(0.0, x) for x in lat])

        # --- idempotent repeats ---
        key = uuid.uuid4().hex
        rs = await asyncio.gather(*[c.post(f"{B}/submissions", json={**body(key=key), "client_submission_id": "same"}, headers=heads[0]) for _ in range(20)])
        ids = {r.json().get("id") for r in rs if r.status_code in (200, 201)}
        codes = sorted({r.status_code for r in rs})
        print(f"{'20 concurrent same-key posts':<34} distinct submissions={len(ids)} status codes={codes}")

        # --- dashboard list queries ---
        ql = []
        for _ in range(50):
            s = time.perf_counter()
            r = await c.get(f"{B}/submissions", params={"page_size": 25}, headers=ah)
            ql.append((time.perf_counter() - s) * 1000)
        summarize("GET /submissions (page of 25)", ql)
        s = time.perf_counter()
        d = await c.get(f"{B}/dashboard", headers=ah)
        print(f"{'GET /dashboard':<34} {(time.perf_counter()-s)*1000:.1f} ms (total submissions listed: {(await c.get(f'{B}/submissions', headers=ah)).json()['total']})")
        sse_task.cancel()
        print(f"logins ok={login_ok}/{args.agents}")


asyncio.run(main())
