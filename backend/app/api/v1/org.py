import asyncio
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import delete, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import current_user, require_admin
from app.core.db import get_session
from app.models import (
    AuditLog,
    Branch,
    Company,
    Organization,
    User,
    UserBranchAssignment,
)
from app.schemas.org import (
    BranchIn,
    BranchOut,
    BranchPatch,
    CompanyOut,
    CompanyPatch,
    EmployeeIn,
    EmployeePatch,
    OrganizationIn,
    OrganizationOut,
    OrganizationPatch,
    UserOut,
)
from app.security.passwords import hash_password

router = APIRouter(tags=["organization"])


def _audit(session: AsyncSession, actor: User, action: str, entity: str, entity_id) -> None:
    session.add(
        AuditLog(
            company_id=actor.company_id,
            actor_id=actor.id,
            action=action,
            entity_type=entity,
            entity_id=str(entity_id),
        )
    )


async def _commit(session: AsyncSession, *, flush_only: bool = False) -> None:
    try:
        await (session.flush() if flush_only else session.commit())
    except IntegrityError:
        await session.rollback()
        raise HTTPException(409, "A record with this code/email already exists")


async def _scoped(session: AsyncSession, model, id_: uuid.UUID, company_id: uuid.UUID):
    obj = await session.get(model, id_)
    # 404 (not 403) for other tenants' records: don't reveal existence.
    if obj is None or obj.company_id != company_id:
        raise HTTPException(404, "Not found")
    return obj


async def _check_refs(
    session: AsyncSession,
    company_id: uuid.UUID,
    organization_id: uuid.UUID | None = None,
    branch_ids: list[uuid.UUID] | None = None,
) -> None:
    if organization_id:
        await _scoped(session, Organization, organization_id, company_id)
    for bid in branch_ids or []:
        await _scoped(session, Branch, bid, company_id)


# ---- Company (own company only; company creation is a platform/seed operation) ----
@router.get("/companies", response_model=list[CompanyOut])
async def list_companies(user: User = Depends(current_user), s: AsyncSession = Depends(get_session)):
    return [await s.get(Company, user.company_id)]


@router.patch("/companies/{company_id}", response_model=CompanyOut)
async def patch_company(
    company_id: uuid.UUID,
    body: CompanyPatch,
    admin: User = Depends(require_admin),
    s: AsyncSession = Depends(get_session),
):
    if company_id != admin.company_id:
        raise HTTPException(404, "Not found")
    c = await s.get(Company, company_id)
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(c, k, v)
    _audit(s, admin, "company.update", "company", c.id)
    await _commit(s)
    return c


# ---- Organizations ----
@router.get("/organizations", response_model=list[OrganizationOut])
async def list_orgs(admin: User = Depends(require_admin), s: AsyncSession = Depends(get_session)):
    rows = await s.execute(
        select(Organization).where(Organization.company_id == admin.company_id).order_by(Organization.name)
    )
    return rows.scalars().all()


@router.post("/organizations", response_model=OrganizationOut, status_code=201)
async def create_org(
    body: OrganizationIn, admin: User = Depends(require_admin), s: AsyncSession = Depends(get_session)
):
    o = Organization(company_id=admin.company_id, **body.model_dump())
    s.add(o)
    await _commit(s, flush_only=True)
    _audit(s, admin, "organization.create", "organization", o.id)
    await _commit(s)
    return o


@router.patch("/organizations/{org_id}", response_model=OrganizationOut)
async def patch_org(
    org_id: uuid.UUID,
    body: OrganizationPatch,
    admin: User = Depends(require_admin),
    s: AsyncSession = Depends(get_session),
):
    o = await _scoped(s, Organization, org_id, admin.company_id)
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(o, k, v)
    _audit(s, admin, "organization.update", "organization", o.id)
    await _commit(s)
    return o


# ---- Branches ----
@router.get("/branches", response_model=list[BranchOut])
async def list_branches(
    status: str | None = None,
    user: User = Depends(current_user),
    s: AsyncSession = Depends(get_session),
):
    q = select(Branch).where(Branch.company_id == user.company_id).order_by(Branch.name)
    if status:
        q = q.where(Branch.status == status)
    if user.role != "admin":  # agents see only their assigned branches
        assigned = select(UserBranchAssignment.branch_id).where(UserBranchAssignment.user_id == user.id)
        q = q.where(or_(Branch.id.in_(assigned), Branch.id == user.branch_id))
    return (await s.execute(q)).scalars().all()


