"""Read models for the calling side of an entry: attempts, lead card, branch answers, tracker, same-number history."""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import BranchAnswer, CallAllocation, CallAttempt, FollowupTracker, LeadCard, SankalpEntry, User
from app.security.rbac import has_perm
from app.services.sankalp import engine as E
from app.services.sankalp import rules as R


async def _names(s: AsyncSession, ids) -> dict:
    ids = {i for i in ids if i}
    if not ids:
        return {}
    return dict((await s.execute(select(User.id, User.full_name).where(User.id.in_(ids)))).all())


async def calling_detail(s: AsyncSession, user: User, e: SankalpEntry) -> dict:
    attempts = (await s.execute(select(CallAttempt).where(CallAttempt.entry_id == e.id)
                                .order_by(CallAttempt.created_at))).scalars().all()
    answers = (await s.execute(select(BranchAnswer).where(BranchAnswer.entry_id == e.id)
                               .order_by(BranchAnswer.created_at))).scalars().all()
    card = await s.get(LeadCard, e.id)
    tracker = await s.get(FollowupTracker, e.id)
    allocations = (await s.execute(select(CallAllocation).where(CallAllocation.entry_id == e.id, CallAllocation.status == "open")
                                   )).scalars().all()
    names = await _names(s, [a.caller_id for a in attempts] + [b.answered_by for b in answers]
                         + [e.first_caller_id] + [a.caller_id for a in allocations] + ([tracker.caller_id] if tracker else []))
    out = {
        "first_caller": names.get(e.first_caller_id),
        # a DSA/CP contact who needs a home loan himself is called with the Lead questions and rules from then on
        "converted": e.call_group == "dsa_cp" and E.is_converted(attempts),
        "on_list_of": [{"caller_id": str(a.caller_id) if a.caller_id else None, "caller": names.get(a.caller_id),
                        "kind": a.kind, "run_date": a.run_date} for a in allocations],
        "attempts": [{"id": str(a.id), "call_date": a.call_date, "slot": a.slot, "outcome": a.outcome, "cycle": a.cycle,
                      "next_date": a.next_date, "answers": a.answers, "row_status": a.row_status,
                      "caller": names.get(a.caller_id), "at": a.created_at} for a in attempts],
        "lead_card": None if not card else {
            **card.data, "handling_branch_id": str(card.handling_branch_id) if card.handling_branch_id else None,
            "loan_requirement": card.loan_requirement, "lead_id": card.lead_id, "lead_id_at": card.lead_id_at},
        "branch_answers": [{"id": str(b.id), "code": b.code, "meaning": R.BRANCH_CODES.get(b.code, ("", None))[0],
                            "answer_date": b.answer_date, "responded_on": b.responded_on, "note": b.note,
                            "by": names.get(b.answered_by), "green_channel": b.green_channel} for b in answers],
        "tracker": None,
        "same_number": [],
    }
    if tracker and (has_perm(user.role, "calls.manage") or has_perm(user.role, "calls.work")):
        out["tracker"] = {"owner": tracker.owner, "action_type": tracker.action_type,
                          "caller_id": str(tracker.caller_id) if tracker.caller_id else None,
                          "caller": names.get(tracker.caller_id), "followup_date": tracker.followup_date,
                          "outcome": tracker.outcome, "tcs_id": tracker.tcs_id, "reject_reason": tracker.reject_reason,
                          "rag_override": tracker.rag_override, "immediate_callback": tracker.immediate_callback,
                          "notes": tracker.notes, "updated_at": tracker.updated_at}
    if has_perm(user.role, "calls.work") or has_perm(user.role, "calls.manage"):
        # the call centre sees every earlier contact with this number (any SO) before dialling
        others = (await s.execute(select(SankalpEntry, User.full_name).join(User, User.id == SankalpEntry.so_user_id)
                                  .where(SankalpEntry.company_id == e.company_id, SankalpEntry.phone == e.phone,
                                         SankalpEntry.id != e.id).order_by(SankalpEntry.submitted_at_device))).all()
        out["same_number"] = [{"id": str(o.id), "entry_code": o.entry_code, "so_name": n, "entry_date": o.entry_date,
                               "category": R.CATEGORIES.get(o.category), "status": o.status or o.selection_status,
                               "rag": o.rag_override or o.rag} for o, n in others]
    return out
