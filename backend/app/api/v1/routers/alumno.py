"""
Router alumno-portal — /api/v1/alumno

C-25: Endpoint de estado académico propio para el rol ALUMNO.
D1 — Identidad SIEMPRE del JWT (CurrentUser); sin params de identidad en URL/body.
D5 — Un solo endpoint agregador GET /alumno/estado-academico.

Endpoints:
    GET /alumno/estado-academico  — devuelve el estado académico del alumno autenticado.

Mapeo de permisos:
    academico:ver_propio  → requerido (fail-closed → 403).

Flujo: Router → AlumnoService → AlumnoRepository → models.
Sin lógica de negocio en el router (regla dura #11).
snake_case; ≤500 LOC.
"""
import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import CurrentUser, get_current_user, get_db, require_permission, resolve_domain_user_id
from app.repositories.alumno_repository import AlumnoRepository
from app.schemas.alumno import EstadoAcademicoRead
from app.services.alumno_service import AlumnoService

router = APIRouter(prefix="/alumno", tags=["alumno"])


# ---------------------------------------------------------------------------
# Dependency helper
# ---------------------------------------------------------------------------

def _make_service(db: AsyncSession, tenant_id: uuid.UUID) -> AlumnoService:
    repo = AlumnoRepository(session=db, tenant_id=tenant_id)
    return AlumnoService(repo=repo)


# ---------------------------------------------------------------------------
# GET /alumno/estado-academico
# ---------------------------------------------------------------------------

@router.get(
    "/estado-academico",
    response_model=EstadoAcademicoRead,
    summary="Estado académico del alumno autenticado",
)
async def get_estado_academico(
    _grant=Depends(require_permission("academico:ver_propio")),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> EstadoAcademicoRead:
    """Retorna el estado académico agregado del alumno: avance, materias y coloquios."""
    domain_user_id = await resolve_domain_user_id(current_user, db)
    service = _make_service(db, current_user.tenant_id)
    return await service.get_estado_academico(current_user, domain_user_id)
