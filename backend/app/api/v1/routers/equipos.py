"""
Router equipos — /api/v1/equipos

C-08 Design Decisions D2/D4:
    Proyección derivada de Asignacion (C-07). Sin tabla nueva.
    Identidad del actor SIEMPRE desde el JWT — nunca de URL/body.
    equipos:ver  → GET /mis-equipos, GET /equipos, GET /exportar.
    equipos:asignar → POST /asignacion-masiva, POST /clonar, PATCH /vigencia-general.

Endpoints:
    GET  /equipos/mis-equipos       — asignaciones propias con estado_vigencia
    GET  /equipos                   — consulta por tripleta + filtros opcionales
    POST /equipos/asignacion-masiva — lote atómico de asignaciones → ResumenLote
    POST /equipos/clonar            — clonación no-destructiva → ResumenClonacion
    PATCH /equipos/vigencia-general — actualiza fechas del equipo → afectadas
    GET  /equipos/exportar          — CSV adjunto con estado_vigencia

snake_case; ≤500 LOC.
"""
import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import CurrentUser, get_current_user, get_db, require_permission, resolve_domain_user_id, try_resolve_domain_user_id
from app.repositories.audit_repository import AuditRepository
from app.repositories.estructura_repository import CohorteRepository, MateriaRepository
from app.repositories.mensajeria_repository import MensajeriaRepository
from app.repositories.usuario_repository import AsignacionRepository, UsuarioRepository
from app.schemas.equipo import (
    AsignacionMasivaRequest,
    ClonarEquipoRequest,
    EquipoQuery,
    MisEquiposItem,
    ResumenClonacion,
    ResumenLote,
    VigenciaGeneralRequest,
)
from app.services.equipo_service import EquipoService
from app.services.usuario_service import ReferenciaInvalida, UsuarioNoEncontrado

router = APIRouter(prefix="/equipos", tags=["equipos"])


# ---------------------------------------------------------------------------
# Dependency helper
# ---------------------------------------------------------------------------

def _make_equipo_service(db: AsyncSession, tenant_id: uuid.UUID) -> EquipoService:
    asig_repo = AsignacionRepository(session=db, tenant_id=tenant_id)
    usr_repo = UsuarioRepository(session=db, tenant_id=tenant_id)
    audit_repo = AuditRepository(session=db, tenant_id=tenant_id)
    mensajeria_repo = MensajeriaRepository(session=db, tenant_id=tenant_id)
    materia_repo = MateriaRepository(session=db, tenant_id=tenant_id)
    cohorte_repo = CohorteRepository(session=db, tenant_id=tenant_id)
    return EquipoService(
        asignacion_repo=asig_repo,
        usuario_repo=usr_repo,
        audit_repo=audit_repo,
        mensajeria_repo=mensajeria_repo,
        materia_repo=materia_repo,
        cohorte_repo=cohorte_repo,
    )


# ---------------------------------------------------------------------------
# GET /equipos/mis-equipos — asignaciones propias del actor autenticado
# ---------------------------------------------------------------------------

