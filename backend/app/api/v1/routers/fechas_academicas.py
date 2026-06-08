"""
Router fechas_academicas — /api/v1/fechas-academicas

C-17 Design Decisions D9:
    Permiso 'estructura:gestionar' para todo el módulo.
    Identidad del actor SIEMPRE desde el JWT — nunca de URL/body.

Endpoints:
    POST   /fechas-academicas                        — crear fecha
    GET    /fechas-academicas                        — listar tabular (filtrable)
    GET    /fechas-academicas/calendario             — vista calendario ordenada por fecha
    GET    /fechas-academicas/{fecha_id}             — obtener por id
    PATCH  /fechas-academicas/{fecha_id}             — editar
    DELETE /fechas-academicas/{fecha_id}             — baja lógica
    GET    /fechas-academicas/{fecha_id}/contenido-lms — fragmento HTML para LMS

snake_case; ≤500 LOC.
"""
import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import CurrentUser, get_current_user, get_db, require_permission
from app.models.academico import FechaAcademicaTipo
from app.repositories.audit_repository import AuditRepository
from app.repositories.fecha_academica_repository import FechaAcademicaRepository
from app.schemas.academico import (
    FechaAcademicaCreate,
    FechaAcademicaRead,
    FechaAcademicaUpdate,
    FragmentoLMSResponse,
)
from app.services.fecha_academica_html import generar_fragmento_calendario
from app.services.fecha_academica_service import (
    FechaAcademicaConflictError,
    FechaAcademicaNotFoundError,
    FechaAcademicaService,
)

router = APIRouter(prefix="/fechas-academicas", tags=["fechas-academicas"])


# ---------------------------------------------------------------------------
# Dependency helper
# ---------------------------------------------------------------------------

def _make_fecha_service(db: AsyncSession, tenant_id: uuid.UUID) -> FechaAcademicaService:
    return FechaAcademicaService(
        fecha_repo=FechaAcademicaRepository(session=db, tenant_id=tenant_id),
        audit_repo=AuditRepository(session=db, tenant_id=tenant_id),
    )


# ---------------------------------------------------------------------------
# POST /fechas-academicas — crear fecha
# ---------------------------------------------------------------------------

@router.post(
    "",
    response_model=FechaAcademicaRead,
    status_code=status.HTTP_201_CREATED,
)
async def crear_fecha_academica(
    body: FechaAcademicaCreate,
    _grant=Depends(require_permission("estructura:gestionar")),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> FechaAcademicaRead:
    """
    Crear una fecha académica.

    Requiere permiso estructura:gestionar.
    Identidad del actor desde el JWT.
    Devuelve 409 si ya existe la misma instancia activa.
    Devuelve 422 si tipo es inválido o numero < 1.
    """
    svc = _make_fecha_service(db, current_user.tenant_id)
    try:
        return await svc.crear(body, current_user)
    except FechaAcademicaConflictError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        )


# ---------------------------------------------------------------------------
# GET /fechas-academicas — listar tabular
# ---------------------------------------------------------------------------

