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

    impersonated_user_id — set when the token carries an impersonation session;
                           None in normal (non-impersonated) sessions.
    """
    user_id: uuid.UUID
    tenant_id: uuid.UUID
    roles: List[str]
    impersonated_user_id: Optional[uuid.UUID] = None


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

    # Parse optional impersonation claim (present only in impersonation sessions)
    impersonated_user_id: Optional[uuid.UUID] = None
    raw_imp = claims.get("impersonated_user_id")
    if raw_imp:
        try:
            impersonated_user_id = uuid.UUID(raw_imp)
        except ValueError:
            raise credentials_exception

    return CurrentUser(
        user_id=user_id,
        tenant_id=tenant_id,
        roles=roles,
        impersonated_user_id=impersonated_user_id,
    )


# ---------------------------------------------------------------------------
# resolve_domain_user_id — traduce auth_identities.id → usuario.id
# ---------------------------------------------------------------------------

async def resolve_domain_user_id(
    current_user: "CurrentUser",
    db: AsyncSession,
) -> uuid.UUID:
    """
    Resuelve el usuario.id de dominio a partir del auth_identity_id del JWT.

    current_user.user_id = auth_identities.id (sub del JWT).
    Las FKs de dominio (cargado_por, etc.) referencian usuario.id.
    Esta función hace el puente entre ambas tablas.

    Lanza 500 si el usuario de dominio no existe (inconsistencia de datos).
    """
    from sqlalchemy import select
    from app.models.usuario import Usuario

    stmt = select(Usuario.id).where(
        Usuario.tenant_id == current_user.tenant_id,
        Usuario.auth_identity_id == current_user.user_id,
        Usuario.deleted_at.is_(None),
    )
    result = await db.execute(stmt)
    uid = result.scalar_one_or_none()
    if uid is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Usuario de dominio no encontrado para la identidad autenticada",
        )
    return uid


# ---------------------------------------------------------------------------
# C-04: require_permission — guard factory
# ---------------------------------------------------------------------------

def require_permission(codigo: str):
    """
    FastAPI dependency factory: guard that verifies the authenticated user
    holds the specified permission.

    Usage::

        @router.get("/endpoint")
        async def endpoint(
            grant: PermissionGrant = Depends(require_permission("modulo:accion"))
        ):
            ...

    Design (design.md D5):
        - Depends on get_current_user (identity from JWT — never from request params).
        - Constructs RbacRepository and AuthorizationService per request.
        - Resolves the effective permission set for the current user.
        - Fail-closed: if the requested permission is not in the effective set → 403.
        - Returns PermissionGrant (codigo, scope) so the endpoint can apply
          row-level filtering when scope == 'propio'.
    """
    from fastapi import Depends, HTTPException, status
    from sqlalchemy.ext.asyncio import AsyncSession
    from app.repositories.rbac_repository import RbacRepository
    from app.services.authorization_service import AuthorizationService, PermissionGrant

    async def _guard(
        current_user: CurrentUser = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
    ) -> PermissionGrant:
        repo = RbacRepository(session=db, tenant_id=current_user.tenant_id)
        svc = AuthorizationService(repository=repo)
        grants = await svc.resolve_effective_permissions(current_user)

        matching = [g for g in grants if g.codigo == codigo]
        if not matching:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission '{codigo}' required",
            )
        return matching[0]

    return _guard
