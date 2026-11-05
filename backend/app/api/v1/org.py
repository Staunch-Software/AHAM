import asyncio
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import delete, func, or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import current_user, require_any_perm, require_perm
from app.core.db import get_session
from app.models import Branch, Cluster, Company, RefreshToken, Region, User, UserBranchAssignment
from app.schemas.org import (
    BranchIn,
    BranchOut,
    BranchPatch,
    ClusterIn,
    ClusterOut,
    ClusterPatch,
    CompanyOut,
    CompanyPatch,
    EmployeeIn,
    EmployeePatch,
    RegionIn,
    RegionOut,
    RegionPatch,
    UserOut,
)
from app.security.passwords import hash_password, temporary_password
from app.security.rbac import PERMISSIONS, PORTALS, ROLES, has_perm
from app.services.reference import audit
from app.services.scope import user_scope, visible_branch_ids

router = APIRouter(tags=["organization"])
require_org = require_perm("org.manage")
require_users = require_perm("users.manage")


async def _commit(session: AsyncSession, *, flush_only: bool = False) -> None:
    try:
        await (session.flush() if flush_only else session.commit())
    except IntegrityError:
        await session.rollback()
        raise HTTPException(409, "A record with this name, code, Emp ID or email already exists")


async def _scoped(session: AsyncSession, model, id_: uuid.UUID | None, company_id: uuid.UUID):
    obj = await session.get(model, id_) if id_ else None
    # 404 (not 403) for other tenants' records: don't reveal existence.
    if obj is None or obj.company_id != company_id:
        raise HTTPException(404, f"{model.__name__} not found")
    return obj


# ---- Roles (for portal UIs) ----
@router.get("/roles")
async def list_roles(user: User = Depends(current_user)):
    return {
        "portals": PORTALS,
        "roles": [{"key": k, "label": r.label, "portal": r.portal, "level": r.level, "scope": r.scope,
                   "placement": r.placement, "permissions": sorted(PERMISSIONS[k])} for k, r in ROLES.items()],
    }


# ---- Company (own company only; company creation is a platform/seed operation) ----
@router.get("/companies", response_model=list[CompanyOut])
async def list_companies(user: User = Depends(current_user), s: AsyncSession = Depends(get_session)):
    return [await s.get(Company, user.company_id)]


@router.patch("/companies/{company_id}", response_model=CompanyOut)
async def patch_company(company_id: uuid.UUID, body: CompanyPatch, admin: User = Depends(require_org),
                        s: AsyncSession = Depends(get_session)):
    if company_id != admin.company_id:
        raise HTTPException(404, "Not found")
    c = await s.get(Company, company_id)
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(c, k, v)
    audit(s, admin, "company.update", "company", c.id)
    await _commit(s)
    return c


# ---- Regions ----
@router.get("/regions", response_model=list[RegionOut])
async def list_regions(user: User = Depends(current_user), s: AsyncSession = Depends(get_session)):
    return (await s.execute(select(Region).where(Region.company_id == user.company_id).order_by(Region.name))).scalars().all()


@router.post("/regions", response_model=RegionOut, status_code=201)
async def create_region(body: RegionIn, admin: User = Depends(require_org), s: AsyncSession = Depends(get_session)):
    r = Region(company_id=admin.company_id, **body.model_dump())
    s.add(r)
    await _commit(s, flush_only=True)
    audit(s, admin, "region.create", "region", r.id)
    await _commit(s)
    return r


@router.patch("/regions/{region_id}", response_model=RegionOut)
async def patch_region(region_id: uuid.UUID, body: RegionPatch, admin: User = Depends(require_org),
                       s: AsyncSession = Depends(get_session)):
    r = await _scoped(s, Region, region_id, admin.company_id)
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(r, k, v)
    audit(s, admin, "region.update", "region", r.id)
    await _commit(s)
    return r


# ---- Clusters ----
@router.get("/clusters", response_model=list[ClusterOut])
async def list_clusters(user: User = Depends(current_user), s: AsyncSession = Depends(get_session)):
    return (await s.execute(select(Cluster).where(Cluster.company_id == user.company_id).order_by(Cluster.name))).scalars().all()


@router.post("/clusters", response_model=ClusterOut, status_code=201)
async def create_cluster(body: ClusterIn, admin: User = Depends(require_org), s: AsyncSession = Depends(get_session)):
    await _scoped(s, Region, body.region_id, admin.company_id)
    c = Cluster(company_id=admin.company_id, **body.model_dump())
    s.add(c)
    await _commit(s, flush_only=True)
    audit(s, admin, "cluster.create", "cluster", c.id)
    await _commit(s)
    return c


