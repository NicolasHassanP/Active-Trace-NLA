"""
Router avisos — /api/v1/avisos

C-15 Design:
    D7  — permiso 'avisos:publicar' requerido para gestión (COORDINADOR, ADMIN).
    D7  — feed y ack requieren solo autenticación (any role); audiencia enforced en repo.
    D8  — identidad del actor SIEMPRE desde el JWT, nunca del body.

Endpoints de gestión (avisos:publicar):
    POST   /avisos               — publicar aviso
    PUT    /avisos/{id}          — modificar aviso
    DELETE /avisos/{id}          — soft-delete aviso
    GET    /avisos/gestion       — management list (ALL tenant avisos, C-23 OQ-1 fix)

Endpoints de feed (any authenticated role):
    GET    /avisos               — full recipient feed (con ack_count)
    GET    /avisos/pendientes    — pending feed (requiere_ack=True + sin ack propio)

Endpoints de ack (any authenticated role):
    POST   /avisos/{id}/ack      — confirmar lectura (idempotente)

snake_case; ≤500 LOC.
"""
import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import CurrentUser, get_current_user, get_db, require_permission, resolve_domain_user_id
from app.repositories.audit_repository import AuditRepository
from app.repositories.aviso_repository import AcknowledgmentRepository, AvisoRepository
from app.schemas.aviso import (
    AckAvisoRequest,
    AcknowledgmentRead,
    ActualizarAvisoRequest,
    AvisoRead,
    CrearAvisoRequest,
)
from app.services.aviso_service import AvisoService

router = APIRouter(prefix="/avisos", tags=["avisos"])


# ---------------------------------------------------------------------------
# Service factory
# ---------------------------------------------------------------------------

def _make_aviso_service(db: AsyncSession, tenant_id: uuid.UUID) -> AvisoService:
    return AvisoService(
        aviso_repo=AvisoRepository(session=db, tenant_id=tenant_id),
        ack_repo=AcknowledgmentRepository(session=db, tenant_id=tenant_id),
        audit_repo=AuditRepository(session=db, tenant_id=tenant_id),
    )


# ---------------------------------------------------------------------------
# Gestión: POST /avisos — publicar aviso
# ---------------------------------------------------------------------------

