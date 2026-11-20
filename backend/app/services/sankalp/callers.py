"""Caller allocation by language, absence and a daily limit (Aham, Nov 2026; beyond the Takeoff master, whose
Allocation sheet only flags a branch with no caller).

- A branch has the languages spoken in its area; a caller has the languages they speak. A caller can take a branch
  when they share a language (a branch with no language set takes anyone).
- The Master owner marks a caller absent for a day: that caller's branches are flagged with a suggested caller.
- Every caller has a daily limit on their list (new entries, retries, PRIORITY and follow-ups together). A caller
  over it is flagged with suggested moves to a caller who speaks the language and has room. The Master owner applies
  suggestions with one click; nothing moves by itself.

Pure functions over plain data, so each rule is table-tested.
"""
from dataclasses import dataclass, field
from typing import Hashable


@dataclass
class BranchToday:
    id: Hashable
    name: str
    region: str | None
    languages: list[str]
    usual: Hashable | None  # the caller who usually takes the branch
    today: Hashable | None  # the caller of the day, when set
    waiting: int = 0  # new entries waiting for the daily selection (projected onto the branch's caller)
    fresh_open: dict = field(default_factory=dict)  # caller id (None: no caller) -> new entries on a list, not called yet


@dataclass
class CallerToday:
    id: Hashable
    name: str
    languages: list[str]
    active: bool = True
    absent: bool = False
    load: int = 0  # today's open list: new entries, retries, PRIORITY and follow-ups


def speaks(caller_languages: list[str], branch_languages: list[str]) -> bool:
    if not branch_languages:
        return True
    return bool({x.strip().lower() for x in caller_languages} & {x.strip().lower() for x in branch_languages})


def available(c: CallerToday | None) -> bool:
    return bool(c and c.active and not c.absent)


def holder(b: BranchToday):
    """Who takes the branch today: its caller of the day, else its usual caller."""
    return b.today if b.today is not None else b.usual


def loads(branches: list[BranchToday], callers: list[CallerToday]) -> dict:
    """Each caller's list today, with the new entries still waiting for the selection counted on the branch's caller."""
    out = {c.id: c.load for c in callers}
    for b in branches:
        h = holder(b)
        if h in out:
            out[h] += b.waiting
    return out


def best_caller(b: BranchToday, callers: list[CallerToday], load: dict, limit: int, exclude=(), held: dict | None = None):
    """The present caller who speaks a branch language and has the most room (then fewer branches, then the name).
    A caller with no languages set is never suggested."""
    held = held or {}
    ok = [c for c in callers if available(c) and c.languages and speaks(c.languages, b.languages) and c.id not in exclude]
    if not ok:
        return None
    return min(ok, key=lambda c: (-(limit - load.get(c.id, 0)), held.get(c.id, 0), c.name))


def _branch_counts(branches: list[BranchToday]) -> dict:
    out: dict = {}
    for b in branches:
        h = holder(b)
        if h is not None:
            out[h] = out.get(h, 0) + 1
    return out


def flags_for(b: BranchToday, c: CallerToday | None, load: dict, limit: int) -> list[dict]:
    langs = " / ".join(b.languages) or "the branch's language"
    if c is None:
        n = b.waiting + b.fresh_open.get(None, 0)
        return [{"code": "no_caller", "message": f"No caller – {n} new {'entry is' if n == 1 else 'entries are'} not allocated"
                 if n else "No caller"}]
    if not c.active:
        return [{"code": "inactive", "message": f"{c.name} is no longer a caller – change"}]
    if c.absent:
        return [{"code": "absent", "message": f"{c.name} is absent today – change the caller"}]
    out = []
    if c.languages and not speaks(c.languages, b.languages):  # no languages set: unknown, not wrong
        out.append({"code": "language", "message": f"{c.name} does not speak {langs}"})
    if load.get(c.id, 0) > limit:
        out.append({"code": "over_limit", "message": f"{c.name} is over the limit by {load[c.id] - limit}"})
    return out


def day_plan(branches: list[BranchToday], callers: list[CallerToday], limit: int) -> dict:
    """Per branch: who takes it, its flags and a suggested caller; per caller: load, room; and the moves that bring
    every caller over the limit back under it."""
    by_id = {c.id: c for c in callers}
    load = loads(branches, callers)
    held = _branch_counts(branches)
    rows = []
    for b in branches:
        c = by_id.get(holder(b))
        fl = flags_for(b, c, load, limit)
        needs_new = any(f["code"] in ("no_caller", "inactive", "absent", "language") for f in fl)
        sug = best_caller(b, callers, load, limit, exclude={c.id} if c else (), held=held) if needs_new else None
        rows.append({"branch": b, "caller": c, "flags": fl, "suggestion": sug})
    return {"branches": rows, "load": load, "moves": moves(branches, callers, limit, load)}


def moves(branches: list[BranchToday], callers: list[CallerToday], limit: int, load: dict | None = None) -> list[dict]:
    """For each present caller over the limit, largest branch first: move new entries already on their list but not
    called yet (after the run), or give the whole branch for the day (before the run, when its new entries are still
    waiting), to the caller who speaks the language and has the most room. Retries stay with their first caller."""
    load = dict(load or loads(branches, callers))
    held = _branch_counts(branches)
    out = []
    for c in sorted(callers, key=lambda c: -(load.get(c.id, 0) - limit)):
        over = load.get(c.id, 0) - limit
        if over <= 0 or not available(c):
            continue
        mine = [b for b in branches if holder(b) == c.id]
        for b in sorted(mine, key=lambda b: -(b.fresh_open.get(c.id, 0) + b.waiting)):
            if over <= 0:
                break
            d = best_caller(b, callers, load, limit, exclude={c.id}, held=held)
            room = limit - load.get(d.id, 0) if d else 0
            if not d or room <= 0:
                continue
            if b.fresh_open.get(c.id, 0):
                n = min(over, room, b.fresh_open[c.id])
                out.append({"kind": "entries", "from": c, "to": d, "branch": b, "count": n})
            elif b.waiting and b.waiting <= room:
                n = b.waiting
                out.append({"kind": "branch", "from": c, "to": d, "branch": b, "count": n})
            else:
                continue
            load[c.id] -= n
            load[d.id] = load.get(d.id, 0) + n
            over -= n
    return out


def auto_assign(branches: list[BranchToday], callers: list[CallerToday], limit: int) -> dict:
    """Today's caller for every branch, largest branch first: its usual caller when present and speaking the language,
    otherwise the present caller who speaks it with the most room. None when nobody can take it (it stays flagged)."""
    by_id = {c.id: c for c in callers}
    load = {c.id: c.load for c in callers}
    held: dict = {}
    out = {}
    for b in sorted(branches, key=lambda b: (-b.waiting, b.name)):
        u = by_id.get(b.usual)
        usual_ok = available(u) and (not u.languages or speaks(u.languages, b.languages))
        pick = u if usual_ok else best_caller(b, callers, load, limit, held=held)
        out[b.id] = pick.id if pick else None
        if pick:
            load[pick.id] += b.waiting
            held[pick.id] = held.get(pick.id, 0) + 1
    return out
