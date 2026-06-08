"""
Router /api/v1/analisis — endpoints de análisis, atrasados y reportes.

C-11 Design Decision D5:
    Todos los endpoints bajo require_permission("atrasados:ver").
    Scope (propio/global) determinado por el grant RBAC del JWT.
    tenant_id/usuario_id NUNCA leídos del body ni de query params.

Endpoints:
    GET  /analisis/atrasados           — lista de alumnos atrasados (RN-06)
    GET  /analisis/ranking             — ranking de aprobadas (RN-09)
    GET  /analisis/reporte-materia     — métricas consolidadas (F2.4)
    GET  /analisis/notas-finales       — notas finales por alumno (F2.5)
    GET  /analisis/monitor             — monitor general/seguimiento (F2.7/F2.8/F2.9)
    POST /analisis/sin-corregir/export — exportación de TPs sin corregir (F2.6)

snake_case; ≤500 LOC. Sin lógica de negocio (solo guard + delegación al service).
"""
import csv
import io
import uuid
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, Query, Response
from fastapi import status as http_status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import CurrentUser, get_current_user, get_db, require_permission, resolve_domain_user_id
from app.repositories.analisis_repository import AnalisisRepository
from app.repositories.audit_repository import AuditRepository
from app.schemas.analisis import (
    AlumnoAtrasado,
    ExportSinCorregirRequest,
    MonitorFila,
    MonitorFiltros,
    NotaFinalAlumno,
    RankingFila,
    ReporteMateria,
)
from app.services.analisis_service import AnalisisService

router = APIRouter(prefix="/analisis", tags=["analisis"])


# ---------------------------------------------------------------------------
# Dependency helpers
# ---------------------------------------------------------------------------

def _make_service(db: AsyncSession, tenant_id: uuid.UUID) -> AnalisisService:
    return AnalisisService(
        repo=AnalisisRepository(session=db, tenant_id=tenant_id),
        audit_repo=AuditRepository(session=db, tenant_id=tenant_id),
    )


# ---------------------------------------------------------------------------
# GET /analisis/atrasados — RN-06
# ---------------------------------------------------------------------------