@router.post(
    "",
    response_model=AvisoRead,
    status_code=status.HTTP_201_CREATED,
)
async def publicar_aviso(
    body: CrearAvisoRequest,
    _grant=Depends(require_permission("avisos:publicar")),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AvisoRead:
    """
    Publica un nuevo aviso con audiencia, ventana de validez y configuración de ack.

    Requiere permiso avisos:publicar (COORDINADOR, ADMIN).
    Identidad del actor desde el JWT.
    """
    svc = _make_aviso_service(db, current_user.tenant_id)
    aviso = await svc.publicar_aviso(body, current_user)
    # Build response with ack_count=0 (just published)
    from app.schemas.aviso import AvisoRead as _AvisoRead
    read = _AvisoRead.model_validate(aviso)
    return read.model_copy(update={"ack_count": 0})


# ---------------------------------------------------------------------------
# Gestión: PUT /avisos/{aviso_id} — modificar aviso
# ---------------------------------------------------------------------------

@router.put(
    "/{aviso_id}",
    response_model=AvisoRead,
)
async def modificar_aviso(
    aviso_id: uuid.UUID,
    body: ActualizarAvisoRequest,
    _grant=Depends(require_permission("avisos:publicar")),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AvisoRead:
    """
    Modifica un aviso existente (parcial o total).

    Requiere permiso avisos:publicar. Retorna 404 si no pertenece al tenant.
    """
    svc = _make_aviso_service(db, current_user.tenant_id)
    aviso = await svc.modificar_aviso(aviso_id, body, current_user)
    ack_count = await svc._ack_repo.count_acks(aviso.id)
    read = AvisoRead.model_validate(aviso)
    return read.model_copy(update={"ack_count": ack_count})


# ---------------------------------------------------------------------------
# Gestión: DELETE /avisos/{aviso_id} — soft-delete aviso
# ---------------------------------------------------------------------------

@router.delete(
    "/{aviso_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def eliminar_aviso(
    aviso_id: uuid.UUID,
    _grant=Depends(require_permission("avisos:publicar")),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """
    Soft-delete un aviso. Requiere permiso avisos:publicar. Retorna 404 si no encontrado.
    """
    svc = _make_aviso_service(db, current_user.tenant_id)
    await svc.eliminar_aviso(aviso_id, current_user)


# ---------------------------------------------------------------------------
# Feed: GET /avisos — full recipient feed
# ---------------------------------------------------------------------------

@router.get(
    "",
    response_model=List[AvisoRead],
)
async def listar_feed(
    cohorte_id: Optional[uuid.UUID] = Query(None),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> List[AvisoRead]:
    """
    Feed completo de avisos para el usuario autenticado.

    Cualquier rol autenticado. Audiencia enforced por audience query en repo.
    Retorna avisos ordenados por orden ASC, severidad DESC.
    """
    svc = _make_aviso_service(db, current_user.tenant_id)
    return await svc.listar_feed(
        usuario_id=current_user.user_id,
        roles=current_user.roles,
        cohorte_id=cohorte_id,
        actor=current_user,
    )


# ---------------------------------------------------------------------------
# Feed: GET /avisos/pendientes — pending feed
# ---------------------------------------------------------------------------

@router.get(
    "/pendientes",
    response_model=List[AvisoRead],
)
async def listar_pendientes(
    cohorte_id: Optional[uuid.UUID] = Query(None),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> List[AvisoRead]:
    """
    Feed pendiente: avisos con requiere_ack=True que el usuario aún no confirmó.

    Cualquier rol autenticado. Solo avisos en ventana activa y sin ack propio.
    """
    svc = _make_aviso_service(db, current_user.tenant_id)
    return await svc.listar_pendientes(
        usuario_id=current_user.user_id,
        roles=current_user.roles,
        cohorte_id=cohorte_id,
        actor=current_user,
    )


# ---------------------------------------------------------------------------
# Gestión: GET /avisos/gestion — management list (C-15 follow-up, C-23 OQ-1)
# ---------------------------------------------------------------------------

@router.get(
    "/gestion",
    response_model=List[AvisoRead],
)
async def listar_avisos_gestion(
    _grant=Depends(require_permission("avisos:publicar")),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> List[AvisoRead]:
    """
    Lista de gestión: TODOS los avisos no eliminados del tenant del actor.

    C-15 follow-up resolviendo el gap OQ-1 de C-23: el feed de audiencia filtra
    por destinatario, lo que impide a un COORDINADOR ver avisos dirigidos a otros
    segmentos. Este endpoint devuelve el set completo del tenant (sin filtro de
    audiencia) para el panel de gestión.

    Requiere permiso avisos:publicar (COORDINADOR, ADMIN). Fail-closed: sin
    permiso → 403. Identidad y tenant SIEMPRE del JWT, nunca del body/URL.
    Ordenado por created_at DESC (más reciente primero).
    """
    svc = _make_aviso_service(db, current_user.tenant_id)
    return await svc.listar_gestion(current_user)


# ---------------------------------------------------------------------------
# Ack: POST /avisos/{aviso_id}/ack — confirmar lectura
# ---------------------------------------------------------------------------

@router.post(
    "/{aviso_id}/ack",
    response_model=AcknowledgmentRead,
    status_code=status.HTTP_200_OK,
)
async def acknowledger_aviso(
    aviso_id: uuid.UUID,
    body: AckAvisoRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AcknowledgmentRead:
    """
    Confirmar la lectura de un aviso (idempotente).

    Cualquier rol autenticado. usuario_id SIEMPRE del JWT — nunca del body.
    Retorna 403 si el aviso no está en ventana o inactivo.
    Retorna 404 si el aviso no existe o no pertenece al tenant.
    """
    domain_user_id = await resolve_domain_user_id(current_user, db)
    svc = _make_aviso_service(db, current_user.tenant_id)
    ack = await svc.acknowledger_aviso(aviso_id, current_user, domain_user_id)
    return AcknowledgmentRead.model_validate(ack)
