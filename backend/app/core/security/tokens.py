"""
JWT token encoding/decoding and opaque refresh/recovery token utilities.

C-03: Access tokens are short-lived JWTs (HS256); refresh and recovery tokens
are opaque random values stored by their SHA-256 hash.
"""
import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List

from jose import JWTError, jwt
from jose.exceptions import ExpiredSignatureError


def _settings():
    from app.core.config import Settings
    return Settings()


# ---------------------------------------------------------------------------
# JWT tokens — access and MFA challenge
# ---------------------------------------------------------------------------

def encode_access_token(
    *,
    user_id: uuid.UUID,
    tenant_id: uuid.UUID,
    roles: List[str],
    expires_minutes: int | None = None,
) -> str:
    """
    Encode a short-lived access token JWT (HS256).

    Claims: sub, tenant_id, roles, iat, exp, type="access".
    """
    settings = _settings()
    if expires_minutes is None:
        expires_minutes = settings.ACCESS_TOKEN_EXPIRE_MINUTES

    now = datetime.now(tz=timezone.utc)
    exp = now + timedelta(minutes=expires_minutes)
    payload: Dict[str, Any] = {
        "sub": str(user_id),
        "tenant_id": str(tenant_id),
        "roles": roles,
        "iat": int(now.timestamp()),
        "exp": int(exp.timestamp()),
        "type": "access",
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")


def decode_access_token(token: str) -> Dict[str, Any]:
    """
    Decode and verify an access token.

    Raises JWTError (or subclass) if the token is invalid, expired, or has
    wrong type. Never returns a claim dict for non-access tokens.
    """
    settings = _settings()
    claims = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
    if claims.get("type") != "access":
        raise JWTError("Token type is not 'access'")
    return claims


def encode_mfa_token(
    *,
    user_id: uuid.UUID,
    tenant_id: uuid.UUID,
    expires_minutes: int | None = None,
) -> str:
    """
    Encode a short-lived MFA challenge token (type="mfa").

    Used as a gate between credential validation and final session issuance
    during the 2FA login flow.
    """
    settings = _settings()
    if expires_minutes is None:
        expires_minutes = settings.MFA_TOKEN_EXPIRE_MINUTES

    now = datetime.now(tz=timezone.utc)
    exp = now + timedelta(minutes=expires_minutes)
    payload: Dict[str, Any] = {
        "sub": str(user_id),
        "tenant_id": str(tenant_id),
        "iat": int(now.timestamp()),
        "exp": int(exp.timestamp()),
        "type": "mfa",
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")


def decode_mfa_token(token: str) -> Dict[str, Any]:
    """
    Decode and verify an MFA challenge token.

    Raises JWTError if invalid, expired, or wrong type.
    """
    settings = _settings()
    claims = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
    if claims.get("type") != "mfa":
        raise JWTError("Token type is not 'mfa'")
    return claims


# ---------------------------------------------------------------------------
# Opaque tokens — refresh and recovery
# ---------------------------------------------------------------------------

def generate_opaque_token() -> str:
    """
    Generate a cryptographically secure opaque token.

    Returns a URL-safe base64 string (43 chars for 32 bytes of randomness).
    The CLIENT stores this value; the SERVER stores only its hash.
    """
    return secrets.token_urlsafe(32)


def hash_opaque_token(token: str) -> str:
    """
    Compute the SHA-256 hash of an opaque token for secure storage.

    Returns a hex digest string. Deterministic: same token → same hash.
    """
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
