"""After the call: branch answers (12.4), corrections (13), the master owner's tracker (13.3), the login register (11)."""
import uuid
from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    Branch,
    BranchAnswer,
    CallAttempt,
    CpSubtype,
    FollowupTracker,
    ImportBatch,
    LeadCard,
    LoginRegisterRow,
    SankalpEntry,
    User,
)
from app.services.phone import clean_phone, is_valid_phone, split_contacts
from app.services.sankalp import engine as E
from app.services.sankalp import rules as R
from app.services.sankalp.ops import (
    company_today,
    event,
    put_on_list_now,
    recompute,
    recompute_many,
    recompute_phone_group,
)
from app.services.sankalp.schemas import BranchAnswerIn, TrackerIn
from app.services.scope import visible_branch_ids
from app.services.settings import load_settings
from app.services.tabular import column_name, parse_date, pick, row_error, text


# ================================================================ 12.4 branch answers
async def branch_has_bm(s: AsyncSession, branch_id: uuid.UUID) -> bool:
    return (await s.execute(select(User.id).where(User.branch_id == branch_id, User.role == "branch_manager",
                                                  User.status == "active").limit(1))).first() is not None


async def can_answer_for(s: AsyncSession, user: User, e: SankalpEntry) -> bool:
    """The BM answers for its branch; the RBH answers for a branch of its region that has no BM. The branch is the
    lead's handling branch (7.4) when the call centre gave one, else the SO's branch."""
    work = e.work_branch_id or e.branch_id
    if user.role == "branch_manager":
        return work in (await visible_branch_ids(s, user) or set())
    if user.role == "region_manager":
        b = await s.get(Branch, work)
        return bool(b and b.region_id == user.region_id and not await branch_has_bm(s, b.id))
    return False


async def answer_lead(s: AsyncSession, e: SankalpEntry, user: User, body: BranchAnswerIn) -> BranchAnswer:
    if not await can_answer_for(s, user, e):
        raise HTTPException(403, {"code": "not_your_branch", "message": "Only the branch's BM (or the RBH where there is no BM) answers this lead"})
    if e.so_action not in R.BRANCH_LEAD_ACTIONS and e.cc_action != R.CC_FOLLOW_UP:
        raise HTTPException(409, {"code": "not_a_branch_lead", "message": "This entry has no open lead action for the branch"})
    cfg = await load_settings(s, e.company_id)
    today = await company_today(s, e.company_id)
    if body.answer_date and body.answer_date < today:
        raise HTTPException(422, {"code": "date_in_past", "message": "The date must be today or later"})
    card = await s.get(LeadCard, e.id)
    st_answers = (await _latest_answers(s, e))
    green = E.green_channel(st_answers, card.loan_requirement if card else None,
                            E.Settings(construction_limit=cfg.green_channel_construction_limit,
                                       purchase_limit=cfg.green_channel_purchase_limit))
    a = BranchAnswer(company_id=e.company_id, entry_id=e.id, code=body.code, answer_date=body.answer_date,
                     responded_on=today, note=body.note, answered_by=user.id,
                     green_channel="pending" if green and body.code in R.GREEN_CHANNEL_PROTECTED else None)
    s.add(a)
    if body.code == "2":  # category wrong: goes to the Sankalp monitor
        e.category_review = "pending"
    event(s, e, "branch_answer", user.id, code=body.code, date=body.answer_date, green_channel=a.green_channel)
    await s.flush()
    await recompute(s, e, cfg=cfg, today=today)
    if e.priority:  # code 3: the customer is not answering the branch: the call centre retries at once (6.2)
        await put_on_list_now(s, e, today)
    return a


async def _latest_answers(s: AsyncSession, e: SankalpEntry) -> dict | None:
    last = (await s.execute(select(CallAttempt).where(CallAttempt.entry_id == e.id, CallAttempt.outcome == R.CONNECTED)
                            .order_by(CallAttempt.created_at.desc()).limit(1))).scalar_one_or_none()
    return last.answers if last else None


