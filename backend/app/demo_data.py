"""A week of realistic Sankalp activity for a client demo (docs/client-demo.md).

Run only on a freshly seeded database, inside the backend container:
    docker compose down -v && docker compose up -d
    docker compose exec backend python -m app.seed
    docker compose exec backend python -m app.demo_data

It plays the Monday-to-Sunday week before today through the real API, one day at a time, as the demo accounts:
roster and attendance uploads, the Sales Officers' entries, the daily run and allocation, the callers' tries, lead
cards, branch answers, corrections, the follow-up tracker, the green channel, a category review and the MIS login
register. Every record gets a time on the day it belongs to. Today is left for the live part of the demo.
The named examples ("Venkata Ramana" ...) are the ones the demo script opens.
"""
import asyncio
import os
import random
import uuid
from datetime import date, datetime, time, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import asyncpg
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select, update

import app.api.v1.branch as m_branch
import app.api.v1.calling as m_calling
import app.api.v1.reference as m_reference
import app.api.v1.reports as m_reports
import app.services.sankalp.handoff as m_handoff
import app.services.sankalp.ops as m_ops
from app.core.db import SessionLocal
from app.main import app
from app.models import Branch, CpSubtype, User
from app.security.passwords import hash_password
from app.services.sankalp import rules as R

IST = ZoneInfo("Asia/Kolkata")
PW = os.environ["SEED_PASSWORD"]
rng = random.Random(20261026)

# ---------------------------------------------------------------- the week
TODAY = datetime.now(IST).date()
MON = TODAY - timedelta(days=TODAY.weekday() + 7)  # Monday of last week
WEEK = [MON + timedelta(days=i) for i in range(7)]
TUE, WED, THU, FRI, SAT, SUN = WEEK[1:]


def at(d: date, hh: int, mm: int = 0, ss: int = 0) -> datetime:
    return datetime.combine(d, time(hh, mm, ss), IST)


def working_after(d: date, n: int) -> date:
    """The n-th working day (not Sunday) after d."""
    while n:
        d += timedelta(days=1)
        if d.weekday() != 6:
            n -= 1
    return d


# ---------------------------------------------------------------- the company's "today" follows the simulated day
class Clock:
    day = TODAY


CLOCK = Clock()


async def _today(s, company_id):
    return CLOCK.day


for _m in (m_ops, m_handoff, m_calling, m_branch, m_reports, m_reference):
    _m.company_today = _today

# ---------------------------------------------------------------- every row made by an action gets the action's time
STAMPED = [("audit_logs", "created_at"), ("branch_answers", "created_at"), ("branch_answers", "reviewed_at"),
           ("call_allocations", "created_at"), ("call_allocations", "closed_at"), ("call_attempts", "created_at"),
           ("caller_days", "set_at"), ("entry_events", "created_at"), ("followup_tracker", "updated_at"),
           ("import_batches", "created_at"), ("lead_cards", "updated_at"), ("lead_cards", "lead_id_at"),
           ("login_register_rows", "created_at"), ("sankalp_entries", "created_at"),
           ("sankalp_entries", "updated_at"), ("sankalp_entries", "received_at_server"),
           ("sankalp_entries", "status_at"), ("selection_runs", "started_at"), ("users", "created_at"),
           ("users", "updated_at")]


class Stamper:
    async def open(self):
        self.conn = await asyncpg.connect(os.environ["DATABASE_URL"].replace("+asyncpg", ""))
        self.mark = await self.conn.fetchval("select clock_timestamp()")

    async def __call__(self, t: datetime):
        ts, mark = t.isoformat(), self.mark.isoformat()
        await self.conn.execute(";".join(f"update {tb} set {col} = '{ts}' where {col} > '{mark}'" for tb, col in STAMPED))
        self.mark = await self.conn.fetchval("select clock_timestamp()")


stamp = Stamper()


# ---------------------------------------------------------------- API as the demo accounts
PORTAL = {"sales_officer": "mobile", "branch_manager": "manage", "cluster_manager": "manage", "region_manager": "manage",
          "caller": "callcentre", "master_owner": "callcentre", "sankalp_monitor": "admin", "mis": "admin", "admin": "admin"}


class Api:
    def __init__(self, client: AsyncClient):
        self.c, self.tokens = client, {}

    async def h(self, emp: str, role: str) -> dict:
        if emp not in self.tokens:
            r = await self.c.post("/api/v1/auth/login", json={"identifier": emp, "password": PW, "portal": PORTAL[role]})
            assert r.status_code == 200, f"login {emp}: {r.text}"
            self.tokens[emp] = {"Authorization": f"Bearer {r.json()['access_token']}"}
        return self.tokens[emp]

    async def call(self, method: str, who: "Person", path: str, expect=(200, 201), **kw):
        r = await self.c.request(method, f"/api/v1{path}", headers=await self.h(who.emp, who.role), **kw)
        assert r.status_code in expect, f"{method} {path} as {who.emp}: {r.status_code} {r.text}"
        return r.json() if r.content else None


class Person:
    def __init__(self, emp, name, role, **kw):
        self.emp, self.name, self.role = emp, name, role
        self.__dict__.update(kw)
        self.id = None


