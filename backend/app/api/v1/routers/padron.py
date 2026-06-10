"""
Router padrón — /api/v1/padron

C-09 Design Decision D5, D6, D7:
    Endpoints de importación y gestión del padrón versionado.

    tenant_id y user_id SIEMPRE desde el JWT (get_current_user), nunca del body.
    require_permission("padron:cargar") en todos los endpoints.
    require_permission("padron:gestionar") verificado inline para vaciar.

Endpoints:
    POST /padron/preview      — multipart file upload; retorna list[PadronRowDTO]
    POST /padron/activar      — JSON ActivarRequest; retorna VersionPadronRead
    DELETE /padron/vaciar     — query params materia_id, cohorte_id; 204
    POST /padron/sync-moodle  — JSON SyncMoodleRequest; retorna VersionPadronRead

snake_case; ≤500 LOC.
"""
import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import CurrentUser, get_current_user, get_db, require_permission, resolve_domain_user_id
from app.repositories.audit_repository import AuditRepository
from app.repositories.padron_repository import PadronRepository
from app.schemas.padron import (
    ActivarRequest,
    PadronRowDTO,
    SyncMoodleRequest,
    VersionPadronRead,
)
from app.services.padron_parser import PadronValidationError
from app.services.padron_service import PadronService

router = APIRouter(prefix="/padron", tags=["padron"])


# ---------------------------------------------------------------------------
# Dependency helpers
# ---------------------------------------------------------------------------

def _make_service(db: AsyncSession, tenant_id: uuid.UUID) -> PadronService:
    repo = PadronRepository(session=db, tenant_id=tenant_id)
    audit_repo = AuditRepository(session=db, tenant_id=tenant_id)
    return PadronService(repo=repo, db=db, audit_repo=audit_repo)


# ---------------------------------------------------------------------------
# POST /padron/preview — parse file, no DB write (D5)
# ---------------------------------------------------------------------------

@router.post("/preview", response_model=List[PadronRowDTO])
async def preview_padron(
    file: UploadFile = File(...),
    _grant=Depends(require_permission("padron:cargar")),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> List[PadronRowDTO]:
    """
    Parsea el archivo de padrón y retorna las filas detectadas sin escribir en DB.

    Acepta .xlsx y .csv.
    Retorna 422 si el archivo es inválido, tiene columnas faltantes o supera el límite.

    Identidad del actor desde el JWT — nunca del body o URL.
    """
    file_bytes = await file.read()
    filename = file.filename or "padron.xlsx"

    svc = _make_service(db, current_user.tenant_id)
    try:
        rows = await svc.preview(
            file_bytes=file_bytes,
            filename=filename,
            materia_id=uuid.uuid4(),  # Not used in preview — passed for interface compat
            cohorte_id=uuid.uuid4(),
            current_user=current_user,
        )
    except PadronValidationError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail)

    return rows


# ---------------------------------------------------------------------------
# POST /padron/activar — confirma importación (D5)
# ---------------------------------------------------------------------------

