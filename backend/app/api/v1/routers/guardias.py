"""
Router guardias — /api/v1/guardias

C-13 Design:
    Permiso único 'encuentros:gestionar'.
    Identidad SIEMPRE desde el JWT — nunca del body/URL (regla dura #8/#14).

Endpoints:
    POST /guardias         — registrar guardia
    GET  /guardias         — listar guardias (role-scoped)
    GET  /guardias/export  — CSV export

snake_case; ≤500 LOC.
"""
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import CurrentUser, get_current_user, get_db, require_permission, resolve_domain_user_id
from app.repositories.audit_repository import AuditRepository
from app.repositories.guardia_repository import GuardiaRepository
from app.repositories.usuario_repository import AsignacionRepository
from app.schemas.guardia import GuardiaFiltros, GuardiaRead, RegistrarGuardiaRequest
from app.services.guardia_service import GuardiaService

router = APIRouter(prefix="/guardias", tags=["guardias"])


# ---------------------------------------------------------------------------
# Dependency helper
# ---------------------------------------------------------------------------

def _make_guardia_service(db: AsyncSession, tenant_id: uuid.UUID) -> GuardiaService:
    return GuardiaService(
        guardia_repo=GuardiaRepository(session=db, tenant_id=tenant_id),
        asignacion_repo=AsignacionRepository(session=db, tenant_id=tenant_id),
        audit_repo=AuditRepository(session=db, tenant_id=tenant_id),
    )


# ---------------------------------------------------------------------------
# POST /guardias — registrar guardia
# ---------------------------------------------------------------------------

@router.post(
    "",
    response_model=GuardiaRead,
    status_code=status.HTTP_201_CREATED,
)
async def registrar_guardia(
    body: RegistrarGuardiaRequest,
    _grant=Depends(require_permission("encuentros:gestionar")),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> GuardiaRead:
    """
    Registra una guardia de atención.

    asignacion_id resuelto desde el JWT (current_user) — nunca del body.
    Requiere permiso encuentros:gestionar.
    """
    domain_user_id = await resolve_domain_user_id(current_user, db)
    svc = _make_guardia_service(db, current_user.tenant_id)
    return await svc.registrar(body, current_user, domain_user_id)


# ---------------------------------------------------------------------------
# GET /guardias/export — CSV adjunto (debe ir antes de GET /guardias)
# ---------------------------------------------------------------------------

@router.get("/export")
async def exportar_guardias(
    materia_id: Optional[uuid.UUID] = Query(None),
    carrera_id: Optional[uuid.UUID] = Query(None),
    cohorte_id: Optional[uuid.UUID] = Query(None),
    dia: Optional[str] = Query(None),
    estado: Optional[str] = Query(None),
    _grant=Depends(require_permission("encuentros:gestionar")),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Response:
    """
    Exporta guardias filtradas como CSV adjunto.

    COORDINADOR/ADMIN: todas las guardias del tenant.
    TUTOR/PROFESOR: solo las propias.
    Requiere permiso encuentros:gestionar.
    """
    from app.models.encuentro import DiaSemana, GuardiaEstado

    dia_enum = None
    if dia is not None:
        try:
            dia_enum = DiaSemana(dia)
        except ValueError:
            from fastapi import HTTPException
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Día inválido: {dia}",
            )

    estado_enum = None
    if estado is not None:
        try:
            estado_enum = GuardiaEstado(estado)
        except ValueError:
            from fastapi import HTTPException
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Estado inválido: {estado}",
            )

    filtros = GuardiaFiltros(
        materia_id=materia_id,
        carrera_id=carrera_id,
        cohorte_id=cohorte_id,
        dia=dia_enum,
        estado=estado_enum,
    )
    domain_user_id = await resolve_domain_user_id(current_user, db)
    svc = _make_guardia_service(db, current_user.tenant_id)
    csv_content = await svc.exportar(filtros, current_user, domain_user_id)

    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=guardias.csv"},
    )


# ---------------------------------------------------------------------------
# GET /guardias — listar guardias
# ---------------------------------------------------------------------------

@router.get("", response_model=list[GuardiaRead])
async def listar_guardias(
    materia_id: Optional[uuid.UUID] = Query(None),
    carrera_id: Optional[uuid.UUID] = Query(None),
    cohorte_id: Optional[uuid.UUID] = Query(None),
    dia: Optional[str] = Query(None),
    estado: Optional[str] = Query(None),
    _grant=Depends(require_permission("encuentros:gestionar")),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[GuardiaRead]:
    """
    Lista guardias de atención.

    COORDINADOR/ADMIN: todas las guardias del tenant.
    TUTOR/PROFESOR: solo las propias.
    Filtros opcionales: materia_id, carrera_id, cohorte_id, dia, estado.
    Requiere permiso encuentros:gestionar.
    """
    from app.models.encuentro import DiaSemana, GuardiaEstado

    dia_enum = None
    if dia is not None:
        try:
            dia_enum = DiaSemana(dia)
        except ValueError:
            from fastapi import HTTPException
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Día inválido: {dia}",
            )

    estado_enum = None
    if estado is not None:
        try:
            estado_enum = GuardiaEstado(estado)
        except ValueError:
            from fastapi import HTTPException
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Estado inválido: {estado}",
            )

    filtros = GuardiaFiltros(
        materia_id=materia_id,
        carrera_id=carrera_id,
        cohorte_id=cohorte_id,
        dia=dia_enum,
        estado=estado_enum,
    )
    domain_user_id = await resolve_domain_user_id(current_user, db)
    svc = _make_guardia_service(db, current_user.tenant_id)
    return await svc.consultar(filtros, current_user, domain_user_id)