@router.patch("/clusters/{cluster_id}", response_model=ClusterOut)
async def patch_cluster(cluster_id: uuid.UUID, body: ClusterPatch, admin: User = Depends(require_org),
                        s: AsyncSession = Depends(get_session)):
    c = await _scoped(s, Cluster, cluster_id, admin.company_id)
    data = body.model_dump(exclude_unset=True)
    if data.get("region_id"):
        await _scoped(s, Region, data["region_id"], admin.company_id)
        # A cluster's branches move with it: they must stay in the cluster's region.
        await s.execute(update(Branch).where(Branch.cluster_id == c.id).values(region_id=data["region_id"]))
    for k, v in data.items():
        setattr(c, k, v)
    audit(s, admin, "cluster.update", "cluster", c.id)
    await _commit(s)
    return c


# ---- Branches ----
async def _branch_refs(s: AsyncSession, company_id: uuid.UUID, region_id, cluster_id) -> uuid.UUID | None:
    """Validates region/cluster and returns the region the branch ends up in (a cluster fixes its region)."""
    if cluster_id:
        cluster = await _scoped(s, Cluster, cluster_id, company_id)
        if region_id and region_id != cluster.region_id:
            raise HTTPException(422, "The cluster belongs to another region")
        return cluster.region_id
    if region_id:
        await _scoped(s, Region, region_id, company_id)
    return region_id


@router.get("/branches", response_model=list[BranchOut])
async def list_branches(status: str | None = None, user: User = Depends(current_user),
                        s: AsyncSession = Depends(get_session)):
    q = select(Branch).where(Branch.company_id == user.company_id).order_by(Branch.name)
    if status:
        q = q.where(Branch.status == status)
    # Callers see every branch name (entries on their list come from any branch); others see their scope.
    if not has_perm(user.role, "calls.work"):
        visible = await visible_branch_ids(s, user)
        if visible is not None:
            q = q.where(Branch.id.in_(visible))
    return (await s.execute(q)).scalars().all()


@router.post("/branches", response_model=BranchOut, status_code=201)
async def create_branch(body: BranchIn, admin: User = Depends(require_org), s: AsyncSession = Depends(get_session)):
    data = body.model_dump()
    data["region_id"] = await _branch_refs(s, admin.company_id, body.region_id, body.cluster_id)
    b = Branch(company_id=admin.company_id, **data)
    s.add(b)
    await _commit(s, flush_only=True)
    audit(s, admin, "branch.create", "branch", b.id)
    await _commit(s)
    return b


@router.patch("/branches/{branch_id}", response_model=BranchOut)
async def patch_branch(branch_id: uuid.UUID, body: BranchPatch, admin: User = Depends(require_org),
                       s: AsyncSession = Depends(get_session)):
    b = await _scoped(s, Branch, branch_id, admin.company_id)
    data = body.model_dump(exclude_unset=True)
    if "region_id" in data or "cluster_id" in data:
        cluster_id = data.get("cluster_id", b.cluster_id)
        region_id = data.get("region_id", None if "cluster_id" in data and data["cluster_id"] else b.region_id)
        data["region_id"] = await _branch_refs(s, admin.company_id, region_id, cluster_id)
    for k, v in data.items():
        setattr(b, k, v)
    audit(s, admin, "branch.update", "branch", b.id)
    await _commit(s)
    return b


@router.get("/org/managers")
async def org_managers(user: User = Depends(require_any_perm("org.manage", "users.manage")),
                       s: AsyncSession = Depends(get_session)):
    """Who heads what: the active BMs of each branch, RTMs of each cluster and RBHs of each region, so HR can see a
    branch with no BM (its leads go to the RBH) or a region with no RBH (then nobody answers those leads)."""
    people = (await s.execute(select(User).where(
        User.company_id == user.company_id, User.status == "active",
        User.role.in_(["branch_manager", "cluster_manager", "region_manager"])))).scalars().all()
    extra = (await s.execute(select(UserBranchAssignment).where(
        UserBranchAssignment.user_id.in_([p.id for p in people if p.role == "branch_manager"] or [uuid.uuid4()])))).scalars().all()
    out: dict[str, dict[str, list[str]]] = {"branches": {}, "clusters": {}, "regions": {}}
    names = {p.id: p.full_name for p in people}
    for p in people:
        key, place = {"branch_manager": ("branches", p.branch_id), "cluster_manager": ("clusters", p.cluster_id),
                      "region_manager": ("regions", p.region_id)}[p.role]
        if place:
            out[key].setdefault(str(place), []).append(p.full_name)
    for a in extra:
        lst = out["branches"].setdefault(str(a.branch_id), [])
        if names[a.user_id] not in lst:
            lst.append(names[a.user_id])
    return out


# ---- Employees (the roster) ----
async def _check_placement(s: AsyncSession, company_id: uuid.UUID, role: str, branch_id, cluster_id, region_id,
                           branch_ids: list[uuid.UUID]) -> None:
    for model, key in ((Branch, branch_id), (Cluster, cluster_id), (Region, region_id)):
        if key:
            await _scoped(s, model, key, company_id)
    for bid in branch_ids:
        await _scoped(s, Branch, bid, company_id)
    need = ROLES[role].placement
    if need and not {"branch": branch_id, "cluster": cluster_id, "region": region_id}[need]:
        raise HTTPException(422, f"A {ROLES[role].label} must be attached to a {need}")


