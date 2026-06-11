"""
Router CRUD asignaciones — /api/v1/asignaciones

C-07 Design Decision D8:
    Requiere require_permission("equipos:asignar") → COORDINADOR, ADMIN.
    tenant_id SIEMPRE desde el JWT (get_current_user), nunca del body.

Endpoints:
    GET    /asignaciones            — lista asignaciones activas (filtros opcionales)
    POST   /asignaciones            — crea una nueva asignación
    PATCH  /asignaciones/{id}       — edita una asignación existente
    DELETE /asignaciones/{id}       — baja lógica (soft delete)

Mapeo de excepciones del service:
    AsignacionNoEncontrada → 404
    UsuarioNoEncontrado    → 422
    ReferenciaInvalida     → 422

estado_vigencia: calculado en el router a partir del helper de vigencia.py.
snake_case; ≤500 LOC.
"""
import uuid
from datetime import date
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import CurrentUser, get_current_user, get_db, require_permission
from app.models.usuario import RolAsignacion
from app.models.vigencia import estado_vigencia
from app.repositories.usuario_repository import AsignacionRepository, UsuarioRepository
from app.schemas.usuario import (
    AsignacionCreate,
    AsignacionRead,
    AsignacionUpdate,
    UsuarioAsignableRead,
)
from app.services.usuario_service import (
    AsignacionNoEncontrada,
    AsignacionService,
    ReferenciaInvalida,
    UsuarioNoEncontrado,
)

router = APIRouter(prefix="/asignaciones", tags=["asignaciones"])


# ---------------------------------------------------------------------------
# Dependency helpers
# ---------------------------------------------------------------------------

def _make_service(db: AsyncSession, tenant_id: uuid.UUID) -> AsignacionService:
    return AsignacionService(
        asignacion_repo=AsignacionRepository(session=db, tenant_id=tenant_id),
        usuario_repo=UsuarioRepository(session=db, tenant_id=tenant_id),
    )