@router.post("/branches", response_model=BranchOut, status_code=201)
async def create_branch(
    body: BranchIn, admin: User = Depends(require_admin), s: AsyncSession = Depends(get_session)
):
    await _check_refs(s, admin.company_id, organization_id=body.organization_id)
    b = Branch(company_id=admin.company_id, **body.model_dump())
    s.add(b)
    await _commit(s, flush_only=True)
    _audit(s, admin, "branch.create", "branch", b.id)
    await _commit(s)
    return b


@router.patch("/branches/{branch_id}", response_model=BranchOut)
async def patch_branch(
    branch_id: uuid.UUID,
    body: BranchPatch,
    admin: User = Depends(require_admin),
    s: AsyncSession = Depends(get_session),
):
    b = await _scoped(s, Branch, branch_id, admin.company_id)
    data = body.model_dump(exclude_unset=True)
    await _check_refs(s, admin.company_id, organization_id=data.get("organization_id"))
    for k, v in data.items():
        setattr(b, k, v)
    _audit(s, admin, "branch.update", "branch", b.id)
    await _commit(s)
    return b


# ---- Employees ----
@router.get("/employees")
async def list_employees(
    q: str | None = None,
    branch_id: uuid.UUID | None = None,
    role: str | None = None,
    status: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    admin: User = Depends(require_admin),
    s: AsyncSession = Depends(get_session),
):
    base = select(User).where(User.company_id == admin.company_id)
    if q:
        like = f"%{q}%"
        base = base.where(
            or_(User.full_name.ilike(like), User.email.ilike(like), User.employee_code.ilike(like))
        )
    if branch_id:
        base = base.where(User.branch_id == branch_id)
    if role:
        base = base.where(User.role == role)
    if status:
        base = base.where(User.status == status)
    total = (await s.execute(select(func.count()).select_from(base.subquery()))).scalar_one()
    rows = (
        await s.execute(base.order_by(User.full_name).offset((page - 1) * page_size).limit(page_size))
    ).scalars().all()
    return {
        "items": [UserOut.model_validate(r) for r in rows],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


async def _set_assignments(s: AsyncSession, user_id: uuid.UUID, branch_ids: list[uuid.UUID]) -> None:
    await s.execute(delete(UserBranchAssignment).where(UserBranchAssignment.user_id == user_id))
    for bid in set(branch_ids):
        s.add(UserBranchAssignment(user_id=user_id, branch_id=bid))


@router.post("/employees", response_model=UserOut, status_code=201)
async def create_employee(
    body: EmployeeIn, admin: User = Depends(require_admin), s: AsyncSession = Depends(get_session)
):
    ids = list(body.branch_ids) + ([body.branch_id] if body.branch_id else [])
    await _check_refs(s, admin.company_id, body.organization_id, ids)
    u = User(
        company_id=admin.company_id,
        organization_id=body.organization_id,
        branch_id=body.branch_id,
        employee_code=body.employee_code,
        full_name=body.full_name,
        email=body.email.lower(),
        phone=body.phone,
        role=body.role,
        password_hash=await asyncio.to_thread(hash_password, body.password),
    )
    s.add(u)
    await _commit(s, flush_only=True)
    await _set_assignments(s, u.id, ids)
    _audit(s, admin, "employee.create", "user", u.id)
    await _commit(s)
    return u


@router.patch("/employees/{employee_id}", response_model=UserOut)
async def patch_employee(
    employee_id: uuid.UUID,
    body: EmployeePatch,
    admin: User = Depends(require_admin),
    s: AsyncSession = Depends(get_session),
):
    u = await _scoped(s, User, employee_id, admin.company_id)
    data = body.model_dump(exclude_unset=True)
    if u.id == admin.id and (data.get("status") == "inactive" or data.get("role") == "agent"):
        raise HTTPException(400, "You cannot deactivate or demote your own account")
    branch_ids = data.pop("branch_ids", None)
    password = data.pop("password", None)
    await _check_refs(s, admin.company_id, None, (branch_ids or []) + ([data["branch_id"]] if data.get("branch_id") else []))
    for k, v in data.items():
        setattr(u, k, v)
    if password:
        u.password_hash = await asyncio.to_thread(hash_password, password)
    if branch_ids is not None:
        await _set_assignments(s, u.id, branch_ids)
    _audit(s, admin, "employee.update", "user", u.id)
    await _commit(s)
    return u
