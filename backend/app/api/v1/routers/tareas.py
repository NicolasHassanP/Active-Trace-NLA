"""
Router tareas — /api/v1/tareas

C-16 Design:
    D7 — tareas:gestionar requerido para: POST /tareas, POST /{id}/delegar,
         GET /tareas/admin, DELETE /{id}.
    D7 — Solo autenticación (con ownership enforcement en service) para:
         GET /tareas/mias, GET /{id}, PATCH /{id}/estado,
         POST|GET /{id}/comentarios.
    D6 — Identidad del actor SIEMPRE desde el JWT, nunca del body.

Endpoints gestionados (tareas:gestionar):
    POST   /tareas                         — crear/asignar tarea
    POST   /tareas/{id}/delegar            — delegar tarea a otro docente
    GET    /tareas/admin                   — listado global con filtros
    DELETE /tareas/{id}                    — soft-delete

Endpoints de self-service (auth + ownership):
    GET    /tareas/mias                    — mis tareas asignadas
    GET    /tareas/{id}                    — detalle (ownership enforced in service)
    PATCH  /tareas/{id}/estado             — cambiar estado (ownership enforced in service)
    POST   /tareas/{id}/comentarios        — agregar comentario (ownership enforced)
    GET    /tareas/{id}/comentarios        — listar hilo (ownership enforced)

snake_case; ≤500 LOC.
"""
import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import CurrentUser, get_current_user, get_db, require_permission
from app.models.tarea import TareaEstado

# ---------------------------------------------------------------------------
# Optional permission helper — resolves gestionar without raising 403
# ---------------------------------------------------------------------------

