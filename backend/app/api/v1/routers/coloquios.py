"""
Router coloquios — /api/v1/coloquios

C-14 Design:
    D6  — dos permisos: 'coloquios:gestionar' (COORD/ADMIN/PROF) y
          'coloquios:reservar' (ALUMNO). RBAC fail-closed.
    Regla #8 — identidad del alumno SIEMPRE desde el JWT, nunca del body.
    HU-47 — resolve_domain_user_id traduce auth_identity_id → usuario.id antes de
             llamar al servicio (necesario en crear_reserva, cancelar_reserva y
             mis-convocatorias).

Endpoints de gestión (coloquios:gestionar):
    POST   /coloquios/convocatorias          — crear convocatoria + turnos
    GET    /coloquios/convocatorias          — listar con métricas
    POST   /coloquios/convocatorias/{id}/candidatos — importar candidatos
    POST   /coloquios/convocatorias/{id}/cerrar     — cerrar convocatoria
    GET    /coloquios/agenda                 — agenda de reservas activas
    GET    /coloquios/metricas               — panel de métricas globales
    GET    /coloquios/convocatorias/{id}/resultados — registro académico
    POST   /coloquios/convocatorias/{id}/resultados — registrar nota final

Endpoints de reserva (coloquios:reservar):
    GET    /coloquios/mis-convocatorias      — convocatorias del alumno con turnos y cupos
    POST   /coloquios/reservas               — reservar turno (alumno)
    DELETE /coloquios/reservas/{reserva_id}  — cancelar reserva (alumno)
    GET    /coloquios/convocatorias/{id}/mi-resultado — resultado propio

snake_case; ≤500 LOC.
"""
import uuid
from datetime import date
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import CurrentUser, get_current_user, get_db, require_permission, resolve_domain_user_id
from app.repositories.audit_repository import AuditRepository
from app.repositories.evaluacion_repository import (
    CandidatoEvaluacionRepository,
    EvaluacionRepository,
    ReservaEvaluacionRepository,
    ResultadoEvaluacionRepository,
    TurnoEvaluacionRepository,
)
from app.schemas.evaluacion import (
    AgendaItemRead,
    ConvocatoriaConTurnosRead,
    ConvocatoriaMetricasRead,
    ConvocatoriasAlumnoRead,
    CrearConvocatoriaRequest,
    ImportarCandidatosRequest,
    MetricasRead,
    ReservaRead,
    ReservaRequest,
    ResultadoRead,
    ResultadoRequest,
)
from app.services.evaluacion_service import EvaluacionService, EvaluacionValidationError

router = APIRouter(prefix="/coloquios", tags=["coloquios"])


# ---------------------------------------------------------------------------
# Service factory — inyecta repos tenant-scoped (patrón encuentros)
# ---------------------------------------------------------------------------

def _make_evaluacion_service(db: AsyncSession, tenant_id: uuid.UUID) -> EvaluacionService:
    return EvaluacionService(
        evaluacion_repo=EvaluacionRepository(session=db, tenant_id=tenant_id),
        turno_repo=TurnoEvaluacionRepository(session=db, tenant_id=tenant_id),
        candidato_repo=CandidatoEvaluacionRepository(session=db, tenant_id=tenant_id),
        reserva_repo=ReservaEvaluacionRepository(session=db, tenant_id=tenant_id),
        resultado_repo=ResultadoEvaluacionRepository(session=db, tenant_id=tenant_id),
        audit_repo=AuditRepository(session=db, tenant_id=tenant_id),
    )


# ---------------------------------------------------------------------------
# Gestión: POST /coloquios/convocatorias
# ---------------------------------------------------------------------------

@router.post(
    "/convocatorias",
    response_model=ConvocatoriaConTurnosRead,
    status_code=status.HTTP_201_CREATED,
)
async def crear_convocatoria(
    body: CrearConvocatoriaRequest,
    _grant=Depends(require_permission("coloquios:gestionar")),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ConvocatoriaConTurnosRead:
    """
    Crea una convocatoria de evaluación con sus turnos reservables.

    Requiere permiso coloquios:gestionar.
    Identidad del actor desde el JWT.
    """
    svc = _make_evaluacion_service(db, current_user.tenant_id)
    try:
        return await svc.crear_convocatoria(body, current_user)
    except EvaluacionValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        )


