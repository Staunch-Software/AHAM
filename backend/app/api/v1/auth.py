import asyncio
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import current_user
from app.core.config import get_settings
from app.core.db import get_session
from app.models import RefreshToken, User, UserBranchAssignment
from app.security.ratelimit import login_limiter
from app.schemas.org import LoginIn, MeOut, RefreshIn, TokenOut
from app.security.passwords import (
    create_access_token,
    hash_password,
    hash_refresh_token,
    new_refresh_token,
    verify_password,
)

router = APIRouter(prefix="/auth", tags=["auth"])

# Verified against when the account doesn't exist, to keep timing uniform.
_DUMMY_HASH = hash_password("not-a-real-password")


async def _issue(session: AsyncSession, user: User) -> TokenOut:
    raw, hashed = new_refresh_token()
    session.add(
        RefreshToken(
            user_id=user.id,
            token_hash=hashed,
            expires_at=datetime.now(timezone.utc)
            + timedelta(days=get_settings().refresh_token_days),
        )
    )
    await session.commit()
    return TokenOut(
        access_token=create_access_token(str(user.id), str(user.company_id), user.role),
        refresh_token=raw,
    )


@router.post("/login", response_model=TokenOut)
async def login(body: LoginIn, request: Request, session: AsyncSession = Depends(get_session)):
    key = f"{request.client.host if request.client else '?'}|{body.email.lower()}"
    if wait := login_limiter.blocked(key):
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "Too many failed attempts. Try again later.",
                            headers={"Retry-After": str(wait)})
    user = (
        await session.execute(select(User).where(User.email == body.email.lower()))
    ).scalar_one_or_none()
    # argon2 is CPU-heavy: run it in a worker thread so it doesn't stall the event loop (SSE, other requests)
    ok = await asyncio.to_thread(verify_password, body.password, user.password_hash if user else _DUMMY_HASH)
    if not user or not ok or user.status != "active":
        login_limiter.fail(key)
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid email or password")
    login_limiter.clear(key)
    return await _issue(session, user)


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
    if not user or user.status != "active":
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid refresh token")
    row.revoked_at = now  # rotation: each refresh token is single-use
    return await _issue(session, user)


@router.post("/logout", status_code=204)
async def logout(body: RefreshIn, session: AsyncSession = Depends(get_session)):
    row = (
        await session.execute(
            select(RefreshToken).where(
                RefreshToken.token_hash == hash_refresh_token(body.refresh_token)
            )
        )
    ).scalar_one_or_none()
    if row and not row.revoked_at:
        row.revoked_at = datetime.now(timezone.utc)
        await session.commit()


@router.get("/me", response_model=MeOut)
async def me(user: User = Depends(current_user), session: AsyncSession = Depends(get_session)):
    ids = (
        await session.execute(
            select(UserBranchAssignment.branch_id).where(UserBranchAssignment.user_id == user.id)
        )
    ).scalars().all()
    out = MeOut.model_validate(user)
    out.branch_ids = list(ids)
    return out