@router.get("/atrasados", response_model=List[AlumnoAtrasado])
async def listar_atrasados(
    materia_id: uuid.UUID = Query(...),
    cohorte_id: uuid.UUID = Query(...),
    actividades: List[str] = Query(default=[]),
    grant=Depends(require_permission("atrasados:ver")),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> List[AlumnoAtrasado]:
    """
    Lista de alumnos atrasados para materia×cohorte×actividades.

    Scope propio: solo importaciones del docente autenticado.
    Scope global: todas las importaciones del tenant.
    Identidad/tenant SIEMPRE desde el JWT (regla dura #8).
    """
    domain_user_id = await resolve_domain_user_id(current_user, db)
    svc = _make_service(db, current_user.tenant_id)
    return await svc.atrasados(
        materia_id=materia_id,
        cohorte_id=cohorte_id,
        actividades=actividades,
        current_user=current_user,
        grant=grant,
        domain_user_id=domain_user_id,
    )


# ---------------------------------------------------------------------------
# GET /analisis/ranking — RN-09
# ---------------------------------------------------------------------------

@router.get("/ranking", response_model=List[RankingFila])
async def listar_ranking(
    materia_id: uuid.UUID = Query(...),
    actividades: List[str] = Query(default=[]),
    grant=Depends(require_permission("atrasados:ver")),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> List[RankingFila]:
    """
    Ranking de alumnos por cantidad de actividades aprobadas (RN-09).
    Solo alumnos con al menos 1 aprobada. Ordenado descendente.
    """
    domain_user_id = await resolve_domain_user_id(current_user, db)
    svc = _make_service(db, current_user.tenant_id)
    return await svc.ranking(
        materia_id=materia_id,
        actividades=actividades,
        current_user=current_user,
        grant=grant,
        domain_user_id=domain_user_id,
    )


# ---------------------------------------------------------------------------
# GET /analisis/reporte-materia — F2.4
# ---------------------------------------------------------------------------

@router.get("/reporte-materia", response_model=ReporteMateria)
async def obtener_reporte_materia(
    materia_id: uuid.UUID = Query(...),
    cohorte_id: uuid.UUID = Query(...),
    actividades: List[str] = Query(default=[]),
    grant=Depends(require_permission("atrasados:ver")),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ReporteMateria:
    """
    Métricas consolidadas de una materia×cohorte (F2.4).
    sin_datos=True si no hay calificaciones o actividades vacías.
    """
    domain_user_id = await resolve_domain_user_id(current_user, db)
    svc = _make_service(db, current_user.tenant_id)
    return await svc.reporte_materia(
        materia_id=materia_id,
        cohorte_id=cohorte_id,
        actividades=actividades,
        current_user=current_user,
        grant=grant,
        domain_user_id=domain_user_id,
    )


# ---------------------------------------------------------------------------
# GET /analisis/notas-finales — F2.5
# ---------------------------------------------------------------------------

@router.get("/notas-finales", response_model=List[NotaFinalAlumno])
async def listar_notas_finales(
    materia_id: uuid.UUID = Query(...),
    actividades: List[str] = Query(default=[]),
    grant=Depends(require_permission("atrasados:ver")),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> List[NotaFinalAlumno]:
    """
    Notas finales por alumno (promedio simple de nota_numerica, D7).
    Incluye alumnos sin calificaciones (nota_final=None).
    """
    domain_user_id = await resolve_domain_user_id(current_user, db)
    svc = _make_service(db, current_user.tenant_id)
    return await svc.notas_finales(
        materia_id=materia_id,
        actividades=actividades,
        current_user=current_user,
        grant=grant,
        domain_user_id=domain_user_id,
    )


# ---------------------------------------------------------------------------
# GET /analisis/monitor — F2.7/F2.8/F2.9
# ---------------------------------------------------------------------------

@router.get("/monitor", response_model=List[MonitorFila])
async def listar_monitor(
    materia_id: Optional[uuid.UUID] = Query(default=None),
    cohorte_id: Optional[uuid.UUID] = Query(default=None),
    comision: Optional[str] = Query(default=None),
    regional: Optional[str] = Query(default=None),
    busqueda: Optional[str] = Query(default=None),
    actividad: Optional[str] = Query(default=None),
    min_cumplidas: Optional[int] = Query(default=None),
    fecha_desde: Optional[datetime] = Query(default=None),
    fecha_hasta: Optional[datetime] = Query(default=None),
    actividades: List[str] = Query(default=[]),
    grant=Depends(require_permission("atrasados:ver")),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> List[MonitorFila]:
    """
    Monitor general/seguimiento (F2.7/F2.8/F2.9).

    Scope global (COORDINADOR/ADMIN): todos los alumnos del tenant.
    Scope propio (PROFESOR/TUTOR): alumnos de sus materias asignadas.

    Filtros opcionales: comision, regional, busqueda, rango de fechas por importado_at.
    Rango de fechas inválido → 422 (validado por MonitorFiltros).
    """
    # Validar rango de fechas (delegado a MonitorFiltros para el 422)
    filtros = MonitorFiltros(
        materia_id=materia_id,
        cohorte_id=cohorte_id,
        comision=comision,
        regional=regional,
        busqueda=busqueda,
        actividad=actividad,
        min_cumplidas=min_cumplidas,
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
    )

    domain_user_id = await resolve_domain_user_id(current_user, db)
    svc = _make_service(db, current_user.tenant_id)
    return await svc.monitor(
        filtros=filtros,
        actividades=actividades,
        current_user=current_user,
        grant=grant,
        domain_user_id=domain_user_id,
    )


# ---------------------------------------------------------------------------
# POST /analisis/sin-corregir/export — F2.6
# ---------------------------------------------------------------------------

@router.post("/sin-corregir/export")
async def exportar_sin_corregir(
    body: ExportSinCorregirRequest,
    grant=Depends(require_permission("atrasados:ver")),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Response:
    """
    Exporta TPs sin corregir como CSV (F2.6, RN-07/RN-08).

    Solo actividades textuales (RN-08); numéricas excluidas.
    Registra AuditEvent con modulo='atrasados' (D8).
    Identidad/tenant desde JWT — nunca del body.
    """
    svc = _make_service(db, current_user.tenant_id)
    entregas = await svc.export_sin_corregir(
        materia_id=body.materia_id,
        cohorte_id=body.cohorte_id,
        filas_finalizacion=body.filas_finalizacion,
        current_user=current_user,
    )

    # Serializar CSV en el router (D8: servicio devuelve filas, router serializa)
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["entrada_padron_id", "actividad", "completado_at"])
    for entrega in entregas:
        writer.writerow([
            str(entrega.entrada_padron_id),
            entrega.actividad,
            str(entrega.completado_at) if hasattr(entrega, "completado_at") and entrega.completado_at else "",
        ])

    return Response(
        content=buf.getvalue(),
        media_type="text/csv",
        headers={
            "Content-Disposition": "attachment; filename=sin_corregir.csv"
        },
    )
