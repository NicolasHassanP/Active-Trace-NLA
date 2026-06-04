"""
Router encuentros — /api/v1/encuentros

C-13 Design Decisions D9:
    Un solo permiso 'encuentros:gestionar' para todo el módulo.
    Identidad del actor SIEMPRE desde el JWT — nunca de URL/body.

Endpoints:
    POST  /encuentros/slots                     — crear slot + instancias
    PATCH /encuentros/instancias/{instancia_id} — editar instancia individual
    GET   /encuentros/instancias                — listar (role-scoped: D11)
    GET   /encuentros/bloque-html               — HTML del aula virtual

snake_case; ≤500 LOC.
"""
import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import CurrentUser, get_current_user, get_db, require_permission
from app.repositories.audit_repository import AuditRepository
from app.repositories.encuentro_repository import (
    InstanciaEncuentroRepository,
    SlotEncuentroRepository,
)
from app.repositories.usuario_repository import AsignacionRepository
from app.schemas.encuentro import (
    BloqueHtmlResponse,
    CrearSlotRequest,
    CrearSlotResponse,
    EditarInstanciaRequest,
    InstanciaEncuentroRead,
)
from app.services.encuentro_html import generar_bloque_html
from app.services.encuentro_service import EncuentroService, EncuentroValidationError

router = APIRouter(prefix="/encuentros", tags=["encuentros"])


# ---------------------------------------------------------------------------
# Dependency helper
# ---------------------------------------------------------------------------

def _make_encuentro_service(db: AsyncSession, tenant_id: uuid.UUID) -> EncuentroService:
    return EncuentroService(
        slot_repo=SlotEncuentroRepository(session=db, tenant_id=tenant_id),
        instancia_repo=InstanciaEncuentroRepository(session=db, tenant_id=tenant_id),
        asignacion_repo=AsignacionRepository(session=db, tenant_id=tenant_id),
        audit_repo=AuditRepository(session=db, tenant_id=tenant_id),
    )


# ---------------------------------------------------------------------------
# POST /encuentros/slots — crear slot + instancias
# ---------------------------------------------------------------------------

@router.post(
    "/slots",
    response_model=CrearSlotResponse,
    status_code=status.HTTP_201_CREATED,
)
async def crear_slot(
    body: CrearSlotRequest,
    _grant=Depends(require_permission("encuentros:gestionar")),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CrearSlotResponse:
    """
    Crea un slot de encuentro (recurrente o único) y genera sus instancias.

    Identidad del actor desde el JWT — nunca del body.
    Requiere permiso encuentros:gestionar.
    """
    svc = _make_encuentro_service(db, current_user.tenant_id)
    try:
        return await svc.crear_slot(body, current_user)
    except EncuentroValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        )


# ---------------------------------------------------------------------------
# PATCH /encuentros/instancias/{instancia_id} — editar instancia
# ---------------------------------------------------------------------------

@router.patch(
    "/instancias/{instancia_id}",
    response_model=InstanciaEncuentroRead,
)
async def editar_instancia(
    instancia_id: uuid.UUID,
    body: EditarInstanciaRequest,
    _grant=Depends(require_permission("encuentros:gestionar")),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> InstanciaEncuentroRead:
    """
    Edita los campos mutables de una instancia de encuentro (RN-14).

    Solo modifica la instancia indicada; slots y hermanas no se tocan.
    Identidad desde el JWT.
    Requiere permiso encuentros:gestionar.
    """
    svc = _make_encuentro_service(db, current_user.tenant_id)
    return await svc.editar_instancia(instancia_id, body, current_user)


# ---------------------------------------------------------------------------
# GET /encuentros/instancias — listar instancias (role-scoped)
# ---------------------------------------------------------------------------

@router.get(
    "/instancias",
    response_model=List[InstanciaEncuentroRead],
)
async def listar_instancias(
    materia_id: Optional[uuid.UUID] = Query(None),
    _grant=Depends(require_permission("encuentros:gestionar")),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> List[InstanciaEncuentroRead]:
    """
    Lista instancias de encuentro.

    COORDINADOR/ADMIN: todas las instancias del tenant.
    PROFESOR/TUTOR: solo sus propias instancias (D11).

    Filtro opcional por materia_id.
    Identidad desde el JWT.
    Requiere permiso encuentros:gestionar.
    """
    svc = _make_encuentro_service(db, current_user.tenant_id)
    return await svc.listar_instancias(actor=current_user, materia_id=materia_id)


# ---------------------------------------------------------------------------
# GET /encuentros/bloque-html — HTML del aula virtual
# ---------------------------------------------------------------------------

@router.get(
    "/bloque-html",
    response_model=BloqueHtmlResponse,
)
async def bloque_html(
    materia_id: Optional[uuid.UUID] = Query(None),
    slot_id: Optional[uuid.UUID] = Query(None),
    _grant=Depends(require_permission("encuentros:gestionar")),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> BloqueHtmlResponse:
    """
    Genera el bloque HTML del aula virtual con las instancias indicadas.

    Filtra por materia_id y/o slot_id (opcionales).
    Si slot_id se provee, retorna solo las instancias de ese slot.
    D7: todos los valores son escapados con html.escape (anti-XSS).
    Requiere permiso encuentros:gestionar.
    """
    inst_repo = InstanciaEncuentroRepository(session=db, tenant_id=current_user.tenant_id)

    if slot_id is not None:
        instancias = await inst_repo.list_by_slot(slot_id)
    elif materia_id is not None:
        instancias = await inst_repo.list_by_materia(materia_id=materia_id)
    else:
        instancias = []

    html_content = generar_bloque_html(instancias)
    return BloqueHtmlResponse(html=html_content)
