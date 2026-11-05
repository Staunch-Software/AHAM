import hashlib
import secrets
from datetime import datetime, timedelta, timezone

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

from app.core.config import get_settings

_ph = PasswordHasher()


def hash_password(password: str) -> str:
    return _ph.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    try:
        return _ph.verify(hashed, password)
    except (VerificationError, InvalidHashError):  # wrong password, or an account with no usable password
        return False


def temporary_password() -> str:
    """Readable one-time password (no 0/O/1/l) handed to a new user, who must replace it at first sign-in."""
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZabcdefghjkmnpqrstuvwxyz23456789"
    return "".join(secrets.choice(alphabet) for _ in range(12))


UNUSABLE_PASSWORD = "!unusable"  # not an argon2 hash: verify_password() is always False for it


def unusable_password_hash() -> str:
    """For roster accounts that have no password yet: sign-in is impossible until a temporary password is issued."""
    return UNUSABLE_PASSWORD


def create_access_token(user_id: str, company_id: str, role: str, portal: str) -> str:
    s = get_settings()
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "cid": company_id,
        "role": role,
        "portal": portal,
        "iat": now,
        "exp": now + timedelta(minutes=s.access_token_minutes),
    }
    return jwt.encode(payload, s.jwt_secret, algorithm="HS256")


def decode_access_token(token: str) -> dict:
    claims = jwt.decode(token, get_settings().jwt_secret, algorithms=["HS256"])
    if claims.get("typ"):  # other signed tokens (e.g. SSE tickets) are not access tokens
        raise jwt.InvalidTokenError("not an access token")
    return claims


def new_refresh_token() -> tuple[str, str]:
    """Returns (raw_token, sha256_hash). Only the hash is stored."""
    raw = secrets.token_urlsafe(48)
    return raw, hashlib.sha256(raw.encode()).hexdigest()


def hash_refresh_token(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()
