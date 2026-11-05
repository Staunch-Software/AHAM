import uuid

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.models import User
from app.security.passwords import decode_access_token
from app.security.rbac import has_perm, portal_of

bearer = HTTPBearer(auto_error=False)


async def token_claims(creds: HTTPAuthorizationCredentials | None = Depends(bearer)) -> dict:
    unauth = HTTPException(status.HTTP_401_UNAUTHORIZED, "Not authenticated")
    if creds is None:
        raise unauth
    try:
        claims = decode_access_token(creds.credentials)
        uuid.UUID(claims["sub"])
    except (jwt.PyJWTError, ValueError, KeyError):
        raise unauth
    return claims


async def current_user_any(
    claims: dict = Depends(token_claims), session: AsyncSession = Depends(get_session)
) -> User:
    """The signed-in user, even one who still has to replace a temporary password (for /me, change-password)."""
    unauth = HTTPException(status.HTTP_401_UNAUTHORIZED, "Not authenticated")
    user = await session.get(User, uuid.UUID(claims["sub"]))
    # Re-check on every request so deactivation or a role change takes effect immediately.
    if user is None or user.status != "active" or claims.get("portal") != portal_of(user.role):
        raise unauth
    return user


async def current_user(user: User = Depends(current_user_any)) -> User:
    if user.must_change_password:
        raise HTTPException(status.HTTP_403_FORBIDDEN, {"code": "password_change_required",
                                                        "message": "Set a new password before continuing"})
    return user


def require_perm(*perms: str):
    """The user must hold every listed permission (app.security.rbac.PERMISSIONS)."""

    async def dep(user: User = Depends(current_user)) -> User:
        if not all(has_perm(user.role, p) for p in perms):
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Insufficient permissions")
        return user

    return dep


def require_any_perm(*perms: str):
    async def dep(user: User = Depends(current_user)) -> User:
        if not any(has_perm(user.role, p) for p in perms):
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Insufficient permissions")
        return user

    return dep


require_admin = require_perm("users.manage")
