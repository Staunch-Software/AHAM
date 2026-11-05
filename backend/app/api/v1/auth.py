import asyncio
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import current_user_any, token_claims
from app.core.config import get_settings
from app.core.db import get_session
from app.models import Branch, Cluster, Company, RefreshToken, Region, User, UserBranchAssignment
from app.schemas.org import ChangePasswordIn, LoginIn, MeOut, RefreshIn, TokenOut
from app.security.passwords import (
    create_access_token,
    hash_password,
    hash_refresh_token,
    new_refresh_token,
    verify_password,
)
from app.security.ratelimit import login_limiter
from app.security.rbac import PERMISSIONS, PORTALS, ROLES, portal_of
from app.services.periods import today_local, tz_of

router = APIRouter(prefix="/auth", tags=["auth"])

# Verified against when the account doesn't exist, to keep timing uniform.
_DUMMY_HASH = hash_password("not-a-real-password")


async def _issue(session: AsyncSession, user: User, portal: str) -> TokenOut:
    raw, hashed = new_refresh_token()
    session.add(
        RefreshToken(
            user_id=user.id,
            token_hash=hashed,
            portal=portal,
            expires_at=datetime.now(timezone.utc) + timedelta(days=get_settings().refresh_token_days),
        )
    )
    await session.commit()
    return TokenOut(
        access_token=create_access_token(str(user.id), str(user.company_id), user.role, portal),
        refresh_token=raw,
        role=user.role,
        portal=portal,
        must_change_password=user.must_change_password,
    )


async def _find_user(session: AsyncSession, identifier: str) -> User | None:
    """Emp ID (case-insensitive) or email. An ambiguous Emp ID (same code in two companies) finds nobody."""
    ident = identifier.strip()
    if "@" in ident:
        q = select(User).where(User.email == ident.lower())
    else:
        q = select(User).where(func.upper(User.employee_code) == ident.upper())
    rows = (await session.execute(q.limit(2))).scalars().all()
    return rows[0] if len(rows) == 1 else None


async def _left_company(session: AsyncSession, user: User) -> bool:
    """True once the roster exit date has passed (in the company's time zone)."""
    if not user.exit_date:
        return False
    company = await session.get(Company, user.company_id)
    return user.exit_date < today_local(tz_of(company.timezone if company else None))


@router.post("/login", response_model=TokenOut)
async def login(body: LoginIn, request: Request, session: AsyncSession = Depends(get_session)):
    key = f"{request.client.host if request.client else '?'}|{body.identifier.strip().lower()}"
    if wait := login_limiter.blocked(key):
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "Too many failed attempts. Try again later.",
                            headers={"Retry-After": str(wait)})
    user = await _find_user(session, body.identifier)
    # argon2 is CPU-heavy: run it in a worker thread so it doesn't stall the event loop (SSE, other requests)
    ok = await asyncio.to_thread(verify_password, body.password, user.password_hash if user else _DUMMY_HASH)
    if not user or not ok or user.status != "active" or await _left_company(session, user):
        login_limiter.fail(key)
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid Emp ID / email or password")
    login_limiter.clear(key)
    home = portal_of(user.role)
    if home != body.portal:
        # The password was right, so it is safe to say where this account signs in.
        raise HTTPException(status.HTTP_403_FORBIDDEN, {
            "code": "wrong_portal", "portal": home,
            "message": f"This account signs in at the {PORTALS.get(home, 'right')}, not here.",
        })
    return await _issue(session, user, home)


@router.post("/refresh", response_model=TokenOut)
async def refresh(body: RefreshIn, session: AsyncSession = Depends(get_session)):
    row = (
        await session.execute(
            select(RefreshToken)
            .where(RefreshToken.token_hash == hash_refresh_token(body.refresh_token))
            .with_for_update()
        )
    ).scalar_one_or_none()
    now = datetime.now(timezone.utc)
    if not row or row.revoked_at or row.expires_at < now:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid refresh token")
    user = await session.get(User, row.user_id)
    # A session opened at one portal dies if the user's role moves to another portal (or they leave).
    if not user or user.status != "active" or row.portal != portal_of(user.role) or await _left_company(session, user):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid refresh token")
    row.revoked_at = now  # rotation: each refresh token is single-use
    return await _issue(session, user, row.portal)


@router.post("/logout", status_code=204)
async def logout(body: RefreshIn, session: AsyncSession = Depends(get_session)):
    row = (
        await session.execute(
            select(RefreshToken).where(RefreshToken.token_hash == hash_refresh_token(body.refresh_token))
        )
    ).scalar_one_or_none()
    if row and not row.revoked_at:
        row.revoked_at = datetime.now(timezone.utc)
        await session.commit()


@router.post("/change-password", response_model=TokenOut)
async def change_password(
    body: ChangePasswordIn,
    claims: dict = Depends(token_claims),
    user: User = Depends(current_user_any),
    session: AsyncSession = Depends(get_session),
):
    """Also how a user replaces a temporary password: every other session is signed out."""
    if not await asyncio.to_thread(verify_password, body.current_password, user.password_hash):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, {"code": "wrong_password", "message": "Current password is wrong"})
    if body.new_password == body.current_password:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, {"code": "same_password",
                                                                   "message": "Choose a password you have not just used"})
    user.password_hash = await asyncio.to_thread(hash_password, body.new_password)
    user.must_change_password = False
    await session.execute(update(RefreshToken).where(RefreshToken.user_id == user.id, RefreshToken.revoked_at.is_(None))
                          .values(revoked_at=datetime.now(timezone.utc)))
    return await _issue(session, user, claims["portal"])


@router.get("/me", response_model=MeOut)
async def me(user: User = Depends(current_user_any), session: AsyncSession = Depends(get_session)):
    ids = (
        await session.execute(select(UserBranchAssignment.branch_id).where(UserBranchAssignment.user_id == user.id))
    ).scalars().all()
    out = MeOut.model_validate(user)
    role = ROLES.get(user.role)
    out.role_label = role.label if role else user.role
    out.portal = role.portal if role else ""
    out.permissions = sorted(PERMISSIONS.get(user.role, ()))
    out.branch_ids = list(ids)
    names = {
        "branch_name": (Branch, user.branch_id), "cluster_name": (Cluster, user.cluster_id),
        "region_name": (Region, user.region_id), "company_name": (Company, user.company_id),
    }
    for attr, (model, key) in names.items():
        if key and (obj := await session.get(model, key)):
            setattr(out, attr, obj.name)
    # An SO's region and cluster follow its branch.
    if user.branch_id and not (out.region_name and out.cluster_name):
        b = await session.get(Branch, user.branch_id)
        if b and b.region_id and not out.region_name:
            out.region_name = (await session.get(Region, b.region_id)).name
        if b and b.cluster_id and not out.cluster_name:
            out.cluster_name = (await session.get(Cluster, b.cluster_id)).name
    return out