async def review_green_channel(s: AsyncSession, answer: BranchAnswer, user: User, accept_reject: bool) -> SankalpEntry:
    """Head-office check of an R2/R3 on a green-channel lead. Not accepted (the default rule): the lead goes back
    to the branch to log in, and credit decides. Accepted: the reject stands."""
    if answer.green_channel != "pending":
        raise HTTPException(409, "This answer is not waiting for a green-channel check")
    answer.green_channel = "accepted" if accept_reject else "returned"
    answer.reviewed_by, answer.reviewed_at = user.id, datetime.now(timezone.utc)
    e = await s.get(SankalpEntry, answer.entry_id)
    event(s, e, "green_channel", user.id, decision=answer.green_channel)
    await s.flush()
    await recompute(s, e)
    return e


# ================================================================ 13 corrections
async def correct_number(s: AsyncSession, e: SankalpEntry, user: User, new_phone_raw: str) -> SankalpEntry:
    """13.2: the right number, given through the BM or RTM while the "Correct customer number" action is open
    (15 days from the call that found the wrong number, as the Takeoff master). The entry is called again
    automatically with a fresh count of tries; the Entry ID stays."""
    if user.role == "region_manager":
        # The BM or RTM corrects numbers; the RBH steps in only for a branch that has neither (as for answers, 12.4).
        b = await s.get(Branch, e.branch_id)
        if not b or b.region_id != user.region_id or b.cluster_id or await branch_has_bm(s, b.id):
            raise HTTPException(403, {"code": "bm_or_rtm_corrects",
                                      "message": "This branch's BM or RTM corrects its numbers (the RBH only where it has neither)"})
    cfg = await load_settings(s, e.company_id)
    today = await company_today(s, e.company_id)
    if e.so_action != R.ACT_CORRECT_NUMBER or (e.so_action_until and e.so_action_until < today):
        raise HTTPException(409, {"code": "no_correction_open",
                                  "message": "This entry has no open 'Correct customer number' action (it is open for "
                                             f"{cfg.correct_number_window_days} days from the call)"})
    phone = clean_phone(new_phone_raw)
    if not is_valid_phone(phone):
        raise HTTPException(422, {"code": "invalid_phone", "message": "Enter a valid 10-digit mobile number starting with 6, 7, 8 or 9"})
    if phone == e.phone:
        raise HTTPException(422, {"code": "same_phone", "message": "That is the number already on the entry"})
    old = e.phone
    e.phone, e.phone_raw = phone, new_phone_raw.strip()[:50]
    e.call_cycle += 1
    if e.selection_status in (None, R.NC_NO_NUMBER):
        e.selection_status = R.ALLOCATE
    event(s, e, "correction.number", user.id, old=old, new=phone, cycle=e.call_cycle)
    await s.flush()
    await recompute(s, e, cfg=cfg, today=today)
    await recompute_phone_group(s, e.company_id, old)
    await put_on_list_now(s, e, today, kind="retry")  # 13.2: called again at once, by the caller who first handled it
    return e


async def correct_so(s: AsyncSession, e: SankalpEntry, user: User, so_user_id: uuid.UUID) -> SankalpEntry:
    """13.1: the RTM (or the BM where the branch has no cluster) or the monitor confirms the right SO. The Entry ID
    stays; the SO and, if needed, the branch (and so the region) change; counts and credit follow the new SO."""
    if user.role == "branch_manager":
        b = await s.get(Branch, e.branch_id)
        if b and b.cluster_id:
            raise HTTPException(403, {"code": "rtm_corrects", "message": "This branch has a cluster: its RTM corrects the SO"})
    so = await s.get(User, so_user_id)
    if not so or so.company_id != e.company_id or so.role != "sales_officer" or not so.branch_id:
        raise HTTPException(422, {"code": "not_a_sales_officer", "message": "Pick a Sales Officer on the roster"})
    if so.id == e.so_user_id:
        raise HTTPException(422, {"code": "same_so", "message": "That SO is already on the entry"})
    if user.role in ("branch_manager", "cluster_manager"):
        if so.branch_id not in (await visible_branch_ids(s, user) or set()):
            raise HTTPException(403, {"code": "outside_scope", "message": "That SO is not in your branches"})
    old_so, old_branch = e.so_user_id, e.branch_id
    e.so_user_id, e.branch_id, e.spoke = so.id, so.branch_id, so.spoke
    event(s, e, "correction.so", user.id, old_so=old_so, new_so=so.id, old_branch=old_branch, new_branch=so.branch_id)
    await s.flush()
    await recompute(s, e)
    return e