@router.get("/mis-equipos", response_model=List[MisEquiposItem])
async def get_mis_equipos(
    _grant=Depends(require_permission("equipos:ver")),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> List[MisEquiposItem]:
    """
    Retorna las asignaciones del usuario autenticado con estado_vigencia derivado.

    Identidad del actor desde el JWT — nunca del body ni de la URL.
    Requiere permiso equipos:ver.
    """
    domain_user_id = await resolve_domain_user_id(current_user, db)
    svc = _make_equipo_service(db, current_user.tenant_id)
    return await svc.listar_mis_equipos(current_user, domain_user_id=domain_user_id)


# ---------------------------------------------------------------------------
# GET /equipos — consulta por tripleta + filtros opcionales
# ---------------------------------------------------------------------------

@router.get("", response_model=List[MisEquiposItem])
async def get_equipo(
    materia_id: uuid.UUID = Query(...),
    carrera_id: uuid.UUID = Query(...),
    cohorte_id: uuid.UUID = Query(...),
    rol: Optional[str] = Query(None),
    responsable_id: Optional[uuid.UUID] = Query(None),
    _grant=Depends(require_permission("equipos:ver")),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> List[MisEquiposItem]:
    """
    Consulta el equipo docente de una tripleta (materia, carrera, cohorte).
    Filtros opcionales: rol, responsable_id.
    Requiere permiso equipos:ver.
    """
    from app.models.usuario import RolAsignacion
    rol_enum = None
    if rol is not None:
        try:
            rol_enum = RolAsignacion(rol)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Rol inválido: {rol}",
            )

    query = EquipoQuery(
        materia_id=materia_id,
        carrera_id=carrera_id,
        cohorte_id=cohorte_id,
        rol=rol_enum,
        responsable_id=responsable_id,
    )
    svc = _make_equipo_service(db, current_user.tenant_id)
    return await svc.consultar_equipo(query)


# ---------------------------------------------------------------------------
# POST /equipos/asignacion-masiva — lote atómico de asignaciones
# ---------------------------------------------------------------------------

@router.post(
    "/asignacion-masiva",
    response_model=ResumenLote,
    status_code=status.HTTP_201_CREATED,
)
async def asignacion_masiva(
    body: AsignacionMasivaRequest,
    _grant=Depends(require_permission("equipos:asignar")),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ResumenLote:
    """
    Crea N asignaciones atómicamente para el equipo indicado.

    Valida todos los usuario_ids y el responsable_id antes de persistir.
    Si cualquier validación falla → 422, rollback total (0 filas creadas).
    Emite auditoría EQUIPOS_ASIGNACION_MASIVA.
    Requiere permiso equipos:asignar.
    """
    domain_user_id = await try_resolve_domain_user_id(current_user, db)
    svc = _make_equipo_service(db, current_user.tenant_id)
    try:
        return await svc.asignacion_masiva(current_user, body, domain_user_id=domain_user_id)
    except (UsuarioNoEncontrado, ReferenciaInvalida) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        )


# ---------------------------------------------------------------------------
# POST /equipos/clonar — clonación no-destructiva entre tripletas
# ---------------------------------------------------------------------------

@router.post(
    "/clonar",
    response_model=ResumenClonacion,
    status_code=status.HTTP_201_CREATED,
)
async def clonar_equipo(
    body: ClonarEquipoRequest,
    _grant=Depends(require_permission("equipos:asignar")),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ResumenClonacion:
    """
    Clona las asignaciones del equipo origen al destino.
    No-destructivo: omite duplicados (mismo usuario_id + rol en destino).
    Emite auditoría EQUIPOS_CLONAR.
    Requiere permiso equipos:asignar.
    """
    domain_user_id = await try_resolve_domain_user_id(current_user, db)
    svc = _make_equipo_service(db, current_user.tenant_id)
    return await svc.clonar_equipo(current_user, body, domain_user_id=domain_user_id)


# ---------------------------------------------------------------------------
# PATCH /equipos/vigencia-general — actualiza fechas del equipo completo
# ---------------------------------------------------------------------------

@router.patch("/vigencia-general")
async def vigencia_general(
    body: VigenciaGeneralRequest,
    _grant=Depends(require_permission("equipos:asignar")),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Actualiza las fechas (desde/hasta) de todas las asignaciones activas del equipo.
    Retorna {"afectadas": N}.
    Emite auditoría EQUIPOS_VIGENCIA_GENERAL.
    Requiere permiso equipos:asignar.
    """
    svc = _make_equipo_service(db, current_user.tenant_id)
    afectadas = await svc.modificar_vigencia_general(current_user, body)
    return {"afectadas": afectadas}


# ---------------------------------------------------------------------------
# GET /equipos/exportar — CSV adjunto
# ---------------------------------------------------------------------------

@router.get("/exportar")
async def exportar_equipo(
    materia_id: uuid.UUID = Query(...),
    carrera_id: uuid.UUID = Query(...),
    cohorte_id: uuid.UUID = Query(...),
    rol: Optional[str] = Query(None),
    responsable_id: Optional[uuid.UUID] = Query(None),
    _grant=Depends(require_permission("equipos:ver")),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Response:
    """
    Exporta el equipo docente como CSV adjunto.
    Columnas: asignacion_id, usuario_id, rol, materia_id, carrera_id,
              cohorte_id, comisiones, desde, hasta, estado_vigencia.
    Sin PII cifrada (D8).
    Requiere permiso equipos:ver.
    """
    from app.models.usuario import RolAsignacion
    rol_enum = None
    if rol is not None:
        try:
            rol_enum = RolAsignacion(rol)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Rol inválido: {rol}",
            )

    query = EquipoQuery(
        materia_id=materia_id,
        carrera_id=carrera_id,
        cohorte_id=cohorte_id,
        rol=rol_enum,
        responsable_id=responsable_id,
    )
    svc = _make_equipo_service(db, current_user.tenant_id)
    csv_content = await svc.exportar_equipo(query)

    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=equipo.csv"},
    )
