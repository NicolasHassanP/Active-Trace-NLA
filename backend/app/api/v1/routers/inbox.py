"""
Router de mensajería interna — /api/v1/inbox

C-20: Bandeja de mensajería interna entre usuarios registrados del sistema.
D6 — Independiente de comunicaciones (sin cola, pull-based).
D7 — Identidad SIEMPRE del JWT; participación desde hilo_participantes.
D8 — require_permission("inbox:usar") en todos los endpoints (fail-closed → 403).

Endpoints:
    GET    /inbox                        — lista hilos del titular del JWT.
    POST   /inbox                        — inicia un nuevo hilo 1:1.
    GET    /inbox/usuarios               — búsqueda de usuarios para combobox destinatario.
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
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import CurrentUser, get_current_user, get_db, require_permission
from app.repositories.mensajeria_repository import MensajeriaRepository
from app.repositories.usuario_repository import UsuarioRepository
from app.schemas.mensajeria import (
    HiloCreate,
    InboxHiloRead,
    MensajeRead,
    RespuestaCreate,
)
from app.schemas.usuario import UsuarioAsignableRead
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


@router.get("/usuarios", response_model=List[UsuarioAsignableRead])
async def buscar_usuarios_inbox(
    q: Optional[str] = Query(default=None),
    _grant=Depends(require_permission("inbox:usar")),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> List[UsuarioAsignableRead]:
    """
    Búsqueda de usuarios para el combobox de destinatario en NuevoHiloForm.

    Requiere permiso inbox:usar (TODOS los roles que usan mensajería interna).
    Tenant SIEMPRE desde el JWT — nunca de query/body (regla dura #8).
    Devuelve solo campos no-PII: id, nombre, apellidos, email, legajo.
    Excluye soft-deleted. Máximo 20 resultados.
    Reutiliza UsuarioRepository.buscar_asignables (tenant-scoped por defecto).
    """
    usuario_repo = UsuarioRepository(session=db, tenant_id=current_user.tenant_id)
    usuarios = await usuario_repo.buscar_asignables(q=q, limit=20)

    result = []
    for u in usuarios:
        result.append(
            UsuarioAsignableRead(
                id=u.id,
                nombre=u.nombre,
                apellidos=u.apellidos,
                email=u.email_encrypted,  # EncryptedString decrypts on access
                legajo=u.legajo,
            )
        )
    return result


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