async def review_category(s: AsyncSession, e: SankalpEntry, user: User, category: str | None,
                          cp_subtype_id: uuid.UUID | None, note: str | None) -> SankalpEntry:
    """Branch code 2 ("category wrong") lands with the Sankalp monitor, who fixes the category or keeps it."""
    if e.category_review != "pending":
        raise HTTPException(409, "This entry is not waiting for a category review")
    old = e.category
    if category and category != e.category:
        if category not in R.CATEGORIES:
            raise HTTPException(422, "Unknown category")
        sub = None
        if category == "contact_point":
            sub = await s.get(CpSubtype, cp_subtype_id) if cp_subtype_id else None
            if not sub or sub.company_id != e.company_id:
                raise HTTPException(422, "Choose the CP sub-type")
        e.category, e.call_group = category, R.CALL_GROUP[category]
        e.cp_subtype_id, e.cp_subtype_label = (sub.id, sub.label) if sub else (None, None)
    e.category_review = "done"
    event(s, e, "category_review", user.id, old=old, new=e.category, note=note)
    await s.flush()
    await recompute(s, e)
    return e


# ================================================================ 13.3 tracker
async def save_tracker(s: AsyncSession, e: SankalpEntry, user: User, body: TrackerIn) -> FollowupTracker:
    if body.caller_id:
        c = await s.get(User, body.caller_id)
        if not c or c.company_id != e.company_id or c.role != "caller":
            raise HTTPException(422, "Pick a caller")
    tr = await s.get(FollowupTracker, e.id)
    if body.outcome == R.TRACKER_RETURN_GREEN:
        # the same as "Return to branch" on the Green channel page: the branch's R2/R3 is not accepted
        held = (await s.execute(select(BranchAnswer).where(BranchAnswer.entry_id == e.id,
                                                           BranchAnswer.green_channel == "pending")
                                .order_by(BranchAnswer.created_at.desc()).limit(1))).scalar_one_or_none()
        if held:
            held.green_channel, held.reviewed_by, held.reviewed_at = "returned", user.id, datetime.now(timezone.utc)
            event(s, e, "green_channel", user.id, decision="returned", via="tracker")
        # with no R2/R3 waiting, the master owner can still send the lead back to the branch (the Takeoff master)
    if tr is None:
        tr = FollowupTracker(entry_id=e.id, company_id=e.company_id)
        s.add(tr)
    for k, v in body.model_dump().items():
        setattr(tr, k, v.strip() if isinstance(v, str) else v)
    tr.tcs_id = tr.tcs_id or None
    tr.updated_by, tr.updated_at = user.id, datetime.now(timezone.utc)
    event(s, e, "tracker", user.id, owner=body.owner, outcome=body.outcome, followup_date=body.followup_date,
          tcs_id=body.tcs_id, rag_override=body.rag_override)
    await s.flush()
    await recompute(s, e)
    # called today only when due today: a PRIORITY entry, or a reopen whose date is today or earlier
    today = await company_today(s, e.company_id)
    reopen_due = body.outcome == R.TRACKER_REOPEN and e.status == R.IN_RETRY and (e.callback_date or today) <= today
    if e.priority or reopen_due:
        await put_on_list_now(s, e, today, kind="priority" if e.priority else "retry")
    return tr


# ================================================================ 11 login register
REGISTER_COLUMNS = {
    "tcs_id": ["tcs id", "tcs lead id", "application id", "app id", "lan", "tcs"],
    # the MIS file's own heading is "Applicant Contact No (Customer)"
    "contact": ["customer contact", "applicant contact no customer", "applicant contact no", "applicant contact number",
                "applicant contact", "applicant mobile", "contact", "mobile", "mobile number", "phone", "contact number",
                "customer mobile"],
    "login_date": ["login date", "logged in date", "date of login", "login dt"],
    "product": ["product", "product type", "product name"],
    "final_status": ["final status", "status"],
    "source": ["source", "lead source", "sourcing"],
    "emp_code": ["emp code", "emp id", "employee code", "so code", "sourcing emp code"],
}