async def _check_gestionar_optional(
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> bool:
    """Returns True if current_user holds tareas:gestionar, False otherwise."""
    try:
        from app.repositories.rbac_repository import RbacRepository
        from app.services.authorization_service import AuthorizationService
        repo = RbacRepository(session=db, tenant_id=current_user.tenant_id)
        svc = AuthorizationService(repository=repo)
        grants = await svc.resolve_effective_permissions(current_user)
        return any(g.codigo == "tareas:gestionar" for g in grants)
    except Exception:
        return False
from app.repositories.audit_repository import AuditRepository
from app.repositories.tarea_repository import ComentarioTareaRepository, TareaRepository
from app.schemas.tarea import (
    ComentarioTareaCreate,
    ComentarioTareaRead,
    TareaCreate,
    TareaDelegar,
    TareaRead,
    TareaUpdateEstado,
)
from app.services.tarea_service import TareaService

router = APIRouter(prefix="/tareas", tags=["tareas"])


# ---------------------------------------------------------------------------
# Service factory
# ---------------------------------------------------------------------------

def _make_tarea_service(db: AsyncSession, tenant_id: uuid.UUID) -> TareaService:
    return TareaService(
        tarea_repo=TareaRepository(session=db, tenant_id=tenant_id),
        comentario_repo=ComentarioTareaRepository(session=db, tenant_id=tenant_id),
        audit_repo=AuditRepository(session=db, tenant_id=tenant_id),
    )


# ---------------------------------------------------------------------------
# Gestión: POST /tareas — crear/asignar tarea
# ---------------------------------------------------------------------------

@router.post(
    "",
    response_model=TareaRead,
    status_code=status.HTTP_201_CREATED,
)
async def crear_tarea(
    body: TareaCreate,
    _grant=Depends(require_permission("tareas:gestionar")),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TareaRead:
    """
    Crea y asigna una tarea a un docente.

    Requiere tareas:gestionar. tenant_id y asignado_por desde el JWT.
    """
    svc = _make_tarea_service(db, current_user.tenant_id)
    tarea = await svc.publicar(body, current_user)
    return TareaRead.model_validate(tarea)


# ---------------------------------------------------------------------------
# Gestión: POST /tareas/{tarea_id}/delegar — delegar tarea
# ---------------------------------------------------------------------------

@router.post(
    "/{tarea_id}/delegar",
    response_model=TareaRead,
)
async def delegar_tarea(
    tarea_id: uuid.UUID,
    body: TareaDelegar,
    _grant=Depends(require_permission("tareas:gestionar")),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TareaRead:
    """
    Delega una tarea a otro docente.

    Requiere tareas:gestionar. Emite TAREA_DELEGAR audit + comentario de sistema.
    """
    svc = _make_tarea_service(db, current_user.tenant_id)
    tarea = await svc.delegar(tarea_id, body.asignado_a, current_user)
    return TareaRead.model_validate(tarea)


# ---------------------------------------------------------------------------
# Gestión: GET /tareas/admin — listado global con filtros
# ---------------------------------------------------------------------------

@router.get(
    "/admin",
    response_model=List[TareaRead],
)
async def listar_admin(
    asignado_a: Optional[uuid.UUID] = Query(None),
    asignado_por: Optional[uuid.UUID] = Query(None),
    materia_id: Optional[uuid.UUID] = Query(None),
    estado: Optional[TareaEstado] = Query(None),
    q: Optional[str] = Query(None),
    _grant=Depends(require_permission("tareas:gestionar")),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> List[TareaRead]:
    """
    Lista todas las tareas del tenant con filtros opcionales.

    Requiere tareas:gestionar.
    """
    svc = _make_tarea_service(db, current_user.tenant_id)
    tareas = await svc.listar_admin(
        current_user=current_user,
        asignado_a=asignado_a,
        asignado_por=asignado_por,
        materia_id=materia_id,
        estado=estado,
        q=q,
    )
    return [TareaRead.model_validate(t) for t in tareas]


# ---------------------------------------------------------------------------
# Gestión: DELETE /tareas/{tarea_id} — soft-delete
# ---------------------------------------------------------------------------

@router.delete(
    "/{tarea_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def eliminar_tarea(
    tarea_id: uuid.UUID,
    _grant=Depends(require_permission("tareas:gestionar")),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """
    Soft-delete una tarea. Requiere tareas:gestionar.
    """
    svc = _make_tarea_service(db, current_user.tenant_id)
    await svc.eliminar(tarea_id, current_user)


# ---------------------------------------------------------------------------
# Self-service: GET /tareas/mias — mis tareas
# ---------------------------------------------------------------------------

@router.get(
    "/mias",
    response_model=List[TareaRead],
)
async def listar_mias(
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> List[TareaRead]:
    """
    Lista las tareas asignadas al usuario autenticado.

    Cualquier usuario autenticado. No requiere tareas:gestionar.
    """
    svc = _make_tarea_service(db, current_user.tenant_id)
    tareas = await svc.listar_mias(current_user)
    return [TareaRead.model_validate(t) for t in tareas]


# ---------------------------------------------------------------------------
# Self-service: GET /tareas/{tarea_id} — detalle
# ---------------------------------------------------------------------------

@router.get(
    "/{tarea_id}",
    response_model=TareaRead,
)
async def detalle_tarea(
    tarea_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    has_gestionar: bool = Depends(_check_gestionar_optional),
) -> TareaRead:
    """
    Detalle de una tarea. Ownership enforced by service (D7).
    Users with tareas:gestionar can access any tenant tarea.
    """
    svc = _make_tarea_service(db, current_user.tenant_id)
    tarea = await svc.detalle(tarea_id, current_user, has_gestionar=has_gestionar)
    return TareaRead.model_validate(tarea)


# ---------------------------------------------------------------------------
# Self-service: PATCH /tareas/{tarea_id}/estado — cambiar estado
# ---------------------------------------------------------------------------

@router.patch(
    "/{tarea_id}/estado",
    response_model=TareaRead,
)
async def cambiar_estado(
    tarea_id: uuid.UUID,
    body: TareaUpdateEstado,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    has_gestionar: bool = Depends(_check_gestionar_optional),
) -> TareaRead:
    """
    Cambia el estado de una tarea según la matriz D3.

    asignado_a puede avanzar su propia tarea (D7); tareas:gestionar puede cambiar cualquier tarea.
    """
    svc = _make_tarea_service(db, current_user.tenant_id)
    tarea = await svc.cambiar_estado(tarea_id, body.estado, current_user, has_gestionar=has_gestionar)
    return TareaRead.model_validate(tarea)


# ---------------------------------------------------------------------------
# Self-service: POST /tareas/{tarea_id}/comentarios — agregar comentario
# ---------------------------------------------------------------------------

@router.post(
    "/{tarea_id}/comentarios",
    response_model=ComentarioTareaRead,
    status_code=status.HTTP_201_CREATED,
)
async def agregar_comentario(
    tarea_id: uuid.UUID,
    body: ComentarioTareaCreate,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    has_gestionar: bool = Depends(_check_gestionar_optional),
) -> ComentarioTareaRead:
    """
    Agrega un comentario al hilo de una tarea. Ownership enforced by service.
    """
    svc = _make_tarea_service(db, current_user.tenant_id)
    comentario = await svc.comentar(tarea_id, body, current_user, has_gestionar=has_gestionar)
    return ComentarioTareaRead.model_validate(comentario)


# ---------------------------------------------------------------------------
# Self-service: GET /tareas/{tarea_id}/comentarios — listar hilo
# ---------------------------------------------------------------------------

@router.get(
    "/{tarea_id}/comentarios",
    response_model=List[ComentarioTareaRead],
)
async def listar_comentarios(
    tarea_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    has_gestionar: bool = Depends(_check_gestionar_optional),
) -> List[ComentarioTareaRead]:
    """
    Lista el hilo de comentarios de una tarea. Ownership enforced by service.
    """
    svc = _make_tarea_service(db, current_user.tenant_id)
    comentarios = await svc.listar_comentarios(tarea_id, current_user, has_gestionar=has_gestionar)
    return [ComentarioTareaRead.model_validate(c) for c in comentarios]
