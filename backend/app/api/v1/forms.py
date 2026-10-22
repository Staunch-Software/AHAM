import hmac
import uuid

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_roles
from app.core.config import get_settings
from app.core.db import get_session
from app.models import (
    Branch,
    Company,
    FormAssignment,
    FormDefinition,
    FormVersion,
    User,
    UserBranchAssignment,
)
from app.services.form_schema import SchemaError, validate_schema
from app.services.workflow import ensure_company_defaults, overlay_for_company

agent_router = APIRouter(prefix="/agent/forms", tags=["agent-forms"])
internal_router = APIRouter(prefix="/internal/forms", tags=["internal"], include_in_schema=False)
require_agent = require_roles("agent")


async def agent_branch_ids(s: AsyncSession, user: User) -> list[uuid.UUID]:
    ids = set(
        (await s.execute(select(UserBranchAssignment.branch_id).where(UserBranchAssignment.user_id == user.id)))
        .scalars()
        .all()
    )
    if user.branch_id:
        ids.add(user.branch_id)
    return list(ids)


async def accessible_forms(s: AsyncSession, user: User) -> list[FormDefinition]:
    branches = await agent_branch_ids(s, user)
    assigned = select(FormAssignment.form_id).where(
        or_(FormAssignment.branch_id.is_(None), FormAssignment.branch_id.in_(branches))
    )
    q = select(FormDefinition).where(
        FormDefinition.company_id == user.company_id, FormDefinition.id.in_(assigned)
    )
    return list((await s.execute(q.order_by(FormDefinition.title))).scalars().all())


async def _latest(s: AsyncSession, form_id: uuid.UUID) -> FormVersion | None:
    return (
        await s.execute(
            select(FormVersion)
            .where(FormVersion.form_id == form_id, FormVersion.status == "published")
            .order_by(FormVersion.version.desc())
            .limit(1)
        )
    ).scalar_one_or_none()


@agent_router.get("")
async def list_forms(user: User = Depends(require_agent), s: AsyncSession = Depends(get_session)):
    out = []
    for f in await accessible_forms(s, user):
        v = await _latest(s, f.id)
        if v:
            out.append({"form_id": f.key, "title": f.title, "version": v.version})
    return out


@agent_router.get("/sync")
async def sync_forms(user: User = Depends(require_agent), s: AsyncSession = Depends(get_session)):
    await ensure_company_defaults(s, user.company_id)
    await s.commit()
    out = []
    for f in await accessible_forms(s, user):
        v = await _latest(s, f.id)
        if v:
            # current managed options (e.g. type of person) are injected here; the stored version is unchanged
            out.append({"form_id": f.key, "version": v.version,
                        "schema": await overlay_for_company(s, user.company_id, v.schema, delivery=True)})
    return out


@agent_router.get("/{form_key}/versions/{version}")
async def get_version(
    form_key: str, version: int, user: User = Depends(require_agent), s: AsyncSession = Depends(get_session)
):
    forms = {f.key: f for f in await accessible_forms(s, user)}
    f = forms.get(form_key)
    v = None
    if f:
        v = (
            await s.execute(
                select(FormVersion).where(
                    FormVersion.form_id == f.id,
                    FormVersion.version == version,
                    FormVersion.status != "retired",
                )
            )
        ).scalar_one_or_none()
    if not v:
        raise HTTPException(404, "Form version not found")
    return {"form_id": f.key, "version": v.version, "status": v.status,
            "schema": await overlay_for_company(s, user.company_id, v.schema, delivery=True)}


# ---- Internal configuration (not linked from any UI; key-protected; off unless INTERNAL_API_KEY is set) ----
async def require_internal(x_internal_key: str | None = Header(None)) -> None:
    configured = get_settings().internal_api_key
    if not configured:
        raise HTTPException(404, "Not found")
    if not x_internal_key or not hmac.compare_digest(x_internal_key, configured):
        raise HTTPException(403, "Forbidden")


class PublishIn(BaseModel):
    company_code: str
    schema_: dict = Field(alias="schema")
    branch_codes: list[str] | None = None  # None = all branches

    model_config = ConfigDict(populate_by_name=True)


async def publish_version(
    s: AsyncSession, company: Company, schema: dict, branch_ids: list[uuid.UUID | None]
) -> FormVersion:
    """Create (never mutate) a form version. Used by the seed script and the internal endpoint."""
    validate_schema(schema)
    form = (
        await s.execute(
            select(FormDefinition).where(
                FormDefinition.company_id == company.id, FormDefinition.key == schema["form_id"]
            )
        )
    ).scalar_one_or_none()
    if form is None:
        form = FormDefinition(company_id=company.id, key=schema["form_id"], title=schema["title"])
        s.add(form)
        await s.flush()
    latest = (
        await s.execute(select(func.max(FormVersion.version)).where(FormVersion.form_id == form.id))
    ).scalar_one()
    if schema["version"] <= (latest or 0):
        raise HTTPException(409, f"version must be greater than existing {latest}")
    v = FormVersion(form_id=form.id, version=schema["version"], schema=schema)
    s.add(v)
    existing = set(
        (await s.execute(select(FormAssignment.branch_id).where(FormAssignment.form_id == form.id)))
        .scalars()
        .all()
    )
    for b in branch_ids:
        if b not in existing:
            s.add(FormAssignment(form_id=form.id, branch_id=b))
    await s.flush()
    return v


@internal_router.post("", dependencies=[Depends(require_internal)], status_code=201)
async def internal_publish(body: PublishIn, s: AsyncSession = Depends(get_session)):
    company = (await s.execute(select(Company).where(Company.code == body.company_code))).scalar_one_or_none()
    if not company:
        raise HTTPException(404, "Unknown company")
    branch_ids: list[uuid.UUID | None] = [None]
    if body.branch_codes is not None:
        rows = (
            await s.execute(
                select(Branch.id).where(Branch.company_id == company.id, Branch.code.in_(body.branch_codes))
            )
        ).scalars().all()
        branch_ids = list(rows)
    try:
        v = await publish_version(s, company, body.schema_, branch_ids)
        await s.commit()
    except SchemaError as e:
        raise HTTPException(422, {"errors": e.errors})
    except IntegrityError:
        await s.rollback()
        raise HTTPException(409, "Version already exists")
    return {"form_id": body.schema_["form_id"], "version": v.version}