TOWN = {"Vijayawada": (16.5062, 80.6480), "Guntur": (16.3067, 80.4365), "Nellore": (14.4426, 79.9865)}
SOS = [
    Person("AHFL90001", "Ravi Kumar", "sales_officer", desig="RO", branch="Vijayawada", spoke="Benz Circle", joined="2025-06-02", per_day=(10, 12)),
    Person("AHFL90002", "Lakshmi Devi", "sales_officer", desig="RM", branch="Guntur", spoke="Brodipet", joined="2024-11-18", per_day=(9, 11)),
    Person("AHFL90003", "Srinivas Naidu", "sales_officer", desig="ABM", branch="Vijayawada", spoke="Patamata", joined="2023-08-01", per_day=(9, 11)),
    Person("AHFL90004", "Padma Priya", "sales_officer", desig="RO", branch="Vijayawada", spoke="Gollapudi", joined="2025-09-15", per_day=(8, 10)),
    Person("AHFL90005", "Kiran Kumar", "sales_officer", desig="RO", branch="Guntur", spoke="Arundelpet", joined="2025-02-10", per_day=(6, 9)),
    Person("AHFL90006", "Sai Teja", "sales_officer", desig="RO", branch="Nellore", spoke="Magunta Layout", joined="2025-04-21", per_day=(8, 11)),
    Person("AHFL90007", "Anusha Reddy", "sales_officer", desig="RM", branch="Nellore", spoke="Vedayapalem", joined=str(WED), per_day=(5, 8)),
    Person("AHFL90008", "Naresh Goud", "sales_officer", desig="RO", branch="Guntur", spoke="Lakshmipuram", joined="2024-03-04", per_day=(6, 9)),
]
SO = dict(zip(["ravi", "lakshmi", "srinivas", "padma", "kiran", "saiteja", "anusha", "naresh"], SOS))
BM = Person("AHFL90011", "Suresh Reddy", "branch_manager")
RTM = Person("AHFL90021", "Anil Varma", "cluster_manager")
RBH = Person("AHFL90031", "Prakash Rao", "region_manager")
DIVYA = Person("AHFL90061", "Divya S", "caller")
FARHAN = Person("AHFL90062", "Farhan Ali", "caller")
MASTER = Person("AHFL90071", "Geetha M", "master_owner")
MONITOR = Person("AHFL90081", "Hari Prasad", "sankalp_monitor")
MIS = Person("AHFL90091", "Indira N", "mis")
CALLER_OF = {"Vijayawada": DIVYA, "Guntur": FARHAN, "Nellore": DIVYA}
ABSENT = {("kiran", THU)}

# ---------------------------------------------------------------- what people say
FIRST = ["Venkatesh", "Srinivasa", "Ramesh", "Suresh", "Mahesh", "Nagaraju", "Rambabu", "Satyanarayana", "Koteswara",
         "Subba Rao", "Appa Rao", "Sambasiva", "Veeraiah", "Chinna", "Naga Babu", "Sudhakar", "Prabhakar", "Murali",
         "Raghu", "Vamsi", "Sravan", "Harish", "Phani", "Gopal", "Bhanu", "Seshu", "Madhavi", "Sujatha", "Padmavathi",
         "Rani", "Sarada", "Lalitha", "Vijaya", "Annapurna", "Sireesha", "Bhargavi", "Hymavathi", "Jyothi", "Sunitha",
         "Aruna", "Revathi", "Naga Lakshmi", "Kalyani", "Durga", "Prasanna", "Ravi Teja", "Yesu", "Abdul", "Imran", "John"]
LAST = ["Reddy", "Naidu", "Chowdary", "Rao", "Varma", "Goud", "Yadav", "Raju", "Babu", "Kumar", "Sastry", "Murthy",
        "Prasad", "Shaik", "Basha", "Setty", "Achari", "Dasari", "Kolli", "Pothula"]
SHOPS = ["Sri Venkateswara Hardware", "Lakshmi Cement Agencies", "Durga Bricks", "Sai Ram Steel Traders",
         "Balaji Sand Suppliers", "Krishna Tiles & Sanitary", "Vinayaka Paints", "Annapurna Timber Depot",
         "Sri Rama Brick Works", "Kanaka Durga Hardware", "Srinivasa Pipes & Fittings", "Mahalakshmi Granites"]
DESC = {
    "lead": ["Owns a plot in {area}, wants to start construction", "Renting in {area}, looking to buy a 2BHK flat",
             "Wants to add a first floor to the house in {area}", "Has a plot near {area}, needs plot + construction loan",
             "Looking at an independent house in {area}, budget 40 lakh", "Kirana shop owner, wants to build on own plot",
             "Teacher, wants to buy a flat near {area}", "Has a home loan elsewhere, asked about lower EMI",
             "Auto driver, wants to extend the house for his son", "Wants to build two rooms for rent on own land"],
    "prospect": ["May buy a house next year, asked about eligibility", "Saving for a plot in {area}, interested later",
                 "Daughter's marriage first, house after that", "Wants to know the EMI for 20 lakh",
                 "Waiting for the house approval from the panchayat"],
    "dsa_connector": ["Local DSA, sends 3-4 home loan files a month", "Insurance agent, meets many house builders",
                      "Real-estate broker in {area}", "Chartered accountant, clients ask about home loans"],
    "contact_point": ["Shop owner, customers buying material for new houses", "Supplies material to builders in {area}",
                      "Knows most of the people building in {area}"],
    "existing_customer": ["Already has an Aham home loan, came for a top-up", "Aham customer since 2023, wanted the statement"],
    "existing_applicant": ["File already with Aham branch, asked about the status", "Applied at the branch last month"],
}
AREAS = {"Vijayawada": ["Benz Circle", "Patamata", "Gollapudi", "Poranki", "Kanuru", "Bhavanipuram", "Gunadala"],
         "Guntur": ["Brodipet", "Arundelpet", "Lakshmipuram", "Pattabhipuram", "Gorantla", "Nallapadu"],
         "Nellore": ["Magunta Layout", "Vedayapalem", "Balaji Nagar", "Dargamitta", "Stonehousepet"]}

HERO_NAMES: set[str] = set()
used_phones: set[str] = set()
used_names: set[str] = set()


def new_phone() -> str:
    while True:
        p = str(rng.choice([6, 7, 8, 9])) + "".join(str(rng.randrange(10)) for _ in range(9))
        if p not in used_phones:
            used_phones.add(p)
            return p


def typed(p: str) -> str:
    """How an SO might type it: the server cleans it and keeps it as typed."""
    return rng.choice([p, p, p, f"{p[:5]} {p[5:]}", f"+91 {p[:5]} {p[5:]}", f"0{p}", f"+91{p}"])


def new_name(category: str) -> str:
    while True:
        n = rng.choice(SHOPS) if category == "contact_point" and rng.random() < 0.6 else f"{rng.choice(FIRST)} {rng.choice(LAST)}"
        if n not in used_names and n not in HERO_NAMES:
            used_names.add(n)
            return n


# ---------------------------------------------------------------- answers
def visit_date(d: date) -> date:
    return working_after(d, rng.randint(1, 4))