@router.post("/activar", response_model=VersionPadronRead, status_code=status.HTTP_201_CREATED)
async def activar_padron(
    body: ActivarRequest,
    _grant=Depends(require_permission("padron:cargar")),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> VersionPadronRead:
    """
    Confirma la importación del padrón: crea VersionPadron + EntradaPadron y activa.

    La versión anterior (si existe) queda inactiva automáticamente (D2).
    Emite auditoría PADRON_CARGAR.
    """
    domain_user_id = await resolve_domain_user_id(current_user, db)
    svc = _make_service(db, current_user.tenant_id)
    version = await svc.activar(
        rows=body.rows,
        materia_id=body.materia_id,
        cohorte_id=body.cohorte_id,
        current_user=current_user,
        domain_user_id=domain_user_id,
    )

    return VersionPadronRead(
        id=version.id,
        materia_id=version.materia_id,
        cohorte_id=version.cohorte_id,
        cargado_por=version.cargado_por,
        cargado_at=version.cargado_at,
        activa=version.activa,
        filas_total=len(body.rows),
    )


# ---------------------------------------------------------------------------
# DELETE /padron/vaciar — soft-delete versión activa (D6)
# ---------------------------------------------------------------------------

@router.delete("/vaciar", status_code=status.HTTP_204_NO_CONTENT)
async def vaciar_padron(
    materia_id: uuid.UUID = Query(...),
    cohorte_id: uuid.UUID = Query(...),
    _grant=Depends(require_permission("padron:cargar")),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """
    Vacía el padrón activo para una materia×cohorte (soft-delete).

    Scope-isolated (D6, RN-04):
        - PROFESOR (solo padron:cargar): solo puede vaciar versiones que cargó él mismo.
        - COORDINADOR/ADMIN (con padron:gestionar): puede vaciar cualquier versión del tenant.

    Retorna 204 si exitoso.
    Retorna 404 si no hay versión activa.
    Retorna 403 si el PROFESOR intenta vaciar versión de otro.
    """
    from app.repositories.rbac_repository import RbacRepository
    from app.services.authorization_service import AuthorizationService

    # Check if user has padron:gestionar (determines scope)
    rbac_repo = RbacRepository(session=db, tenant_id=current_user.tenant_id)
    auth_svc = AuthorizationService(repository=rbac_repo)
    grants = await auth_svc.resolve_effective_permissions(current_user)
    has_gestionar = any(g.codigo == "padron:gestionar" for g in grants)

    domain_user_id = await resolve_domain_user_id(current_user, db)
    svc = _make_service(db, current_user.tenant_id)
    await svc.vaciar(
        materia_id=materia_id,
        cohorte_id=cohorte_id,
        current_user=current_user,
        has_gestionar=has_gestionar,
        domain_user_id=domain_user_id,
    )


# ---------------------------------------------------------------------------
# POST /padron/sync-moodle — sync on-demand desde Moodle WS (D7)
# ---------------------------------------------------------------------------

@router.post("/sync-moodle", response_model=VersionPadronRead, status_code=status.HTTP_201_CREATED)
async def sync_moodle_padron(
    body: SyncMoodleRequest,
    _grant=Depends(require_permission("padron:cargar")),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> VersionPadronRead:
    """
    Sincroniza usuarios matriculados desde Moodle WS como nueva versión activa.

    Retorna 503 si MOODLE_BASE_URL/TOKEN no están configurados.
    Retorna 502 si Moodle WS no está disponible tras 2 intentos.
    """
    from app.core.config import Settings
    from app.integrations.moodle_ws import MoodleWSClient

    settings = Settings()

    if not settings.MOODLE_BASE_URL or not settings.MOODLE_TOKEN:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "La integración con Moodle no está configurada en este entorno. "
                "Defina MOODLE_BASE_URL y MOODLE_TOKEN para habilitar la sincronización."
            ),
        )

    moodle_client = MoodleWSClient(
        base_url=settings.MOODLE_BASE_URL,
        token=settings.MOODLE_TOKEN,
    )

    domain_user_id = await resolve_domain_user_id(current_user, db)
    svc = _make_service(db, current_user.tenant_id)
    version = await svc.sync_from_moodle(
        course_id=body.course_id,
        materia_id=body.materia_id,
        cohorte_id=body.cohorte_id,
        current_user=current_user,
        moodle_client=moodle_client,
        domain_user_id=domain_user_id,
    )

    # Count entries created
    from sqlalchemy import select, func
    from app.models.padron import EntradaPadron
    count_stmt = (
        select(func.count())
        .select_from(EntradaPadron)
        .where(
            EntradaPadron.version_id == version.id,
            EntradaPadron.deleted_at.is_(None),
        )
    )
    result = await db.execute(count_stmt)
    filas_total = result.scalar_one() or 0

    return VersionPadronRead(
        id=version.id,
        materia_id=version.materia_id,
        cohorte_id=version.cohorte_id,
        cargado_por=version.cargado_por,
        cargado_at=version.cargado_at,
        activa=version.activa,
        filas_total=filas_total,
    )
