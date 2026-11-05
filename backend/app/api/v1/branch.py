"""Management portal hand-off (sections 12-13): the branch's leads and answers, corrections, the monitor's queues."""
import uuid
from datetime import date, timedelta

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_any_perm, require_perm
from app.api.v1.entries import entry_row, get_scoped_entry
from app.core.db import get_session
from app.models import Branch, BranchAnswer, Region, SankalpEntry, User
from app.services.sankalp import rules as R
from app.services.sankalp.handoff import answer_lead, branch_has_bm, correct_number, correct_so, review_category
from app.services.sankalp.ops import company_today
from app.services.sankalp.schemas import BranchAnswerIn
from app.services.scope import entry_scope, visible_branch_ids
from app.services.settings import load_settings

router = APIRouter(tags=["branch"])


WORK_BRANCH = func.coalesce(SankalpEntry.work_branch_id, SankalpEntry.branch_id)  # 7.4 handling branch, else the SO's


async def _page(s: AsyncSession, q, order, page: int, page_size: int) -> dict:
    """A list page with its total, so a screen can say "showing X of Y" (no silent row limit, section 15)."""
    total = (await s.execute(select(func.count()).select_from(q.subquery()))).scalar_one()
    rows = (await s.execute(q.order_by(*order).offset((page - 1) * page_size).limit(page_size))).all()
    return {"items": [entry_row(*r) for r in rows], "total": total, "page": page, "page_size": page_size}


def _joined():
    return (select(SankalpEntry, User, Branch, Region).join(User, User.id == SankalpEntry.so_user_id)
            .join(Branch, Branch.id == SankalpEntry.branch_id).outerjoin(Region, Region.id == Branch.region_id))


async def _latest_answers(s: AsyncSession, ids: list[uuid.UUID]) -> dict[uuid.UUID, BranchAnswer]:
    if not ids:
        return {}
    rows = (await s.execute(select(BranchAnswer).where(BranchAnswer.entry_id.in_(ids))
                            .order_by(BranchAnswer.entry_id, BranchAnswer.created_at))).scalars().all()
    return {a.entry_id: a for a in rows}  # the last one per entry wins


def _answer_dict(a: BranchAnswer | None, today: date) -> dict | None:
    if not a:
        return None
    return {"code": a.code, "meaning": R.BRANCH_CODES[a.code][0], "answer_date": a.answer_date,
            "responded_on": a.responded_on, "green_channel": a.green_channel,
            "missed": bool(a.answer_date and a.answer_date < today)}


@router.get("/branch/leads")
async def branch_leads(user: User = Depends(require_perm("branch.answer")), s: AsyncSession = Depends(get_session)):
    """Leads waiting for the branch: open lead actions (visit, documents, follow-up) and green-channel holds.
    A BM sees its branch; an RBH sees the branches of its region that have no BM."""
    today = await company_today(s, user.company_id)
    q = _joined().where(await entry_scope(s, user), or_(SankalpEntry.so_action.in_(R.LEAD_ACTIONS),
                                                         SankalpEntry.cc_action == R.CC_FOLLOW_UP))
    visible = await visible_branch_ids(s, user)
    if visible is not None:  # the branch that works the lead answers it (7.4 handling branch)
        q = q.where(WORK_BRANCH.in_(visible or {uuid.uuid4()}))
    # earliest action date first; ties by entry, so the list (and anything walking it) is always in the same order
    rows = (await s.execute(q.order_by(SankalpEntry.so_action_date.nulls_last(), SankalpEntry.submitted_at_device,
                                       SankalpEntry.entry_code))).all()
    if user.role == "region_manager":
        works = {r[0].work_branch_id or r[0].branch_id for r in rows}
        no_bm = {b for b in works if not await branch_has_bm(s, b)}
        rows = [r for r in rows if (r[0].work_branch_id or r[0].branch_id) in no_bm]
    answers = await _latest_answers(s, [r[0].id for r in rows])
    handling = dict((await s.execute(select(Branch.id, Branch.name).where(
        Branch.id.in_({r[0].work_branch_id for r in rows if r[0].work_branch_id} or {uuid.uuid4()})))).all())
    return {"today": today, "items": [{**entry_row(*r), "branch_answer": _answer_dict(answers.get(r[0].id), today),
                                       "handling_branch_name": handling.get(r[0].work_branch_id)} for r in rows]}


@router.post("/branch/leads/{entry_id}/answer", status_code=201)
async def post_answer(entry_id: uuid.UUID, body: BranchAnswerIn, user: User = Depends(require_perm("branch.answer")),
                      s: AsyncSession = Depends(get_session)):
    e = await get_scoped_entry(s, user, entry_id)
    a = await answer_lead(s, e, user, body)
    await s.commit()
    return {"answer_id": str(a.id), "green_channel": a.green_channel, "so_action": e.so_action,
            "so_action_date": e.so_action_date, "cc_action": e.cc_action, "cc_action_date": e.cc_action_date,
            "lead_outcome": e.lead_outcome, "priority": e.priority, "rag": e.rag_override or e.rag}


