"""
Router calificaciones — /api/v1/calificaciones

C-10 Design Decisions D5, D7, D8, D9:
    Endpoints de importación, preview, umbral y reporte de finalización.

    tenant_id y user_id SIEMPRE desde el JWT (get_current_user), nunca del body.
    require_permission("calificaciones:importar") en preview, importar y finalizacion.
    require_permission("calificaciones:configurar-umbral") en umbral PUT/GET.

Endpoints:
    POST /calificaciones/preview      — multipart file; returns PreviewCalificaciones
    POST /calificaciones/importar     — JSON ImportarCalificacionesRequest; returns list[CalificacionRead]
    POST /calificaciones/finalizacion — JSON ReporteFinalizacionRequest; returns list[EntregaSinCorregir]
    PUT  /calificaciones/umbral       — JSON ConfigurarUmbralRequest; returns UmbralMateriaRead
    GET  /calificaciones/umbral       — query materia_id; returns UmbralMateriaRead

snake_case; ≤500 LOC.
"""
import uuid
from typing import List

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import CurrentUser, get_current_user, get_db, require_permission, resolve_domain_user_id
from app.repositories.audit_repository import AuditRepository
from app.repositories.calificacion_repository import CalificacionRepository
from app.repositories.padron_repository import PadronRepository
from app.schemas.calificacion import (
    CalificacionRead,
    ConfigurarUmbralRequest,
    EntregaSinCorregir,
    ImportarCalificacionesRequest,
    PreviewCalificaciones,
    ReporteFinalizacionRequest,
    UmbralMateriaRead,
)
from app.services.calificacion_parser import CalificacionValidationError
from app.services.calificacion_service import CalificacionService
from app.services.umbral_service import UmbralService

router = APIRouter(prefix="/calificaciones", tags=["calificaciones"])


# ---------------------------------------------------------------------------
# Dependency helpers
# ---------------------------------------------------------------------------

def _make_cal_service(db: AsyncSession, tenant_id: uuid.UUID) -> CalificacionService:
    repo = CalificacionRepository(session=db, tenant_id=tenant_id)
    padron_repo = PadronRepository(session=db, tenant_id=tenant_id)
    audit_repo = AuditRepository(session=db, tenant_id=tenant_id)
    return CalificacionService(repo=repo, padron_repo=padron_repo, audit_repo=audit_repo)


def _make_umbral_service(db: AsyncSession, tenant_id: uuid.UUID) -> UmbralService:
    repo = CalificacionRepository(session=db, tenant_id=tenant_id)
    return UmbralService(repo=repo)


# ---------------------------------------------------------------------------
# POST /calificaciones/preview — parse file, no DB write (D7)
# ---------------------------------------------------------------------------

@router.post("/preview", response_model=PreviewCalificaciones)
async def preview_calificaciones(
    file: UploadFile = File(...),
    _grant=Depends(require_permission("calificaciones:importar")),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PreviewCalificaciones:
    """
    Parsea el archivo de calificaciones y retorna actividades detectadas sin escribir en DB.

    Acepta .xlsx y .csv.
    Retorna 422 si el archivo es inválido, tiene columnas de identidad faltantes.

    Identidad del actor desde el JWT — nunca del body o URL.
    """
    file_bytes = await file.read()
    filename = file.filename or "calificaciones.xlsx"

    svc = _make_cal_service(db, current_user.tenant_id)
    try:
        result = await svc.preview(
            file_bytes=file_bytes,
            filename=filename,
            current_user=current_user,
        )
    except CalificacionValidationError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail)

    return result


# ---------------------------------------------------------------------------
# POST /calificaciones/importar — confirma importación (D7, D8)
# ---------------------------------------------------------------------------