async def import_register(s: AsyncSession, user: User, filename: str, rows: list[dict], dry_run: bool) -> dict:
    """Saves the register rows (every upload is kept: for a TCS ID seen more than once, the latest row wins by
    default), then recomputes every entry whose phone appears in a changed row."""
    errors, parsed = [], []
    col = {k: column_name(rows, a) for k, a in REGISTER_COLUMNS.items()}
    for row in rows:
        n = row["_row"]
        tcs = text(pick(row, REGISTER_COLUMNS["tcs_id"]), 50)
        if not tcs:
            errors.append(row_error(n, col["tcs_id"], "", "TCS ID is empty. Every login needs its TCS ID"))
            continue
        try:
            login_date = parse_date(pick(row, REGISTER_COLUMNS["login_date"]))
        except ValueError as e:
            errors.append(row_error(n, col["login_date"], pick(row, REGISTER_COLUMNS["login_date"]), str(e), tcs_id=tcs))
            continue
        raw_contact = pick(row, REGISTER_COLUMNS["contact"])
        phones = split_contacts(raw_contact)
        if not phones:
            errors.append(row_error(n, col["contact"], raw_contact, "No valid 10-digit mobile number (starting 6-9) in this "
                                    "cell, so no entry can be matched. The row is kept; the Master owner can enter the "
                                    "TCS ID on the entry by hand", tcs_id=tcs))
        parsed.append(LoginRegisterRow(
            company_id=user.company_id, row_no=n, tcs_id=tcs.upper(), contacts_raw=text(raw_contact, 300), phones=phones,
            login_date=login_date, product=text(pick(row, REGISTER_COLUMNS["product"]), 100),
            final_status=text(pick(row, REGISTER_COLUMNS["final_status"]), 100),
            source=text(pick(row, REGISTER_COLUMNS["source"]), 100), emp_code=text(pick(row, REGISTER_COLUMNS["emp_code"]), 50)))
    tcs_ids = {r.tcs_id for r in parsed}
    phones = {p for r in parsed for p in r.phones}
    # phones of earlier rows of the same TCS IDs: a newer row may take the TCS ID away from them
    if tcs_ids:
        for old in (await s.execute(select(LoginRegisterRow.phones).where(
                LoginRegisterRow.company_id == user.company_id, LoginRegisterRow.tcs_id.in_(tcs_ids)))).scalars():
            phones.update(old or [])
    matched = 0
    if phones:
        matched = (await s.execute(select(SankalpEntry.id).where(SankalpEntry.company_id == user.company_id,
                                                                 SankalpEntry.phone.in_(phones)))).all()
        matched = len(matched)
    summary = {"rows": len(parsed), "tcs_ids": len(tcs_ids), "numbers": len(phones), "entries_matched": matched,
               "errors": len(errors)}
    if dry_run:
        return {"dry_run": True, "summary": summary, "errors": errors[:1000]}
    batch = ImportBatch(company_id=user.company_id, kind="login_register", filename=filename[:255], uploaded_by=user.id,
                        rows_total=len(rows), rows_ok=len(parsed), rows_error=len(rows) - len(parsed),
                        summary=summary, errors=errors[:1000])
    s.add(batch)
    await s.flush()
    for r in parsed:
        r.batch_id = batch.id
        s.add(r)
    await s.flush()
    if phones:
        await recompute_many(s, user.company_id, SankalpEntry.phone.in_(phones))
    # entries holding one of these TCS IDs through a phone no longer in the register lose it
    if tcs_ids:
        await recompute_many(s, user.company_id, or_(SankalpEntry.tcs_id.in_(tcs_ids)))
    return {"dry_run": False, "summary": summary, "errors": errors[:1000], "batch_id": str(batch.id)}