@router.get("/branch/actions")
async def so_actions(expired: bool = False, action: str | None = None, page: int = Query(1, ge=1),
                     page_size: int = Query(100, ge=1, le=500),
                     user: User = Depends(require_perm("entries.read")), s: AsyncSession = Depends(get_session)):
    """12.1: open SO / branch actions in my scope (correct a number, DSA/CP follow-up, lead actions). With
    expired=true: actions whose window (12.3) ran out before anyone acted on them. action: one action, or "lead"."""
    col = SankalpEntry.expired_action if expired else SankalpEntry.so_action
    q = _joined().where(await entry_scope(s, user), col.is_not(None))
    if action:
        q = q.where(col.in_(R.LEAD_ACTIONS) if action == "lead" else col == action)
    if expired:
        return await _page(s, q, [SankalpEntry.expired_on.desc(), SankalpEntry.entry_code], page, page_size)
    return await _page(s, q, [SankalpEntry.so_action_date.nulls_last(), SankalpEntry.entry_code], page, page_size)


@router.get("/branch/missed-dates")
async def missed_dates(user: User = Depends(require_any_perm("branch.answer", "dashboard.read")),
                       s: AsyncSession = Depends(get_session)):
    """12.4: per branch (the branch that works the lead), lead answers whose date has passed with no login and no
    newer answer. A date the 14-day rule gave to the call centre is the call centre's, not a branch miss, and a lead
    rejected since then is no longer waiting."""
    today = await company_today(s, user.company_id)
    cfg = await load_settings(s, user.company_id)
    latest = (select(BranchAnswer.entry_id, func.max(BranchAnswer.created_at).label("at"))
              .group_by(BranchAnswer.entry_id).subquery())
    q = (select(Branch.id, Branch.name, func.count())
         .select_from(BranchAnswer)
         .join(latest, and_(latest.c.entry_id == BranchAnswer.entry_id, latest.c.at == BranchAnswer.created_at))
         .join(SankalpEntry, SankalpEntry.id == BranchAnswer.entry_id).join(Branch, Branch.id == WORK_BRANCH)
         .where(await entry_scope(s, user), BranchAnswer.answer_date < today,
                BranchAnswer.answer_date <= BranchAnswer.responded_on + timedelta(days=cfg.branch_date_threshold_days),
                or_(SankalpEntry.lead_outcome.is_(None),
                    SankalpEntry.lead_outcome.notin_([R.LOGGED_IN, R.OUTCOME_REJECTED]))))
    visible = await visible_branch_ids(s, user)
    if visible is not None:  # a lead handled by another branch counts there, not on the SO's branch's page
        q = q.where(WORK_BRANCH.in_(visible or {uuid.uuid4()}))
    rows = (await s.execute(q.group_by(Branch.id, Branch.name).order_by(func.count().desc()))).all()
    return [{"branch_id": str(b), "branch": n, "missed": c} for b, n, c in rows]


# ---------------------------------------------------------------- corrections (13.1, 13.2)
class NumberIn(BaseModel):
    phone: str = Field(min_length=1, max_length=50)


class SoIn(BaseModel):
    so_user_id: uuid.UUID


@router.post("/entries/{entry_id}/correct-number")
async def post_correct_number(entry_id: uuid.UUID, body: NumberIn, user: User = Depends(require_perm("correct.number")),
                              s: AsyncSession = Depends(get_session)):
    e = await get_scoped_entry(s, user, entry_id)
    await correct_number(s, e, user, body.phone)
    await s.commit()
    return {"phone": e.phone, "status": e.status, "rag": e.rag_override or e.rag, "call_cycle": e.call_cycle}


@router.post("/entries/{entry_id}/correct-so")
async def post_correct_so(entry_id: uuid.UUID, body: SoIn, user: User = Depends(require_perm("correct.so")),
                          s: AsyncSession = Depends(get_session)):
    e = await get_scoped_entry(s, user, entry_id)
    await correct_so(s, e, user, body.so_user_id)
    await s.commit()
    return {"entry_code": e.entry_code, "so_user_id": str(e.so_user_id), "branch_id": str(e.branch_id)}


# ---------------------------------------------------------------- Sankalp monitor queues
@router.get("/monitor/category-review")
async def category_queue(page: int = Query(1, ge=1), page_size: int = Query(100, ge=1, le=500),
                         user: User = Depends(require_perm("category.review")), s: AsyncSession = Depends(get_session)):
    q = _joined().where(SankalpEntry.company_id == user.company_id, SankalpEntry.category_review == "pending")
    return await _page(s, q, [SankalpEntry.received_at_server], page, page_size)


class CategoryIn(BaseModel):
    category: str | None = None
    cp_subtype_id: uuid.UUID | None = None
    note: str | None = Field(None, max_length=500)


@router.post("/monitor/category-review/{entry_id}")
async def resolve_category(entry_id: uuid.UUID, body: CategoryIn, user: User = Depends(require_perm("category.review")),
                           s: AsyncSession = Depends(get_session)):
    e = await get_scoped_entry(s, user, entry_id)
    await review_category(s, e, user, body.category, body.cp_subtype_id, body.note)
    await s.commit()
    return {"category": e.category, "call_group": e.call_group, "category_review": e.category_review}


@router.get("/monitor/time-flags")
async def time_flags(page: int = Query(1, ge=1), page_size: int = Query(100, ge=1, le=500),
                     user: User = Depends(require_perm("category.review")), s: AsyncSession = Depends(get_session)):
    """Entries whose phone clock looked wrong when they were made: ahead of the server, or set back since the phone
    last reached the server (check the time)."""
    q = _joined().where(SankalpEntry.company_id == user.company_id, SankalpEntry.device_time_suspect)
    return await _page(s, q, [SankalpEntry.received_at_server.desc()], page, page_size)
