"""
FastAPI dependencies — session management and identity resolution.

C-03: get_current_user derives identity/tenant/roles EXCLUSIVELY from the
verified JWT. NEVER from request params, body, or non-auth headers.
"""
import uuid
from dataclasses import dataclass
from typing import AsyncGenerator, List, Optional

from fastapi import HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession


# ---------------------------------------------------------------------------
# CurrentUser — immutable value object from the verified JWT
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class CurrentUser:
    """
    Immutable value object representing the authenticated user.

    Derived ONLY from the verified JWT claims. Fields cannot be modified
    after creation (frozen dataclass).
    """
    user_id: uuid.UUID
    tenant_id: uuid.UUID
    roles: List[str]


# ---------------------------------------------------------------------------
# DB session dependency (C-01)
# ---------------------------------------------------------------------------

async def get_db(request: Request) -> AsyncGenerator[AsyncSession, None]:
    """Dependency que abre una sesión async por request y la cierra en finally."""
    session_factory = request.app.state.session_factory
    session: AsyncSession = session_factory()
    try:
        yield session
    finally:
        await session.close()


# ---------------------------------------------------------------------------
# C-03: Identity from JWT — get_current_user
# ---------------------------------------------------------------------------

async def get_current_user(request: Request) -> CurrentUser:
    """
    FastAPI dependency: extract and verify the access token from the request.

    Extracts `Authorization: Bearer <jwt>`, verifies signature, expiry, and
    `type="access"`, then returns a frozen CurrentUser value object.

    NEVER reads identity from URL params, body, or non-auth headers.

    Raises HTTPException 401 if the token is missing, invalid, expired, or
    has the wrong type.
    """
    from jose import JWTError
    from app.core.security import decode_access_token

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    auth_header: Optional[str] = request.headers.get("authorization")
    if not auth_header or not auth_header.lower().startswith("bearer "):
        raise credentials_exception

    token = auth_header[7:]  # Strip "Bearer "
    if not token:
        raise credentials_exception

    try:
        claims = decode_access_token(token)
    except JWTError:
        raise credentials_exception

    try:
        user_id = uuid.UUID(claims["sub"])
        tenant_id = uuid.UUID(claims["tenant_id"])
        roles: List[str] = claims.get("roles", [])
    except (KeyError, ValueError):
        raise credentials_exception

    return CurrentUser(user_id=user_id, tenant_id=tenant_id, roles=roles)


# ---------------------------------------------------------------------------
# C-04 placeholder: require_permission
# ---------------------------------------------------------------------------

# RESERVADO → C-04: dependency que verifica que el usuario tiene un permiso modulo:accion
# async def require_permission(...): ...
