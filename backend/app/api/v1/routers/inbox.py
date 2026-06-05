"""
Router de mensajería interna — /api/v1/inbox

C-20: Bandeja de mensajería interna entre usuarios registrados del sistema.
D6 — Independiente de comunicaciones (sin cola, pull-based).
D7 — Identidad SIEMPRE del JWT; participación desde hilo_participantes.
D8 — require_permission("inbox:usar") en todos los endpoints (fail-closed → 403).

Endpoints:
    GET    /inbox                        — lista hilos del titular del JWT.
    POST   /inbox                        — inicia un nuevo hilo 1:1.
    GET    /inbox/{hilo_id}              — lee mensajes del hilo (marca leído).
    POST   /inbox/{hilo_id}/responder    — agrega mensaje al hilo.

Mapeo de excepciones:
    HiloNoEncontrado       → 404
    DestinatarioInvalido   → 404/422
    HiloDuplicado          → 409

Flujo: Router → InboxService → MensajeriaRepository → models.
Sin lógica de negocio en el router (regla dura #11).
snake_case; ≤500 LOC.
"""
import uuid
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import CurrentUser, get_current_user, get_db, require_permission
from app.repositories.mensajeria_repository import MensajeriaRepository
from app.schemas.mensajeria import (
    HiloCreate,
    InboxHiloRead,
    MensajeRead,
    RespuestaCreate,
)
from app.services.inbox_service import (
    DestinatarioInvalido,
    HiloDuplicado,
    HiloNoEncontrado,
    InboxService,
)

router = APIRouter(prefix="/inbox", tags=["inbox"])


# ---------------------------------------------------------------------------
# Dependency helper
# ---------------------------------------------------------------------------

def _make_service(db: AsyncSession, tenant_id: uuid.UUID) -> InboxService:
    repo = MensajeriaRepository(session=db, tenant_id=tenant_id)
    return InboxService(repo=repo)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("", response_model=List[InboxHiloRead])
async def ver_inbox(
    _grant=Depends(require_permission("inbox:usar")),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> List[InboxHiloRead]:
    """
    Lista hilos del titular del JWT, con conteo de no leídos.
    Requiere permiso 'inbox:usar'.
    """
    svc = _make_service(db, current_user.tenant_id)
    return await svc.ver_inbox(current_user)


@router.post("", response_model=MensajeRead, status_code=status.HTTP_201_CREATED)
async def iniciar_hilo(
    body: HiloCreate,
    _grant=Depends(require_permission("inbox:usar")),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MensajeRead:
    """
    Inicia un nuevo hilo 1:1. Requiere permiso 'inbox:usar'.
    """
    svc = _make_service(db, current_user.tenant_id)
    try:
        mensaje = await svc.iniciar_hilo(current_user, body)
    except DestinatarioInvalido as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except HiloDuplicado as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    return mensaje


@router.get("/{hilo_id}", response_model=List[MensajeRead])
async def abrir_hilo(
    hilo_id: uuid.UUID,
    _grant=Depends(require_permission("inbox:usar")),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> List[MensajeRead]:
    """
    Devuelve mensajes del hilo. Marca leído para el titular del JWT.
    Solo participantes del hilo pueden acceder → 404 para no participantes.
    """
    svc = _make_service(db, current_user.tenant_id)
    try:
        return await svc.abrir_hilo(current_user, hilo_id)
    except HiloNoEncontrado as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.post("/{hilo_id}/responder", response_model=MensajeRead, status_code=status.HTTP_201_CREATED)
async def responder(
    hilo_id: uuid.UUID,
    body: RespuestaCreate,
    _grant=Depends(require_permission("inbox:usar")),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MensajeRead:
    """
    Agrega un mensaje al hilo. Solo participantes pueden responder → 404.
    """
    svc = _make_service(db, current_user.tenant_id)
    try:
        return await svc.responder(current_user, hilo_id, body)
    except HiloNoEncontrado as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