@router.post("/importar", response_model=List[CalificacionRead], status_code=status.HTTP_201_CREATED)
async def importar_calificaciones(
    body: ImportarCalificacionesRequest,
    _grant=Depends(require_permission("calificaciones:importar")),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> List[CalificacionRead]:
    """
    Persiste Calificacion records para las actividades seleccionadas.

    Linkea cada fila al padrón activo por email (D7).
    Deriva aprobado con el umbral efectivo de la asignación del importador (D3/D5).
    Re-importar la misma actividad hace upsert (no duplica) (D8).
    Emite auditoría CALIFICACIONES_IMPORTAR (D10).

    Retorna la lista de CalificacionRead creadas/actualizadas.
    La identidad del actor viene del JWT — nunca del body.
    """
    domain_user_id = await resolve_domain_user_id(current_user, db)
    svc = _make_cal_service(db, current_user.tenant_id)
    cals = await svc.importar(req=body, current_user=current_user, domain_user_id=domain_user_id)
    return cals


# ---------------------------------------------------------------------------
# POST /calificaciones/finalizacion — reporte de finalización (F1.2, RN-07/RN-08)
# ---------------------------------------------------------------------------

@router.post("/finalizacion", response_model=List[EntregaSinCorregir])
async def finalizacion_report(
    body: ReporteFinalizacionRequest,
    _grant=Depends(require_permission("calificaciones:importar")),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> List[EntregaSinCorregir]:
    """
    Cruza el reporte de finalización del LMS contra las calificaciones importadas.

    Detecta entregas textuales completadas sin nota registrada (RN-07).
    Excluye actividades de escala numérica (RN-08).

    Retorna lista de EntregaSinCorregir.
    La identidad del actor viene del JWT — nunca del body.
    """
    svc = _make_cal_service(db, current_user.tenant_id)
    return await svc.detectar_sin_corregir(req=body, current_user=current_user)


# ---------------------------------------------------------------------------
# PUT /calificaciones/umbral — configurar umbral de aprobación (D5)
# ---------------------------------------------------------------------------

@router.put("/umbral", response_model=UmbralMateriaRead)
async def configurar_umbral(
    body: ConfigurarUmbralRequest,
    _grant=Depends(require_permission("calificaciones:configurar-umbral")),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UmbralMateriaRead:
    """
    Configura el umbral de aprobación para la asignación del docente en una materia.

    La asignacion_id se resuelve desde current_user + materia_id (D5, regla dura #8/#14).
    Hace get-or-create upsert sobre UmbralMateria.

    Retorna el UmbralMateriaRead actualizado.
    Identidad del actor desde el JWT — nunca del body.
    """
    svc = _make_umbral_service(db, current_user.tenant_id)
    try:
        result = await svc.configurar(
            materia_id=body.materia_id,
            umbral_pct=body.umbral_pct,
            valores_aprobatorios=body.valores_aprobatorios,
            current_user=current_user,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        )
    return result


# ---------------------------------------------------------------------------
# GET /calificaciones/umbral — obtener umbral efectivo (D5)
# ---------------------------------------------------------------------------

@router.get("/umbral", response_model=UmbralMateriaRead)
async def get_umbral(
    materia_id: uuid.UUID = Query(...),
    _grant=Depends(require_permission("calificaciones:configurar-umbral")),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UmbralMateriaRead:
    """
    Retorna el umbral efectivo para la asignación del docente en una materia.

    Si no hay UmbralMateria configurado, retorna el defecto del sistema (60%).
    La asignacion_id se resuelve desde current_user + materia_id (D5, regla dura #8/#14).
    Identidad del actor desde el JWT — nunca del query param.
    """
    from sqlalchemy import select
    from app.models.usuario import Asignacion, Usuario

    # current_user.user_id = auth_identities.id (JWT sub).
    # Asignacion.usuario_id references usuario.id — resolve via Usuario join.
    stmt = (
        select(Asignacion)
        .join(Usuario, (Usuario.id == Asignacion.usuario_id) & (Usuario.deleted_at.is_(None)))
        .where(
            Asignacion.tenant_id == current_user.tenant_id,
            Usuario.auth_identity_id == current_user.user_id,
            Asignacion.materia_id == materia_id,
            Asignacion.deleted_at.is_(None),
        )
        .order_by(Asignacion.desde.desc())
        .limit(1)
    )
    result = await db.execute(stmt)
    asignacion = result.scalar_one_or_none()

    if asignacion is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No active asignacion found for user in materia {materia_id}",
        )

    svc = _make_umbral_service(db, current_user.tenant_id)
    return await svc.get_efectivo(
        asignacion_id=asignacion.id,
        materia_id=materia_id,
    )