def lead_answers(d: date, name: str, kind: str = "validated", **over) -> dict:
    a = {"name_check": rng.choices(["Same person", "Same person, different spelling", "Different person – same family"],
                                   [85, 10, 5])[0],
         "name_given": name, "visit": rng.choices(["Yes", "Don't recall"], [85, 15])[0],
         "relationship": rng.choices(["No", "Yes – another employee"], [92, 8])[0],
         "loan_need": rng.choices(["Home purchase", "Self-construction", "Plot + construction", "Improvement or extension",
                                   "Balance transfer", "BT + construction"], [35, 25, 15, 15, 5, 5])[0],
         "timeline": rng.choice(R.TIMELINE), "income": rng.choices(R.INCOME, [45, 35, 15, 5])[0],
         "documents": rng.choices(["Yes", "Partly", "No"], [45, 35, 20])[0],
         "next_step": rng.choices(["SO / branch visit", "Call centre to continue", "Not now"], [55, 15, 30])[0],
         "purpose": rng.choice(R.PURPOSE), "own_contribution": rng.choice(R.OWN_CONTRIBUTION)}
    if kind == "no_visit":
        a["visit"] = "No"
    elif kind == "diff_person":
        a["name_check"] = "Different person"
    elif kind == "missing":
        a.pop("loan_need")
    elif kind == "knows_so":
        a["relationship"] = "Yes – the same officer"
    elif kind == "red":
        a.update(loan_need="Not looking for a loan", next_step="Not now")
    elif kind == "lap":
        a["loan_need"] = rng.choice(["LAP", "BT + LAP"])
    elif kind == "already":
        a["documents"] = "File already logged with Aham"
    a.update(over)
    if a.get("next_step") == "SO / branch visit" and "next_date" not in a:
        a["next_date"] = str(visit_date(d))
    if a.get("next_step") != "SO / branch visit":
        a.pop("next_date", None)
    return a


AMOUNT = {"Home purchase": (15, 60), "Self-construction": (5, 25), "Plot + construction": (10, 40),
          "Improvement or extension": (3, 12), "Balance transfer": (10, 30), "BT + construction": (12, 35),
          "LAP": (5, 30), "BT + LAP": (8, 30)}
JOBS = ["Government teacher", "Kirana shop owner", "Software engineer", "Auto driver", "Farmer", "Bank clerk",
        "Tailoring unit owner", "Pharmacist", "Contractor", "Private school staff"]


def lead_card(loan_need: str, town: str, lead_id: str | None = None, **over) -> dict:
    lo, hi = AMOUNT.get(loan_need, (8, 30))
    pin = {"Vijayawada": "5200", "Guntur": "5220", "Nellore": "5240"}[town] + f"{rng.randint(1, 30):02d}"
    salaried = rng.random() < 0.55
    income = rng.randrange(18, 90) * 1000
    card = {"age": rng.randint(26, 56), "city": town, "address": f"{rng.randint(1, 60)}-{rng.randint(1, 30)}, {rng.choice(AREAS[town])}",
            "property_pincode": pin, "payslip_or_itr": rng.random() < 0.8, "job_profile": rng.choice(JOBS) if salaried else "Self-employed",
            "individual_monthly_income": income, "family_monthly_income": income + rng.randrange(0, 40) * 1000,
            "vehicle": rng.random() < 0.6, "cibil_score": rng.choice([None, rng.randint(640, 820)]),
            "bounce_last_6_months": rng.random() < 0.08, "property_owner": rng.choice(["Self", "Spouse", "Father", "Self and spouse"]),
            "property_area": f"{rng.choice([120, 150, 167, 200, 240, 300])} sq yd", "approved_property": rng.choice(["Yes", "Yes", "Applied"]),
            "property_type": rng.choice(["Independent house", "Flat", "Plot", "Row house"]), "loan_purpose": loan_need,
            "loan_requirement": rng.randint(lo * 2, hi * 2) * 50_000}
    if card["vehicle"]:
        card["vehicle_type"] = rng.choice(["Two-wheeler", "Two-wheeler", "Car", "Auto"])
    if lead_id:
        card["lead_id"] = lead_id
    card.update(over)
    return card


def tcs_lead_id() -> str:
    return f"TCS-L-{rng.randint(100000, 999999)}"


UNANSWERED = [R.RNR, R.RNR, R.RNR, "Busy", "Switched off", "Not reachable"]


# ---------------------------------------------------------------- how each contact behaves on the phone
class Plan:
    """Default behaviour of a random contact; named examples override `on_call`."""

    def __init__(self, e: dict, group: str):
        self.e, self.group, self.tries, self.connected = e, group, 0, False
        if group == "lead":
            self.fate = rng.choices(["now", "later", "never", "wrong", "invalid", "refused", "callback"],
                                    [55, 18, 4, 4, 3, 4, 5])[0]
            self.connect_on = 1 if self.fate == "now" else rng.choice([2, 3, 4])
            self.kind = rng.choices(["validated", "no_visit", "diff_person", "missing", "knows_so", "red", "lap", "already"],
                                    [62, 6, 4, 3, 4, 12, 5, 4])[0]
        else:
            self.fate = rng.choices(["dsa", "noanswer"], [72, 28])[0]
            self.dsa = rng.choices(["Green", "NA", "Amber", "Red", "blank", "convert"], [42, 20, 15, 5, 6, 12])[0]

    def on_call(self, d: date) -> dict | None:
        """The try to record now: {"outcome", "answers"?, "next_date"?, "card"?}; None leaves it on the list."""
        self.tries += 1
        town, name = self.e["town"], self.e["person_name"]
        if self.connected:  # a follow-up or PRIORITY call on a contact already reached: the case moves on
            return {"outcome": "Connected", "answers": lead_answers(d, name, next_step="SO / branch visit")}
        if self.group == "dsa":
            if self.fate == "noanswer":
                return {"outcome": rng.choice(UNANSWERED)}
            self.connected = True
            if self.dsa == "convert":
                a = lead_answers(d, name, needs_home_loan="Yes")
                return {"outcome": "Connected", "answers": a, "card": lead_card(a["loan_need"], town, tcs_lead_id() if rng.random() < 0.5 else None)}
            return {"outcome": "Connected", "answers": {"needs_home_loan": "No", **({} if self.dsa == "blank" else {"dsa_rag": self.dsa})}}
        if self.fate in ("wrong", "invalid", "refused"):
            return {"outcome": {"wrong": "Wrong person", "invalid": "Invalid number", "refused": "Refused to talk"}[self.fate]}
        if self.fate == "callback" and self.tries == 1:
            return {"outcome": "Callback requested", "next_date": str(working_after(d, rng.randint(1, 2)))}
        if self.fate == "never" or self.tries < self.connect_on:
            return {"outcome": rng.choice(UNANSWERED)}
        self.connected = True
        a = lead_answers(d, name, self.kind)
        out = {"outcome": "Connected", "answers": a}
        if self.kind in ("validated", "no_visit", "diff_person") and rng.random() < 0.7:
            out["card"] = lead_card(a["loan_need"], town, tcs_lead_id() if rng.random() < 0.55 else None)
        return out