# ---------------------------------------------------------------------------
# Gestión: GET /coloquios/convocatorias — listar con métricas
# ---------------------------------------------------------------------------

@router.get(
    "/convocatorias",
    response_model=List[ConvocatoriaMetricasRead],
)
async def listar_convocatorias(
    _grant=Depends(require_permission("coloquios:gestionar")),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> List[ConvocatoriaMetricasRead]:
    """
    Lista las convocatorias con métricas derivadas (convocados, reservas, cupos).

    Requiere permiso coloquios:gestionar.
    """
    svc = _make_evaluacion_service(db, current_user.tenant_id)
    return await svc.listar_con_metricas()


# ---------------------------------------------------------------------------
# Gestión: POST /coloquios/convocatorias/{evaluacion_id}/candidatos
# ---------------------------------------------------------------------------

@router.post(
    "/convocatorias/{evaluacion_id}/candidatos",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def importar_candidatos(
    evaluacion_id: uuid.UUID,
    body: ImportarCandidatosRequest,
    _grant=Depends(require_permission("coloquios:gestionar")),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """
    Importa el padrón de candidatos a una convocatoria (idempotente).

    Requiere permiso coloquios:gestionar.
    """
    if body.evaluacion_id != evaluacion_id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="evaluacion_id del body no coincide con el de la URL",
        )
    svc = _make_evaluacion_service(db, current_user.tenant_id)
    await svc.importar_candidatos(body, current_user)


# ---------------------------------------------------------------------------
# Gestión: POST /coloquios/convocatorias/{evaluacion_id}/cerrar
# ---------------------------------------------------------------------------

@router.post(
    "/convocatorias/{evaluacion_id}/cerrar",
    status_code=status.HTTP_200_OK,
)
async def cerrar_convocatoria(
    evaluacion_id: uuid.UUID,
    _grant=Depends(require_permission("coloquios:gestionar")),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Cierra una convocatoria (no acepta nuevas reservas).

    Requiere permiso coloquios:gestionar.
    """
    svc = _make_evaluacion_service(db, current_user.tenant_id)
    return await svc.cerrar_convocatoria(evaluacion_id, current_user)


# ---------------------------------------------------------------------------
# Gestión: GET /coloquios/agenda
# ---------------------------------------------------------------------------

@router.get(
    "/agenda",
    response_model=List[AgendaItemRead],
)
async def agenda(
    materia_id: Optional[uuid.UUID] = Query(None),
    fecha_desde: Optional[date] = Query(None),
    fecha_hasta: Optional[date] = Query(None),
    _grant=Depends(require_permission("coloquios:gestionar")),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> List[AgendaItemRead]:
    """
    Agenda consolidada de reservas activas (filtrable).

    Requiere permiso coloquios:gestionar.
    """
    svc = _make_evaluacion_service(db, current_user.tenant_id)
    return await svc.agenda(
        materia_id=materia_id,
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
    )


# ---------------------------------------------------------------------------
# Gestión: GET /coloquios/metricas
# ---------------------------------------------------------------------------

@router.get(
    "/metricas",
    response_model=MetricasRead,
)
async def metricas(
    _grant=Depends(require_permission("coloquios:gestionar")),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MetricasRead:
    """
    Panel de métricas globales del módulo (F7.1).

    Requiere permiso coloquios:gestionar.
    """
    svc = _make_evaluacion_service(db, current_user.tenant_id)
    return await svc.metricas(current_user)


# ---------------------------------------------------------------------------
# Gestión: GET/POST /coloquios/convocatorias/{evaluacion_id}/resultados
# ---------------------------------------------------------------------------

@router.get(
    "/convocatorias/{evaluacion_id}/resultados",
    response_model=List[ResultadoRead],
)
async def registro_academico(
    evaluacion_id: uuid.UUID,
    _grant=Depends(require_permission("coloquios:gestionar")),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> List[ResultadoRead]:
    """
    Registro académico consolidado de notas finales.

    Requiere permiso coloquios:gestionar.
    """
    svc = _make_evaluacion_service(db, current_user.tenant_id)
    return await svc.registro_academico(evaluacion_id)


@router.post(
    "/convocatorias/{evaluacion_id}/resultados",
    response_model=ResultadoRead,
    status_code=status.HTTP_200_OK,
)
async def registrar_resultado(
    evaluacion_id: uuid.UUID,
    body: ResultadoRequest,
    _grant=Depends(require_permission("coloquios:gestionar")),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ResultadoRead:
    """
    Registra o actualiza la nota final de un alumno.

    Upsert por (evaluacion_id, alumno_id). Requiere coloquios:gestionar.
    """
    svc = _make_evaluacion_service(db, current_user.tenant_id)
    return await svc.registrar_resultado(body, current_user)


# ---------------------------------------------------------------------------
# Reserva: GET /coloquios/mis-convocatorias  (HU-47)
# ---------------------------------------------------------------------------

@router.get(
    "/mis-convocatorias",
    response_model=List[ConvocatoriasAlumnoRead],
)
async def mis_convocatorias(
    _grant=Depends(require_permission("coloquios:reservar")),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> List[ConvocatoriasAlumnoRead]:
    """
    Devuelve las convocatorias donde el alumno autenticado es candidato.

    Solo convocatorias abiertas. Incluye turnos con cupos_disponibles derivados.
    Identidad SIEMPRE del JWT — domain_user_id resuelto aquí.
    Requiere permiso coloquios:reservar.
    """
    domain_user_id = await resolve_domain_user_id(current_user, db)
    svc = _make_evaluacion_service(db, current_user.tenant_id)
    return await svc.listar_mis_convocatorias(domain_user_id)


# ---------------------------------------------------------------------------
# Reserva: POST /coloquios/reservas
# ---------------------------------------------------------------------------

@router.post(
    "/reservas",
    response_model=ReservaRead,
    status_code=status.HTTP_201_CREATED,
)
async def reservar_turno(
    body: ReservaRequest,
    _grant=Depends(require_permission("coloquios:reservar")),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ReservaRead:
    """
    Reserva un turno para el ALUMNO autenticado.

    Identidad del alumno SIEMPRE del JWT — domain_user_id resuelto aquí.
    Requiere permiso coloquios:reservar.
    """
    domain_user_id = await resolve_domain_user_id(current_user, db)
    svc = _make_evaluacion_service(db, current_user.tenant_id)
    return await svc.crear_reserva(body, current_user, domain_user_id)


# ---------------------------------------------------------------------------
# Reserva: DELETE /coloquios/reservas/{reserva_id}
# ---------------------------------------------------------------------------

@router.delete(
    "/reservas/{reserva_id}",
    status_code=status.HTTP_200_OK,
    response_model=ReservaRead,
)
async def cancelar_reserva(
    reserva_id: uuid.UUID,
    _grant=Depends(require_permission("coloquios:reservar")),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ReservaRead:
    """
    Cancela la propia reserva del ALUMNO autenticado.

    Solo el dueño puede cancelar. domain_user_id resuelto aquí.
    Requiere coloquios:reservar.
    """
    domain_user_id = await resolve_domain_user_id(current_user, db)
    svc = _make_evaluacion_service(db, current_user.tenant_id)
    return await svc.cancelar_reserva(reserva_id, current_user, domain_user_id)


# ---------------------------------------------------------------------------
# Reserva: GET /coloquios/convocatorias/{evaluacion_id}/mi-resultado
# ---------------------------------------------------------------------------

@router.get(
    "/convocatorias/{evaluacion_id}/mi-resultado",
    response_model=ResultadoRead,
)
async def mi_resultado(
    evaluacion_id: uuid.UUID,
    _grant=Depends(require_permission("coloquios:reservar")),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ResultadoRead:
    """
    El ALUMNO consulta su propio resultado.

    Solo devuelve el resultado del alumno autenticado.
    Requiere permiso coloquios:reservar.
    """
    svc = _make_evaluacion_service(db, current_user.tenant_id)
    return await svc.get_resultado_alumno(evaluacion_id, current_user)
