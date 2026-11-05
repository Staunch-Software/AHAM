"""Which branches, people and entries a signed-in user may see (the RBAC data scope)."""
import uuid

from sqlalchemy import and_, false, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.elements import ColumnElement

from app.models import Branch, CallAllocation, SankalpEntry, User, UserBranchAssignment
from app.security.rbac import ROLES


async def visible_branch_ids(s: AsyncSession, user: User) -> set[uuid.UUID] | None:
    """None means every branch of the company."""
    scope = ROLES[user.role].scope
    if scope == "company":
        return None
    if scope in ("own", "branch"):
        extra = (await s.execute(select(UserBranchAssignment.branch_id)
                                 .where(UserBranchAssignment.user_id == user.id))).scalars().all()
        return {b for b in [user.branch_id, *extra] if b}
    if scope == "cluster":
        cond = Branch.cluster_id == user.cluster_id if user.cluster_id else false()
    elif scope == "region":
        cond = Branch.region_id == user.region_id if user.region_id else false()
    else:  # allocated (callers): branch lists are not theirs to browse
        return set()
    rows = await s.execute(select(Branch.id).where(Branch.company_id == user.company_id, cond))
    return set(rows.scalars().all())


async def entry_scope(s: AsyncSession, user: User) -> ColumnElement[bool]:
    """SQL condition limiting SankalpEntry rows to what the user may see."""
    base = SankalpEntry.company_id == user.company_id
    scope = ROLES[user.role].scope
    if scope == "own":
        return and_(base, SankalpEntry.so_user_id == user.id)
    if scope == "allocated":
        mine = select(CallAllocation.entry_id).where(CallAllocation.caller_id == user.id)
        return and_(base, or_(SankalpEntry.first_caller_id == user.id, SankalpEntry.id.in_(mine)))
    branches = await visible_branch_ids(s, user)
    if branches is None:
        return base
    # the SO's branch, or the branch that works the lead (7.4 handling branch)
    return and_(base, or_(SankalpEntry.branch_id.in_(branches), SankalpEntry.work_branch_id.in_(branches)))         if branches else false()


async def user_scope(s: AsyncSession, user: User) -> ColumnElement[bool]:
    """People a manager may see in team lists: users placed in a branch they can see."""
    base = User.company_id == user.company_id
    branches = await visible_branch_ids(s, user)
    if branches is None:
        return base
    return and_(base, User.branch_id.in_(branches)) if branches else false()