class Scripted(Plan):
    """A named example: its tries are given day by day."""

    def __init__(self, e, group, by_day: dict):
        super().__init__(e, group)
        self.by_day = by_day

    def on_call(self, d):
        steps = self.by_day.get(d)
        if steps is None:
            return super().on_call(d)
        self.tries += 1
        return steps.pop(0) if steps else None


# ---------------------------------------------------------------- the demo
class Demo:
    def __init__(self, api: Api):
        self.api = api
        self.entries: dict[str, dict] = {}  # entry id -> entry (+ town, so, plan, validated_on)
        self.heroes: dict[str, dict] = {}   # name -> entry
        self.planned: dict[date, list] = {}  # scripted entries per day
        self.answered: set[str] = set()

    # ---------------------------------------------------------- reference data
    async def load_ids(self):
        async with SessionLocal() as s:
            users = {u.employee_code: u for u in (await s.execute(select(User))).scalars().all()}
            self.branch = {b.name: b.id for b in (await s.execute(select(Branch))).scalars().all()}
            self.cp = {c.label: c.id for c in (await s.execute(select(CpSubtype))).scalars().all()}
        for p in [*SOS, BM, RTM, RBH, DIVYA, FARHAN, MASTER, MONITOR, MIS]:
            p.id = users[p.emp].id if p.emp in users else None

    async def roster(self, with_exit: bool):
        rows = ["Emp ID,Name,Designation,Region,Cluster,Branch,Spoke,Joining date,Exit date,Email,Phone,Role"]
        for p in SOS:
            exit_date = str(THU) if with_exit and p.emp == "AHFL90008" else ""
            rows.append(f"{p.emp},{p.name},{p.desig},AP & TG,AP Coastal,{p.branch},{p.spoke},{p.joined},{exit_date},,,")
        await self.api.call("POST", MONITOR, "/imports/roster", files={"file": ("FOS_spoke_roster.csv", "\n".join(rows) + "\n", "text/csv")},
                            data={"dry_run": "false"})

    async def attendance(self, d: date, at_time: datetime | None):
        rows = ["Emp ID,Date,Status"]
        for key, p in SO.items():
            if date.fromisoformat(p.joined) > d or (p.emp == "AHFL90008" and d > THU):
                continue
            code = "A" if (key, d) in ABSENT else rng.choices(["P", "P(MS)", "P(R)"], [88, 8, 4])[0]
            rows.append(f"{p.emp},{d},{code}")
        await self.api.call("POST", MONITOR, "/imports/attendance", files={"file": (f"attendance_{d}.csv", "\n".join(rows) + "\n", "text/csv")},
                            data={"dry_run": "false"})
        if at_time:
            await stamp(at_time)

    # ---------------------------------------------------------- entries
    async def make_entry(self, so: Person, d: date, hh: int, mm: int, category: str, name: str | None = None,
                         phone: str | None = None, desc: str | None = None, delay_s: int | None = None,
                         last_contact: datetime | None = None, subtype: str | None = None, typed_as: str | None = None) -> dict:
        name = name or new_name(category)
        phone = phone or new_phone()
        area = rng.choice(AREAS[so.branch])
        desc = desc or rng.choice(DESC[category]).format(area=area)
        lat0, lon0 = TOWN[so.branch]
        submitted = at(d, hh, mm, rng.randint(0, 59))
        body = {"idempotency_key": uuid.uuid4().hex, "client_entry_id": uuid.uuid4().hex, "category": category,
                "person_name": name, "phone": typed_as or typed(phone), "description": desc, "photo_ids": [],
                "keka_photo_time": f"09:{(sum(map(ord, so.emp)) + d.toordinal()) % 30 + 10:02d}",
                "submitted_at_device": submitted.isoformat(), "device_tz_offset_min": 330,
                "location": {"latitude": round(lat0 + rng.uniform(-0.035, 0.035), 6),
                             "longitude": round(lon0 + rng.uniform(-0.035, 0.035), 6),
                             "accuracy_m": round(rng.uniform(4, 25), 1),
                             "fix_at_device": (submitted + timedelta(seconds=2)).isoformat(), "status": "obtained"}}
        if category == "contact_point":
            body["cp_subtype_id"] = str(self.cp[subtype or rng.choice(list(self.cp))])
        if last_contact:
            body["device_clock_at_last_contact"] = last_contact.isoformat()
        e = await self.api.call("POST", so, "/entries", json=body)
        await stamp(submitted + timedelta(seconds=delay_s if delay_s is not None else rng.randint(20, 95)))
        e.update(town=so.branch, so=so, phone_clean=phone, person_name=name)
        group = R.CALL_GROUP[category]
        e["plan"] = Plan(e, "lead" if group == "lead" else "dsa") if group != "none" else None
        self.entries[e["id"]] = e
        return e

    async def entries_for(self, d: date):
        scripted = sorted(self.planned.get(d, []), key=lambda x: (x[1], x[2]))
        for so_key, hh, mm, kw, plan, key in scripted:
            e = await self.make_entry(SO[so_key], d, hh, mm, **kw)
            e["key"] = key
            self.heroes[key] = e
            if plan is not None:
                e["plan"] = Scripted(e, "lead" if R.CALL_GROUP[kw["category"]] == "lead" else "dsa", plan)
        heroes_by = {}
        for so_key, *_ in scripted:
            heroes_by[so_key] = heroes_by.get(so_key, 0) + 1
        for key, p in SO.items():
            if (key, d) in ABSENT or date.fromisoformat(p.joined) > d or (p.emp == "AHFL90008" and d > THU):
                continue
            if d == SUN:
                n = {"ravi": 1, "saiteja": 1}.get(key, 0)
            else:
                lo, hi = p.per_day
                n = rng.randint(lo, hi) - (2 if d == SAT else 0)
            n -= heroes_by.get(key, 0)
            minutes = sorted(rng.sample(range(10 * 60, 18 * 60 + 30), max(n, 0)))
            for m in minutes:
                cat = rng.choices(list(R.CATEGORIES), [44, 20, 8, 11, 10, 7])[0]
                await self.make_entry(p, d, m // 60, m % 60, cat)

    # ---------------------------------------------------------- the call centre
    async def calling_day(self, d: date, first: bool, leave_unworked: dict | None = None):
        if first:
            await self.api.call("PUT", MASTER, "/calls/caller-days", json={"day": str(d), "assignments": [
                {"branch_id": str(self.branch[b]), "caller_id": str(c.id)} for b, c in CALLER_OF.items()]})
        else:
            prev = d - timedelta(days=2 if d.weekday() == 0 else 1)
            await self.api.call("POST", MASTER, "/calls/caller-days/copy", json={"from_day": str(prev), "to_day": str(d)})
        await stamp(at(d, 9, 2))
        await self.api.call("POST", MASTER, "/calls/runs", json={"run_date": str(d)})
        await stamp(at(d, 9, 6))
        for caller in (DIVYA, FARHAN):
            skip = (leave_unworked or {}).get(caller.emp, 0)
            clock = at(d, 9, 30 + rng.randint(0, 10))
            items = (await self.api.call("GET", caller, "/calls/my-list"))["items"]
            for it in items[:len(items) - skip]:
                clock = await self.one_call(caller, it, d, clock)
            clock = max(clock, at(d, 15, rng.randint(0, 20)))
            items = (await self.api.call("GET", caller, "/calls/my-list"))["items"]
            for it in items[:len(items) - skip]:
                if it["tries_today"] >= 1:  # the afternoon try of those still not reached
                    clock = await self.one_call(caller, it, d, clock)

    async def one_call(self, caller: Person, it: dict, d: date, clock: datetime) -> datetime:
        e = self.entries[it["id"]]
        step = e["plan"].on_call(d) if e.get("plan") else None
        if step is None:
            return clock
        hour = clock.hour
        slot = R.SLOTS[min(max(hour - 9, 0), 9)]
        body = {"slot": slot, "outcome": step["outcome"]}
        if "answers" in step:
            body["answers"] = step["answers"]
        if "next_date" in step:
            body["next_date"] = step["next_date"]
        res = await self.api.call("POST", caller, f"/calls/entries/{e['id']}/attempts", json=body)
        await stamp(clock)
        if str(res.get("row_status", "")).startswith("Validated") or res.get("row_status") == R.NOT_COUNTED_LAP:
            e.setdefault("validated_on", d)
        card = step.get("card")
        if card and (str(res.get("row_status", "")).startswith("Validated") or res.get("row_status") == R.NOT_COUNTED_LAP):
            await self.api.call("PUT", caller, f"/calls/entries/{e['id']}/lead-card", json=card)
            await stamp(clock + timedelta(minutes=3))
        return clock + timedelta(minutes=rng.randint(4, 8))

    # ---------------------------------------------------------- the branch
    async def branch_day(self, d: date, scripted: dict):
        for who in (BM, RBH):
            clock = at(d, 11, rng.randint(0, 40))
            leads = (await self.api.call("GET", who, "/branch/leads"))["items"]
            for lead in leads:
                e = self.entries.get(lead["id"])
                if not e or lead["branch_answer"] or e["id"] in self.answered:
                    continue
                if e.get("key") in scripted:
                    code, when, note = scripted[e["key"]]
                    await self.answer(who, e, d, code, when, clock, note)
                    clock += timedelta(minutes=rng.randint(6, 25))
                    continue
                if e.get("key") or e.get("validated_on") is None or e["validated_on"] >= d or rng.random() > 0.75:
                    continue
                code = rng.choices(["A1", "A2", "A3", "A5", "B", "C1", "C3", "F1", "F2", "E1", "E2", "1", "3", "R1", "R2", "R4", "R5", "R6"],
                                   [10, 6, 6, 3, 5, 5, 5, 7, 5, 4, 3, 10, 3, 2, 3, 3, 3, 2])[0]
                asked = R.BRANCH_CODES[code][1]
                when = None
                if asked:
                    far = code in ("E1", "E2") and rng.random() < 0.5
                    when = working_after(d, rng.randint(16, 24) if far else rng.randint(1, 6))
                await self.answer(who, e, d, code, when, clock)
                clock += timedelta(minutes=rng.randint(6, 25))
        missing = [k for k in scripted if self.heroes[k]["id"] not in self.answered]
        assert not missing, f"{d}: no manager saw {missing}"

    async def answer(self, who, e, d, code, when, clock, note=None):
        body = {"code": code, **({"answer_date": str(when)} if when else {}), **({"note": note} if note else {})}
        await self.api.call("POST", who, f"/branch/leads/{e['id']}/answer", json=body)
        await stamp(clock)
        self.answered.add(e["id"])
        e["branch_code"], e["branch_date"] = code, when

    # ---------------------------------------------------------- the MIS login register
    async def login_register(self, d: date, extra_rows: list[str]):
        rows = ["TCS ID,Customer contact,Login date,Product,Final status,Source,Emp code"]
        for e in self.entries.values():
            if e.get("key") or e.get("branch_code") is None:
                continue
            code, when = e["branch_code"], e.get("branch_date")
            if code == "1":
                when = working_after(e["validated_on"], rng.randint(1, 2))
            elif not code.startswith(("A", "B", "C")) or when is None:
                continue
            if when > d or rng.random() > 0.7:
                continue
            p = e["phone_clean"]
            contact = rng.choices([p, f"{new_phone()} / {p}", f"{p}, {new_phone()}"], [75, 15, 10])[0]
            rows.append(f"{rng.randint(4800000, 4899999)},\"{contact}\",{when},Home Loan,Logged in,Sankalp,{e['so'].emp}")
        rows += extra_rows
        # Section 11: the same file, to open and "Check first" in the demo (a check saves nothing)
        Path("/tmp/login-register-saturday.csv").write_text("\n".join(rows) + "\n", encoding="utf-8")
        res = await self.api.call("POST", MIS, "/imports/login-register",
                                  files={"file": (f"MIS_login_register_{d}.csv", "\n".join(rows) + "\n", "text/csv")},
                                  data={"dry_run": "false"})
        await stamp(at(d, 17, 40))
        return res


def hero(demo: Demo, day: date, so: str, hh: int, mm: int, plan: dict | None = None, key: str | None = None, **kw):
    HERO_NAMES.add(kw["name"])
    demo.planned.setdefault(day, []).append((so, hh, mm, kw, plan, key or kw["name"]))


C = "Connected"


def ans(d, name, **kw):
    kind = kw.pop("kind", "validated")
    return lead_answers(d, name, kind, **{"name_check": "Same person", "visit": "Yes", "relationship": "No", **kw})


async def main():
    await stamp.open()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://demo") as client:
        api = Api(client)
        demo = Demo(api)
        await demo.load_ids()
        assert all(p.id for p in [BM, RTM, RBH, DIVYA, FARHAN, MASTER, MONITOR, MIS]), "run python -m app.seed first"

        # ------------------------------------------------ the named examples (see docs/client-demo.md)
        p_va = new_phone()
        hero(demo, MON, "ravi", 10, 15, {TUE: [{"outcome": C, "answers": ans(TUE, "Venkata Ramana", loan_need="Home purchase", documents="Yes",
                                                                                next_step="SO / branch visit", next_date=str(THU), visit="Yes", name_check="Same person"),
                                                 "card": lead_card("Home purchase", "Vijayawada", "TCS-L-104512", loan_requirement=3_500_000, cibil_score=742, age=38)}]},
             name="Venkata Ramana", category="lead", phone=p_va, typed_as=f"+91 {p_va[:5]} {p_va[5:]}",
             desc="Renting in Patamata, wants to buy a 2BHK flat near Benz Circle")
        hero(demo, TUE, "kiran", 11, 20, {WED: [{"outcome": C, "answers": ans(WED, "Lakshmi Prasanna", next_step="SO / branch visit")}]},
             name="Lakshmi Prasanna", category="lead", delay_s=6 * 3600 + 25 * 60,
             desc="Met at a construction site with no signal; wants to build on her plot")
        hero(demo, SUN, "ravi", 11, 5, None, name="Ramesh Chowdary", category="lead",
             desc="Met at the Sunday market in Gunadala, wants a construction loan")
        p_sb = new_phone()
        hero(demo, MON, "padma", 12, 30, {TUE: [{"outcome": C, "answers": ans(TUE, "Suresh Babu")}]},
             name="Suresh Babu", category="lead", phone=p_sb, desc="Wants to buy a flat in Gollapudi")
        hero(demo, THU, "padma", 15, 10, None, key="Suresh Babu #2", name="Suresh Babu", category="lead", phone=p_sb,
             desc="Met Suresh Babu again at the site office")
        p_nr = new_phone()
        hero(demo, WED, "srinivas", 10, 40, {THU: [{"outcome": C, "answers": ans(THU, "Nagarjuna Rao")}]},
             name="Nagarjuna Rao", category="lead", phone=p_nr, desc="Owns a plot in Poranki, wants plot + construction")
        hero(demo, WED, "ravi", 16, 20, None, key="Nagarjuna Rao #2", name="Nagarjuna Rao", category="lead", phone=p_nr,
             desc="Plot owner in Poranki, interested in a loan")
        p_hr = new_phone()
        hero(demo, MON, "saiteja", 11, 0, {TUE: [{"outcome": C, "answers": ans(TUE, "Hanumantha Rao")}]},
             name="Hanumantha Rao", category="lead", phone=p_hr, desc="Wants to extend his house in Balaji Nagar")
        hero(demo, THU, "padma", 11, 0, None, key="Hanumantha Rao #2", name="Hanumantha Rao", category="lead", phone=p_hr,
             desc="Met at a relative's house, asked about a loan")
        p_gh = new_phone()
        hero(demo, MON, "lakshmi", 13, 10, {TUE: [{"outcome": C, "answers": {"needs_home_loan": "No", "dsa_rag": "Green"}}]},
             name="Ganesh Hardware", category="contact_point", phone=p_gh, subtype="Other Hardware Shop",
             desc="Hardware shop on the main road, sends customers who build houses")
        hero(demo, THU, "kiran", 12, 45, None, key="Ganesh Hardware #2", name="Ganesh Hardware", category="dsa_connector", phone=p_gh,
             desc="Hardware shop owner, wants to refer customers")
        p_pv = new_phone()
        never = {day: [{"outcome": rng.choice(UNANSWERED)}, {"outcome": rng.choice(UNANSWERED)}] for day in (TUE, WED, THU, FRI)}
        never[SAT] = [{"outcome": R.RNR}]
        hero(demo, MON, "ravi", 14, 50, never, name="Prasad Varma", category="lead", phone=p_pv,
             desc="Gave his number at the bus stand, wants a loan for a flat")
        hero(demo, WED, "srinivas", 17, 5, None, key="Prasad Varma #2", name="Prasad Varma", category="lead", phone=p_pv,
             desc="Met at Kanuru, interested in a home loan")
        hero(demo, MON, "kiran", 15, 30, {TUE: [{"outcome": R.RNR}]}, name="Balaji Constructions", category="dsa_connector",
             desc="Small builder, could refer buyers")
        hero(demo, MON, "padma", 16, 0, {TUE: [{"outcome": "Callback requested", "next_date": str(THU)}],
                                          THU: [{"outcome": C, "answers": ans(THU, "Rajesh Kumar", loan_need="Plot + construction", next_step="SO / branch visit")}]},
             name="Rajesh Kumar", category="lead", desc="Busy at work, asked to be called on Thursday")
        hero(demo, TUE, "saiteja", 12, 20, {WED: [{"outcome": C, "answers": ans(WED, "Sri Sai Cements", needs_home_loan="Yes", loan_need="Self-construction",
                                                                                 next_step="SO / branch visit"),
                                                    "card": lead_card("Self-construction", "Nellore", "TCS-L-208831", loan_requirement=1_800_000)}]},
             name="Sri Sai Cements", category="contact_point", subtype="Sand / Gravel / Brick Shop",
             desc="Cement dealer; also building his own house")
        p_mk = new_phone()
        hero(demo, TUE, "ravi", 13, 35, {WED: [{"outcome": "Wrong person"}], FRI: [{"outcome": C, "answers": ans(FRI, "Mohan Krishna", next_step="SO / branch visit")}]},
             name="Mohan Krishna", category="lead", phone=p_mk, desc="Wants to buy a house in Bhavanipuram")
        hero(demo, THU, "padma", 13, 15, {FRI: [{"outcome": "Wrong person"}]}, name="Durga Prasad", category="lead",
             desc="Wants a loan to build on his father's plot")
        hero(demo, MON, "srinivas", 11, 45, {TUE: [{"outcome": C, "answers": ans(TUE, "Bhaskar Rao", loan_need="Self-construction", next_step="SO / branch visit"),
                                                    "card": lead_card("Self-construction", "Vijayawada", "TCS-L-311209", loan_requirement=600_000)}]},
             name="Bhaskar Rao", category="lead", desc="Daily-wage mason, wants to build two rooms on his own plot")
        hero(demo, WED, "ravi", 12, 10, {THU: [{"outcome": C, "answers": ans(THU, "Kavitha Devi", loan_need="Home purchase", next_step="SO / branch visit"),
                                                "card": lead_card("Home purchase", "Vijayawada", "TCS-L-415577", loan_requirement=1_200_000)}]},
             name="Kavitha Devi", category="lead", desc="Tailor, wants to buy a small house in Gunadala")
        hero(demo, TUE, "padma", 14, 25, {WED: [{"outcome": C, "answers": ans(WED, "Venu Gopal", next_step="SO / branch visit")}]},
             name="Venu Gopal", category="lead", desc="Works in Hyderabad, home every month")
        hero(demo, TUE, "srinivas", 15, 40, {WED: [{"outcome": C, "answers": ans(WED, "Swathi Reddy", next_step="SO / branch visit")}],
                                             FRI: [{"outcome": C, "answers": ans(FRI, "Swathi Reddy", next_step="SO / branch visit",
                                                                                remarks="Reachable after 6 pm; asked the branch to call then")}]},
             name="Swathi Reddy", category="lead", desc="Nurse, night shifts; wants a flat near the hospital")
        hero(demo, TUE, "ravi", 16, 30, {WED: [{"outcome": C, "answers": ans(WED, "Ramu Yadav", next_step="SO / branch visit")}]},
             name="Ramu Yadav", category="prospect", desc="Saving up, may buy a house next year")
        hero(demo, MON, "padma", 10, 50, {TUE: [{"outcome": C, "answers": ans(TUE, "Sambasiva Rao", next_step="SO / branch visit")}]},
             name="Sambasiva Rao", category="prospect", desc="Thinking of buying next year")
        hero(demo, MON, "saiteja", 15, 15, {TUE: [{"outcome": C, "answers": ans(TUE, "Lakshmi Narayana", next_step="SO / branch visit")}]},
             name="Lakshmi Narayana", category="lead", desc="Wants to buy a flat in Magunta Layout")
        hero(demo, TUE, "kiran", 14, 5, {WED: [{"outcome": C, "answers": ans(WED, "Gopi Krishna", next_step="SO / branch visit")}]},
             name="Gopi Krishna", category="lead", desc="Shop owner, wants a construction loan")
        hero(demo, MON, "naresh", 12, 0, {TUE: [{"outcome": C, "answers": ans(TUE, "Siva Kumar", kind="missing")}],
                                          THU: [{"outcome": C, "answers": ans(THU, "Siva Kumar", loan_need="Improvement or extension", next_step="SO / branch visit")}]},
             name="Siva Kumar", category="lead", desc="Wants to add a room to his house")
        hero(demo, TUE, "lakshmi", 10, 35, {WED: [{"outcome": C, "answers": ans(WED, "Anjali Devi", kind="red")}]},
             name="Anjali Devi", category="lead", desc="Asked about loans for her son's house")
        hero(demo, MON, "srinivas", 13, 20, {TUE: [{"outcome": C, "answers": ans(TUE, "Krishna Murthy", next_step="Call centre to continue")}],
                                             WED: [{"outcome": C, "answers": ans(WED, "Krishna Murthy", kind="red",
                                                                                 remarks="Took a loan from a local bank last week")}]},
             name="Krishna Murthy", category="lead", desc="Comparing banks for a construction loan")
        p_rb = new_phone()
        hero(demo, MON, "kiran", 11, 10, {TUE: [{"outcome": C, "answers": ans(TUE, "Ravindra Babu", loan_need="LAP", next_step="SO / branch visit")}]},
             name="Ravindra Babu", category="lead", phone=p_rb, desc="Wants money for his business against his house")
        p_ur = new_phone()
        hero(demo, TUE, "lakshmi", 15, 50, {WED: [{"outcome": C, "answers": ans(WED, "Usha Rani", next_step="SO / branch visit")}]},
             name="Usha Rani", category="lead", phone=p_ur, desc="Said her file is moving at a branch")
        hero(demo, FRI, "saiteja", 9, 40, None, name="Chandra Sekhar", category="lead",
             desc="Met at the tea stall, wants a home loan", last_contact=at(FRI, 9, 55), delay_s=45 * 60)
        hero(demo, WED, "srinivas", 14, 15, {THU: [{"outcome": C, "answers": ans(THU, "Narasimha Rao", next_step="SO / branch visit")}]},
             name="Narasimha Rao", category="lead", desc="Padma's contact, met together at the site")
        hero(demo, TUE, "ravi", 11, 55, {WED: [{"outcome": C, "answers": ans(WED, "Pradeep Kumar", next_step="SO / branch visit"),
                                                "card": lead_card("Home purchase", "Guntur", "TCS-L-517903", loan_requirement=2_800_000,
                                                                  handling_branch_id=str(demo.branch["Guntur"]))}]},
             name="Pradeep Kumar", category="lead", desc="Lives in Vijayawada, buying a house in Guntur")

        # ------------------------------------------------ Monday: roster, attendance, first entries
        CLOCK.day = MON
        await demo.roster(with_exit=False)
        await stamp(at(MON, 8, 40))
        async with SessionLocal() as s:  # the demo SOs sign in with the demo password
            await s.execute(update(User).where(User.employee_code.in_([p.emp for p in SOS]))
                            .values(password_hash=hash_password(PW), must_change_password=False))
            await s.commit()
        await stamp(at(MON, 8, 41))
        await demo.load_ids()

        for i, d in enumerate(WEEK):
            CLOCK.day = d
            api.tokens.clear()
            if d != SUN:
                await demo.attendance(d, at(d, 10, 30))
            if i > 0 and d != SUN:
                await demo.calling_day(d, first=(i == 1), leave_unworked={FARHAN.emp: 3} if d == FRI else None)
                await demo.branch_day(d, scripted=BRANCH_SCRIPT.get(d, {}))
                await afternoon(demo, d)
            await demo.entries_for(d)
            print(f"{d:%a %d %b}: {len(demo.entries)} entries so far", flush=True)

        # ------------------------------------------------ today's attendance, the leaver, a phone clock ahead
        CLOCK.day = TODAY
        api.tokens.clear()
        await demo.roster(with_exit=True)
        await stamp(at(SAT, 12, 15))
        await demo.attendance(TODAY, None)
        ahead = datetime.now(IST) + timedelta(minutes=25)
        e = await demo.make_entry(SO["ravi"], ahead.date(), ahead.hour, ahead.minute, "lead", name="Bhavani Shankar",
                                  desc="Met at the bank; his phone clock was wrong", delay_s=-25 * 60)
        await stamp.conn.execute("""
            update entry_events ev set detail = jsonb_set(ev.detail, '{synced_after_s}',
                to_jsonb(greatest(0, extract(epoch from e.received_at_server - e.submitted_at_device))::int))
            from sankalp_entries e where ev.entry_id = e.id and ev.kind = 'created' and ev.detail ? 'synced_after_s'""")
        print("\nNamed examples:")
        for name, ex in sorted(demo.heroes.items()):
            print(f"  {name:<30} {ex['entry_code']}")
        print(f"  {'Bhavani Shankar':<30} {e['entry_code']}")
        # Section 10, live: a one-row login register for Hanumantha Rao's number (Sai Teja's validated entry and
        # Padma's later one, not called). Uploaded in the demo, both log in, and "first validation" stays with the
        # earliest. Built here so the number and the login date (today) always fit this week's data.
        Path("/tmp/login-register-live.csv").write_text(
            "TCS ID,Customer contact,Login date,Product,Final status,Source,Emp code\n"
            f"4851410,{demo.heroes['Hanumantha Rao']['phone_clean']},{TODAY},Home Loan,Logged in,Sankalp,AHFL90006\n",
            encoding="utf-8")
        print("\nLogin registers for sections 10 and 11: /tmp/login-register-live.csv and /tmp/login-register-saturday.csv"
              " in the backend container")
    await stamp.conn.close()


# ---------------------------------------------------------------- the branch's scripted answers (12.4)
BRANCH_SCRIPT = {
    WED: {"Venkata Ramana": ("A1", FRI, "KYC of the co-applicant pending"),
          "Bhaskar Rao": ("R2", None, "Income too low for the amount"),
          "Sambasiva Rao": ("2", None, "Customer is ready to buy now: a Lead, not a Prospect")},
    THU: {"Venu Gopal": ("E2", working_after(THU, 18), "Customer in Hyderabad until the 20th"),
          "Swathi Reddy": ("3", None, "Not picking up the branch's calls"),
          "Ramu Yadav": ("2", None, "Has his down payment ready: a Lead, not a Prospect"),
          "Pradeep Kumar": ("F1", SAT, "BM visit to the Guntur property")},
    SAT: {"Mohan Krishna": ("3", None, "Customer not answering the branch since Friday")},
    FRI: {"Kavitha Devi": ("R3", None, "CIBIL below our cut-off"),
          "Lakshmi Prasanna": ("C3", working_after(SAT, 1), "Login fixed for Monday")},
}


async def afternoon(demo: Demo, d: date):
    """What the master owner, the monitor and the managers do after the calls."""
    H = demo.heroes
    api = demo.api
    if d == WED:  # an "answers missing" call is reopened for calling
        await api.call("PUT", MASTER, f"/calls/entries/{H['Siva Kumar']['id']}/tracker",
                       json={"owner": "call_centre", "outcome": "Reopen for calling", "notes": "Loan need not asked; call again"})
        await stamp(at(d, 16, 10))
    if d == THU:
        gc = await api.call("GET", MASTER, "/calls/green-channel")
        for g in gc:
            if g["entry_id"] == H["Bhaskar Rao"]["id"]:  # head office: within ₹8 lakh, not rejected; back to the branch
                await api.call("POST", MASTER, f"/calls/green-channel/{g['answer_id']}", json={"accept_reject": False})
                await stamp(at(d, 12, 20))
        await api.call("POST", MONITOR, f"/monitor/category-review/{H['Sambasiva Rao']['id']}",
                       json={"category": "lead", "note": "Checked with the branch: ready to buy now"})
        await stamp(at(d, 11, 5))
        await api.call("POST", BM, f"/entries/{H['Mohan Krishna']['id']}/correct-number", json={"phone": new_phone()})
        await stamp(at(d, 12, 40))
        await api.call("POST", RTM, f"/entries/{H['Narasimha Rao']['id']}/correct-so", json={"so_user_id": str(SO['padma'].id)})
        await stamp(at(d, 15, 30))
    if d == FRI:
        await api.call("PUT", MASTER, f"/calls/entries/{H['Lakshmi Narayana']['id']}/tracker",
                       json={"owner": "done", "outcome": "Logged in", "tcs_id": "4851377",
                             "notes": "Logged in at Nellore; mobile in the register is the wife's"})
        await stamp(at(d, 16, 5))
        await api.call("PUT", MASTER, f"/calls/entries/{H['Gopi Krishna']['id']}/tracker",
                       json={"owner": "done", "outcome": "Rejected", "reject_reason": "Loan taken elsewhere",
                             "notes": "Chose another lender (SBI)"})
        await stamp(at(d, 16, 15))
        await api.call("PUT", MASTER, f"/calls/entries/{H['Anjali Devi']['id']}/tracker",
                       json={"rag_override": "AMBER", "notes": "Son may need a loan after the harvest; check in January"})
        await stamp(at(d, 16, 25))
    if d == SAT:
        p_va = H["Venkata Ramana"]["phone_clean"]
        extra = [f"4851203,{new_phone()} / {p_va},{FRI},Home Loan,Logged in,Sankalp,AHFL90001",
                 f"4851288,{H['Ravindra Babu']['phone_clean']},{FRI},LAP,Logged in,Sankalp,AHFL90005",
                 f"4851290,{H['Usha Rani']['phone_clean']},{MON},Home Loan,Logged in,Branch walk-in,AHFL90002",
                 f"4851301,{new_phone()},{THU},Home Loan,Logged in,Branch walk-in,",
                 f"4851302,{new_phone()} & {new_phone()},{FRI},Home Loan,Logged in,DSA,"]
        res = await demo.login_register(d, extra)
        print("login register:", res.get("summary"), "| rows not used:", res.get("errors"))


if __name__ == "__main__":
    asyncio.run(main())