@router.get(
    "",
    response_model=List[FechaAcademicaRead],
)
async def listar_fechas_academicas(
    materia_id: Optional[uuid.UUID] = Query(None),
    cohorte_id: Optional[uuid.UUID] = Query(None),
    tipo: Optional[FechaAcademicaTipo] = Query(None),
    periodo: Optional[str] = Query(None),
    _grant=Depends(require_permission("estructura:gestionar")),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> List[FechaAcademicaRead]:
    """
    Listar fechas académicas activas del tenant (vista tabular).

    Filtrables por materia, cohorte, tipo y periodo.
    Requiere permiso estructura:gestionar.
    """
    svc = _make_fecha_service(db, current_user.tenant_id)
    return await svc.listar(
        materia_id=materia_id,
        cohorte_id=cohorte_id,
        tipo=tipo,
        periodo=periodo,
    )


# ---------------------------------------------------------------------------
# GET /fechas-academicas/calendario — vista calendario
# ---------------------------------------------------------------------------

@router.get(
    "/calendario",
    response_model=List[FechaAcademicaRead],
)
async def listar_calendario(
    materia_id: uuid.UUID = Query(...),
    cohorte_id: uuid.UUID = Query(...),
    _grant=Depends(require_permission("estructura:gestionar")),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> List[FechaAcademicaRead]:
    """
    Vista calendario: fechas de una materia × cohorte ordenadas por fecha ASC (D7).

    Requiere permiso estructura:gestionar.
    materia_id y cohorte_id son requeridos.
    """
    svc = _make_fecha_service(db, current_user.tenant_id)
    return await svc.listar_calendario(materia_id, cohorte_id)


# ---------------------------------------------------------------------------
# GET /fechas-academicas/{fecha_id} — obtener por id
# ---------------------------------------------------------------------------

@router.get(
    "/{fecha_id}",
    response_model=FechaAcademicaRead,
)
async def obtener_fecha_academica(
    fecha_id: uuid.UUID,
    _grant=Depends(require_permission("estructura:gestionar")),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> FechaAcademicaRead:
    """
    Obtener una fecha académica por id.

    Requiere permiso estructura:gestionar.
    Devuelve 404 si no existe o pertenece a otro tenant.
    """
    svc = _make_fecha_service(db, current_user.tenant_id)
    try:
        return await svc.obtener(fecha_id)
    except FechaAcademicaNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )


# ---------------------------------------------------------------------------
# PATCH /fechas-academicas/{fecha_id} — editar
# ---------------------------------------------------------------------------

@router.patch(
    "/{fecha_id}",
    response_model=FechaAcademicaRead,
)
async def editar_fecha_academica(
    fecha_id: uuid.UUID,
    body: FechaAcademicaUpdate,
    _grant=Depends(require_permission("estructura:gestionar")),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> FechaAcademicaRead:
    """
    Editar campos mutables de una fecha académica.

    Requiere permiso estructura:gestionar.
    Solo modifica los campos presentes en el body.
    Devuelve 404 si no existe o pertenece a otro tenant.
    """
    svc = _make_fecha_service(db, current_user.tenant_id)
    try:
        return await svc.editar(fecha_id, body, current_user)
    except FechaAcademicaNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )


# ---------------------------------------------------------------------------
# DELETE /fechas-academicas/{fecha_id} — baja lógica
# ---------------------------------------------------------------------------

@router.delete(
    "/{fecha_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def eliminar_fecha_academica(
    fecha_id: uuid.UUID,
    _grant=Depends(require_permission("estructura:gestionar")),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """
    Dar de baja (soft delete) una fecha académica.

    Requiere permiso estructura:gestionar.
    Devuelve 404 si no existe o pertenece a otro tenant.
    Registra auditoría FECHA_ACADEMICA_GESTIONAR.
    """
    svc = _make_fecha_service(db, current_user.tenant_id)
    try:
        await svc.eliminar(fecha_id, current_user)
    except FechaAcademicaNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )


# ---------------------------------------------------------------------------
# GET /fechas-academicas/{fecha_id}/contenido-lms — fragmento HTML LMS
# ---------------------------------------------------------------------------

@router.get(
    "/{fecha_id}/contenido-lms",
    response_model=FragmentoLMSResponse,
)
async def contenido_lms(
    fecha_id: uuid.UUID,
    _grant=Depends(require_permission("estructura:gestionar")),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> FragmentoLMSResponse:
    """
    Generar fragmento HTML del calendario LMS para una fecha académica.

    D6: función pura con html.escape — anti-XSS.
    Requiere permiso estructura:gestionar.
    Devuelve 404 si no existe o pertenece a otro tenant.

    NOTE: This endpoint returns the LMS fragment for the specific fecha's
    materia × cohorte (all active fechas for that combination).
    """
    svc = _make_fecha_service(db, current_user.tenant_id)
    try:
        fecha = await svc.obtener(fecha_id)
    except FechaAcademicaNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )

    # Get all fechas for the same materia × cohorte (calendar context)
    fechas_models = await FechaAcademicaRepository(
        session=db, tenant_id=current_user.tenant_id
    ).listar_calendario(fecha.materia_id, fecha.cohorte_id)

    html_content = generar_fragmento_calendario(fechas_models)
    return FragmentoLMSResponse(html=html_content)