def _build_asignacion_read(
    asignacion,
    hoy: Optional[date] = None,
    usuario_nombre: Optional[str] = None,
    usuario_apellidos: Optional[str] = None,
) -> AsignacionRead:
    """
    Construye AsignacionRead desde el ORM model.
    Computa estado_vigencia con el helper puro (D4).
    Acepta nombre/apellidos resueltos externamente (batch o single fetch).
    """
    return AsignacionRead(
        id=asignacion.id,
        usuario_id=asignacion.usuario_id,
        usuario_nombre=usuario_nombre,
        usuario_apellidos=usuario_apellidos,
        rol=asignacion.rol,
        desde=asignacion.desde,
        hasta=asignacion.hasta,
        materia_id=asignacion.materia_id,
        carrera_id=asignacion.carrera_id,
        cohorte_id=asignacion.cohorte_id,
        comisiones=asignacion.comisiones or [],
        responsable_id=asignacion.responsable_id,
        estado_vigencia=estado_vigencia(asignacion.desde, asignacion.hasta, hoy),
        created_at=asignacion.created_at,
        updated_at=asignacion.updated_at,
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/usuarios", response_model=List[UsuarioAsignableRead])
async def buscar_usuarios_asignables(
    q: Optional[str] = Query(default=None),
    _grant=Depends(require_permission("equipos:asignar")),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> List[UsuarioAsignableRead]:
    """
    Búsqueda de usuarios para el combobox de asignaciones.

    Requiere permiso equipos:asignar (COORDINADOR, ADMIN).
    Tenant SIEMPRE desde el JWT — nunca de query/body.
    Devuelve solo campos no-PII: id, nombre, apellidos, email, legajo.
    Excluye soft-deleted. Máximo 20 resultados.
    """
    usuario_repo = UsuarioRepository(session=db, tenant_id=current_user.tenant_id)
    usuarios = await usuario_repo.buscar_asignables(q=q, limit=20)

    # Deserialize email_encrypted to plaintext for the response.
    # The ORM EncryptedString column handles decryption automatically.
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


@router.get("", response_model=List[AsignacionRead])
async def listar_asignaciones(
    usuario_id: Optional[uuid.UUID] = Query(default=None),
    rol: Optional[RolAsignacion] = Query(default=None),
    responsable_id: Optional[uuid.UUID] = Query(default=None),
    _grant=Depends(require_permission("equipos:asignar")),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> List[AsignacionRead]:
    """Lista asignaciones activas del tenant con filtros opcionales."""
    svc = _make_service(db, current_user.tenant_id)
    asignaciones = await svc.listar_asignaciones(
        usuario_id=usuario_id,
        rol=rol,
        responsable_id=responsable_id,
    )
    # Batch-fetch nombres: un único query IN para todos los usuario_id del listado.
    usuario_repo = UsuarioRepository(session=db, tenant_id=current_user.tenant_id)
    ids = list({a.usuario_id for a in asignaciones})
    nombres_map = await usuario_repo.get_nombres_por_ids(ids)
    hoy = date.today()
    return [
        _build_asignacion_read(
            a,
            hoy,
            usuario_nombre=nombres_map.get(a.usuario_id, (None, None))[0],
            usuario_apellidos=nombres_map.get(a.usuario_id, (None, None))[1],
        )
        for a in asignaciones
    ]


@router.post("", response_model=AsignacionRead, status_code=status.HTTP_201_CREATED)
async def crear_asignacion(
    body: AsignacionCreate,
    _grant=Depends(require_permission("equipos:asignar")),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AsignacionRead:
    """Crea una nueva asignación para un usuario del tenant."""
    svc = _make_service(db, current_user.tenant_id)
    try:
        asignacion = await svc.crear_asignacion(
            current_user,
            usuario_id=body.usuario_id,
            rol=body.rol,
            desde=body.desde,
            hasta=body.hasta,
            materia_id=body.materia_id,
            carrera_id=body.carrera_id,
            cohorte_id=body.cohorte_id,
            comisiones=body.comisiones,
            responsable_id=body.responsable_id,
        )
    except UsuarioNoEncontrado as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
    except ReferenciaInvalida as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
    # Single fetch for the assigned user's name.
    usuario_repo = UsuarioRepository(session=db, tenant_id=current_user.tenant_id)
    nombres_map = await usuario_repo.get_nombres_por_ids([asignacion.usuario_id])
    nombre, apellidos = nombres_map.get(asignacion.usuario_id, (None, None))
    return _build_asignacion_read(asignacion, usuario_nombre=nombre, usuario_apellidos=apellidos)


@router.patch("/{asignacion_id}", response_model=AsignacionRead)
async def editar_asignacion(
    asignacion_id: uuid.UUID,
    body: AsignacionUpdate,
    _grant=Depends(require_permission("equipos:asignar")),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AsignacionRead:
    """Edita una asignación existente (PATCH parcial)."""
    svc = _make_service(db, current_user.tenant_id)
    responsable_provided = "responsable_id" in (body.model_fields_set or set())
    try:
        asignacion = await svc.editar_asignacion(
            asignacion_id,
            rol=body.rol,
            desde=body.desde,
            hasta=body.hasta,
            materia_id=body.materia_id,
            carrera_id=body.carrera_id,
            cohorte_id=body.cohorte_id,
            comisiones=body.comisiones,
            responsable_id=body.responsable_id,
            _responsable_provided=responsable_provided,
        )
    except AsignacionNoEncontrada as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except ReferenciaInvalida as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
    # Single fetch for the assigned user's name.
    usuario_repo = UsuarioRepository(session=db, tenant_id=current_user.tenant_id)
    nombres_map = await usuario_repo.get_nombres_por_ids([asignacion.usuario_id])
    nombre, apellidos = nombres_map.get(asignacion.usuario_id, (None, None))
    return _build_asignacion_read(asignacion, usuario_nombre=nombre, usuario_apellidos=apellidos)


@router.delete("/{asignacion_id}", status_code=status.HTTP_204_NO_CONTENT)
async def dar_baja_asignacion(
    asignacion_id: uuid.UUID,
    _grant=Depends(require_permission("equipos:asignar")),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Baja lógica de asignación (soft delete). No borra automáticamente vencidas."""
    svc = _make_service(db, current_user.tenant_id)
    try:
        await svc.dar_baja_asignacion(asignacion_id)
    except AsignacionNoEncontrada as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
