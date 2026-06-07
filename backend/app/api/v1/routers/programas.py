"""
Router programas — /api/v1/programas

C-17 Design Decisions D9:
    Permiso 'estructura:gestionar' para todo el módulo.
    Identidad del actor SIEMPRE desde el JWT — nunca de URL/body.

Endpoints:
    POST   /programas             — registrar referencia de programa
    GET    /programas             — listar programas activos (filtrable)
    GET    /programas/{id}        — obtener programa por id
    DELETE /programas/{id}        — baja lógica

snake_case; ≤500 LOC.
"""
import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import CurrentUser, get_current_user, get_db, require_permission
from app.repositories.audit_repository import AuditRepository
from app.repositories.programa_repository import ProgramaMateriaRepository
from app.schemas.academico import ProgramaCreate, ProgramaRead
from app.services.programa_service import (
    ProgramaConflictError,
    ProgramaNotFoundError,
    ProgramaService,
)

router = APIRouter(prefix="/programas", tags=["programas"])


# ---------------------------------------------------------------------------
# Dependency helper
# ---------------------------------------------------------------------------

def _make_programa_service(db: AsyncSession, tenant_id: uuid.UUID) -> ProgramaService:
    return ProgramaService(
        programa_repo=ProgramaMateriaRepository(session=db, tenant_id=tenant_id),
        audit_repo=AuditRepository(session=db, tenant_id=tenant_id),
    )


# ---------------------------------------------------------------------------
# POST /programas — registrar programa
# ---------------------------------------------------------------------------

@router.post(
    "",
    response_model=ProgramaRead,
    status_code=status.HTTP_201_CREATED,
)
async def crear_programa(
    body: ProgramaCreate,
    _grant=Depends(require_permission("programas:gestionar")),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ProgramaRead:
    """
    Registrar un programa de materia con referencia de archivo.

    Requiere permiso estructura:gestionar.
    Identidad del actor desde el JWT.
    Devuelve 409 si ya existe un programa activo para la misma combinación.
    """
    svc = _make_programa_service(db, current_user.tenant_id)
    try:
        return await svc.crear(body, current_user)
    except ProgramaConflictError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        )


# ---------------------------------------------------------------------------
# GET /programas — listar programas
# ---------------------------------------------------------------------------

@router.get(
    "",
    response_model=List[ProgramaRead],
)
async def listar_programas(
    materia_id: Optional[uuid.UUID] = Query(None),
    carrera_id: Optional[uuid.UUID] = Query(None),
    cohorte_id: Optional[uuid.UUID] = Query(None),
    _grant=Depends(require_permission("programas:gestionar")),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> List[ProgramaRead]:
    """
    Listar programas activos del tenant, filtrables por materia, carrera y cohorte.

    Requiere permiso estructura:gestionar.
    """
    svc = _make_programa_service(db, current_user.tenant_id)
    return await svc.listar(
        materia_id=materia_id,
        carrera_id=carrera_id,
        cohorte_id=cohorte_id,
    )


# ---------------------------------------------------------------------------
# GET /programas/{programa_id} — obtener por id
# ---------------------------------------------------------------------------

@router.get(
    "/{programa_id}",
    response_model=ProgramaRead,
)
async def obtener_programa(
    programa_id: uuid.UUID,
    _grant=Depends(require_permission("programas:gestionar")),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ProgramaRead:
    """
    Obtener un programa de materia por id.

    Requiere permiso estructura:gestionar.
    Devuelve 404 si no existe o pertenece a otro tenant.
    """
    svc = _make_programa_service(db, current_user.tenant_id)
    try:
        return await svc.obtener(programa_id)
    except ProgramaNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )


# ---------------------------------------------------------------------------
# DELETE /programas/{programa_id} — baja lógica
# ---------------------------------------------------------------------------

@router.delete(
    "/{programa_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def eliminar_programa(
    programa_id: uuid.UUID,
    _grant=Depends(require_permission("programas:gestionar")),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """
    Dar de baja (soft delete) un programa de materia.

    Requiere permiso estructura:gestionar.
    Devuelve 404 si no existe o pertenece a otro tenant.
    Registra auditoría PROGRAMA_GESTIONAR.
    """
    svc = _make_programa_service(db, current_user.tenant_id)
    try:
        await svc.eliminar(programa_id, current_user)
    except ProgramaNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )
