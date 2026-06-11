"""
Impersonacion router — endpoints de inicio y fin de sesión de impersonación.

Dominio: CRÍTICO (auth + auditoría). No lógica de negocio aquí — todo
delegado a ImpersonacionService.

Endpoints:
    POST /api/v1/usuarios/{usuario_id}/impersonar   — iniciar impersonación
    POST /api/v1/auth/impersonacion/finalizar        — finalizar impersonación

Reglas duras:
  - Identidad SIEMPRE desde el JWT verificado (CurrentUser). Nunca de params.
  - require_permission("impersonacion:usar") fail-closed en iniciar.
  - finalizar no requiere permiso extra — cualquier token con impersonación activa puede finalizarla.
  - Multi-tenancy: el service verifica que target pertenece al tenant del actor.
  - snake_case en todo.
"""
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import (
    CurrentUser,
    get_current_user,
    get_db,
    require_permission,
)
from app.core.request_context import extract_request_context
from app.repositories.audit_repository import AuditRepository
from app.repositories.auth_identity_repository import AuthIdentityRepository
from app.repositories.usuario_repository import UsuarioRepository
from app.schemas.auth import AccessTokenResponse, ImpersonarResponse
from app.services.authorization_service import PermissionGrant
from app.services.impersonacion_service import (
    AutoImpersonacionProhibida,
    ImpersonacionNoActiva,
    ImpersonacionService,
    UsuarioNoEncontrado,
)

# Two separate routers so they can be mounted at different prefixes in main.py
usuarios_router = APIRouter(prefix="/usuarios", tags=["impersonacion"])
auth_router = APIRouter(prefix="/auth", tags=["impersonacion"])


# ---------------------------------------------------------------------------
# Dependency helpers
# ---------------------------------------------------------------------------

def _make_impersonacion_service(
    db: AsyncSession,
    tenant_id: uuid.UUID,
) -> ImpersonacionService:
    """Build an ImpersonacionService scoped to the actor's tenant."""
    return ImpersonacionService(
        usuario_repo=UsuarioRepository(session=db, tenant_id=tenant_id),
        auth_identity_repo=AuthIdentityRepository(session=db),
        audit_repo=AuditRepository(session=db, tenant_id=tenant_id),
    )


# ---------------------------------------------------------------------------
# POST /api/v1/usuarios/{usuario_id}/impersonar
# ---------------------------------------------------------------------------

@usuarios_router.post(
    "/{usuario_id}/impersonar",
    response_model=ImpersonarResponse,
    status_code=status.HTTP_200_OK,
)
async def impersonar_usuario(
    usuario_id: uuid.UUID,
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
    _grant: PermissionGrant = Depends(require_permission("impersonacion:usar")),
    db: AsyncSession = Depends(get_db),
) -> ImpersonarResponse:
    """
    Iniciar una sesión de impersonación.

    Requiere permiso 'impersonacion:usar' (solo ADMIN global).
    El token emitido preserva el sub del actor real e incluye claims de impersonación.

    Errores:
      404 — usuario target no existe en el tenant del actor.
      400 — el actor intenta impersonarse a sí mismo.
      403 — sin permiso (manejado por require_permission, fail-closed).
    """
    ctx = extract_request_context(request)
    svc = _make_impersonacion_service(db, current_user.tenant_id)
    try:
        result = await svc.iniciar(
            actor=current_user,
            target_usuario_id=usuario_id,
            ip=ctx.ip,
            user_agent=ctx.user_agent,
        )
    except UsuarioNoEncontrado as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )
    except AutoImpersonacionProhibida as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )
    return ImpersonarResponse(
        access_token=result["access_token"],
        impersonated_name=result["impersonated_name"],
    )


# ---------------------------------------------------------------------------
# POST /api/v1/auth/impersonacion/finalizar
# ---------------------------------------------------------------------------

@auth_router.post(
    "/impersonacion/finalizar",
    response_model=AccessTokenResponse,
    status_code=status.HTTP_200_OK,
)
async def finalizar_impersonacion(
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AccessTokenResponse:
    """
    Finalizar la sesión de impersonación activa.

    El JWT actual debe contener el claim 'impersonated_user_id'. Si no existe,
    se devuelve 400. Emite un token limpio con los roles reales del actor.

    No requiere permiso extra — cualquier usuario con una sesión de impersonación
    activa puede finalizarla.
    """
    ctx = extract_request_context(request)
    svc = _make_impersonacion_service(db, current_user.tenant_id)
    try:
        result = await svc.finalizar(
            actor=current_user,
            ip=ctx.ip,
            user_agent=ctx.user_agent,
        )
    except ImpersonacionNoActiva as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )
    return AccessTokenResponse(
        access_token=result["access_token"],
        token_type=result.get("token_type", "bearer"),
    )