@router.get("/employees")
async def list_employees(
    q: str | None = None,
    branch_id: uuid.UUID | None = None,
    role: str | None = None,
    status: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=200),
    user: User = Depends(require_any_perm("users.manage", "team.read", "calls.manage", "reference.import")),
    s: AsyncSession = Depends(get_session),
):
    company_wide = any(has_perm(user.role, p) for p in ("users.manage", "calls.manage", "reference.import"))
    base = select(User).where(User.company_id == user.company_id if company_wide else await user_scope(s, user))
    if q:
        like = f"%{q}%"
        base = base.where(or_(User.full_name.ilike(like), User.email.ilike(like), User.employee_code.ilike(like)))
    if branch_id:
        base = base.where(User.branch_id == branch_id)
    if role:
        base = base.where(User.role.in_(role.split(",")))
    if status:
        base = base.where(User.status == status)
    total = (await s.execute(select(func.count()).select_from(base.subquery()))).scalar_one()
    rows = (await s.execute(base.order_by(User.full_name).offset((page - 1) * page_size).limit(page_size))).scalars().all()
    return {"items": [UserOut.model_validate(r) for r in rows], "total": total, "page": page, "page_size": page_size}


async def _set_assignments(s: AsyncSession, user_id: uuid.UUID, branch_ids: list[uuid.UUID]) -> None:
    await s.execute(delete(UserBranchAssignment).where(UserBranchAssignment.user_id == user_id))
    for bid in set(branch_ids):
        s.add(UserBranchAssignment(user_id=user_id, branch_id=bid))


@router.post("/employees", status_code=201)
async def create_employee(body: EmployeeIn, admin: User = Depends(require_users), s: AsyncSession = Depends(get_session)):
    """Creates the account with a one-time temporary password (returned once); the user must replace it at sign-in."""
    await _check_placement(s, admin.company_id, body.role, body.branch_id, body.cluster_id, body.region_id, body.branch_ids)
    password = temporary_password()
    data = body.model_dump(exclude={"branch_ids", "email"})
    u = User(company_id=admin.company_id, email=body.email.lower() if body.email else None,
             password_hash=await asyncio.to_thread(hash_password, password), must_change_password=True,
             **{**data, "employee_code": body.employee_code.strip().upper()})
    s.add(u)
    await _commit(s, flush_only=True)
    await _set_assignments(s, u.id, body.branch_ids)
    audit(s, admin, "employee.create", "user", u.id)
    await _commit(s)
    return {**UserOut.model_validate(u).model_dump(mode="json"), "temporary_password": password}


@router.patch("/employees/{employee_id}", response_model=UserOut)
async def patch_employee(employee_id: uuid.UUID, body: EmployeePatch, admin: User = Depends(require_users),
                         s: AsyncSession = Depends(get_session)):
    u = await _scoped(s, User, employee_id, admin.company_id)
    data = body.model_dump(exclude_unset=True)
    if u.id == admin.id and (data.get("status") == "inactive" or data.get("role", "admin") != "admin"):
        raise HTTPException(400, "You cannot deactivate or demote your own account")
    branch_ids = data.pop("branch_ids", None)
    if "email" in data:
        data["email"] = data["email"].lower() if data["email"] else None
    merged = {k: data.get(k, getattr(u, k)) for k in ("role", "branch_id", "cluster_id", "region_id")}
    await _check_placement(s, admin.company_id, merged["role"], merged["branch_id"], merged["cluster_id"],
                           merged["region_id"], branch_ids or [])
    role_changed = "role" in data and data["role"] != u.role
    for k, v in data.items():
        setattr(u, k, v)
    if branch_ids is not None:
        await _set_assignments(s, u.id, branch_ids)
    if role_changed or data.get("status") == "inactive":
        # A new role may belong to another portal: end the old sessions.
        await s.execute(update(RefreshToken).where(RefreshToken.user_id == u.id, RefreshToken.revoked_at.is_(None))
                        .values(revoked_at=datetime.now(timezone.utc)))
    audit(s, admin, "employee.update", "user", u.id)
    await _commit(s)
    return u


@router.post("/employees/{employee_id}/temporary-password")
async def reset_password(employee_id: uuid.UUID, admin: User = Depends(require_users),
                         s: AsyncSession = Depends(get_session)):
    """Shown once. The user must set their own password at the next sign-in; open sessions are ended."""
    u = await _scoped(s, User, employee_id, admin.company_id)
    password = temporary_password()
    u.password_hash = await asyncio.to_thread(hash_password, password)
    u.must_change_password = True
    await s.execute(update(RefreshToken).where(RefreshToken.user_id == u.id, RefreshToken.revoked_at.is_(None))
                    .values(revoked_at=datetime.now(timezone.utc)))
    audit(s, admin, "employee.temporary_password", "user", u.id)
    await _commit(s)
    return {"employee_code": u.employee_code, "temporary_password": password}
