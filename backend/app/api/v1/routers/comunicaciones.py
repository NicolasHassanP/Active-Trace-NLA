"""
Router comunicaciones — /api/v1/comunicaciones

C-12 Design Decisions:
    D1 — require_permission('comunicacion:enviar') en preview y encolar.
    D2 — require_permission('comunicacion:aprobar') en aprobar/cancelar de lote e individual.
    D3 — Identidad del actor SIEMPRE desde el JWT (get_current_user) — nunca del body.
    D4 — Factory de service sigue el patrón de calificaciones.py.
    D5 — Sin lógica de negocio en este router — todo delegado al service.

Endpoints:
    POST /comunicaciones/preview            — renderiza plantilla, 200 | 422
    POST /comunicaciones/encolar            — encola lote, 201
    POST /comunicaciones/aprobar-lote       — aprueba lote, 200
    POST /comunicaciones/cancelar-lote      — cancela lote, 200
    POST /comunicaciones/aprobar-individual — aprueba un mensaje, 200
    POST /comunicaciones/cancelar-individual — cancela un mensaje, 200
    GET  /comunicaciones/lote/{lote_id}     — estado del lote, 200

snake_case; ≤500 LOC.
"""
import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import CurrentUser, get_current_user, get_db, require_permission, resolve_domain_user_id
from app.repositories.audit_repository import AuditRepository
from app.repositories.comunicacion_repository import ComunicacionRepository
from app.repositories.tenant_config_repository import TenantConfigRepository
from app.schemas.comunicacion import (
    ComunicacionRead,
    EncolarRequest,
    EncolarResponse,
    IndividualRequest,
    LoteRequest,
    LoteStatusResponse,
    MisEnviosResponse,
    PendienteAprobacionItem,
    PendientesAprobacionResponse,
    PreviewRequest,
    PreviewResponse,
)
from app.services.comunicacion_plantilla import VariablePlantillaFaltanteError
from app.services.comunicacion_estados import TransicionInvalidaError
from app.services.comunicacion_service import ComunicacionService

router = APIRouter(prefix="/comunicaciones", tags=["comunicaciones"])


# ---------------------------------------------------------------------------
# Factory helper
# ---------------------------------------------------------------------------

def _make_service(db: AsyncSession, tenant_id: uuid.UUID) -> ComunicacionService:
    com_repo = ComunicacionRepository(session=db, tenant_id=tenant_id)
    tc_repo = TenantConfigRepository(session=db, tenant_id=tenant_id)
    audit_repo = AuditRepository(session=db, tenant_id=tenant_id)
    return ComunicacionService(repo=com_repo, tenant_config_repo=tc_repo, audit_repo=audit_repo)


def _to_read(com) -> ComunicacionRead:
    """Convert a Comunicacion ORM instance to ComunicacionRead schema."""
    return ComunicacionRead(
        id=com.id,
        tenant_id=com.tenant_id,
        estado=com.estado.value if hasattr(com.estado, "value") else str(com.estado),
        lote_id=com.lote_id,
        asunto=com.asunto,
        cuerpo=com.cuerpo,
        destinatario_email=com.destinatario,
        enviado_at=com.enviado_at,
        error_detalle=com.error_detalle,
        enviado_por=com.enviado_por,
        aprobado_por=com.aprobado_por,
        creado_en=com.created_at,
        actualizado_en=com.updated_at,
    )


# ---------------------------------------------------------------------------
# POST /comunicaciones/preview — renderiza sin DB (7.1)
# ---------------------------------------------------------------------------

@router.post("/preview", response_model=PreviewResponse)
async def preview_comunicacion(
    body: PreviewRequest,
    _grant=Depends(require_permission("comunicacion:enviar")),
    current_user: CurrentUser = Depends(get_current_user),
) -> PreviewResponse:
    """
    Renderiza asunto y cuerpo con las variables dadas — sin escribir en DB.

    Retorna 422 si alguna variable falta (OQ-4).
    La identidad del actor viene del JWT — nunca del body.
    """
    try:
        result = ComunicacionService.preview_static(
            asunto_plantilla=body.asunto_plantilla,
            cuerpo_plantilla=body.cuerpo_plantilla,
            variables=body.variables,
        )
    except VariablePlantillaFaltanteError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        )
    return PreviewResponse(asunto=result["asunto"], cuerpo=result["cuerpo"])


# ---------------------------------------------------------------------------
# POST /comunicaciones/encolar — encola lote (7.1, 7.2)
# ---------------------------------------------------------------------------

@router.post(
    "/encolar",
    response_model=EncolarResponse,
    status_code=status.HTTP_201_CREATED,
)
async def encolar_comunicaciones(
    body: EncolarRequest,
    _grant=Depends(require_permission("comunicacion:enviar")),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> EncolarResponse:
    """
    Encola un lote de comunicaciones (estado Pendiente).

    Falla fuerte si la plantilla tiene variable sin resolver (OQ-4).
    La identidad/tenant del remitente viene del JWT — nunca del body.
    Audita COMUNICACION_ENVIAR exactamente una vez.
    """
    domain_user_id = await resolve_domain_user_id(current_user, db)
    svc = _make_service(db, current_user.tenant_id)
    try:
        lote_id, coms = await svc.encolar(
            destinatarios=body.destinatarios,
            asunto_plantilla=body.asunto_plantilla,
            cuerpo_plantilla=body.cuerpo_plantilla,
            variables_por_destinatario=body.variables_por_destinatario,
            current_user=current_user,
            domain_user_id=domain_user_id,
        )
    except VariablePlantillaFaltanteError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        )
    return EncolarResponse(
        lote_id=lote_id,
        total_encolados=len(coms),
        mensajes=[_to_read(c) for c in coms],
    )


# ---------------------------------------------------------------------------
# POST /comunicaciones/aprobar-lote — aprueba lote (7.1)
# ---------------------------------------------------------------------------

@router.post("/aprobar-lote", response_model=List[ComunicacionRead])
async def aprobar_lote(
    body: LoteRequest,
    _grant=Depends(require_permission("comunicacion:aprobar")),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> List[ComunicacionRead]:
    """
    Aprueba todos los mensajes Pendiente del lote para despacho.

    La identidad del aprobador viene del JWT.
    """
    domain_user_id = await resolve_domain_user_id(current_user, db)
    svc = _make_service(db, current_user.tenant_id)
    actualizados = await svc.aprobar_lote(lote_id=body.lote_id, current_user=current_user, domain_user_id=domain_user_id)
    return [_to_read(c) for c in actualizados]


# ---------------------------------------------------------------------------
# POST /comunicaciones/cancelar-lote — cancela lote (7.1)
# ---------------------------------------------------------------------------

@router.post("/cancelar-lote", response_model=List[ComunicacionRead])
async def cancelar_lote(
    body: LoteRequest,
    _grant=Depends(require_permission("comunicacion:aprobar")),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> List[ComunicacionRead]:
    """
    Cancela todos los mensajes Pendiente del lote.

    Retorna 409 si algún mensaje está en estado no cancelable.
    """
    svc = _make_service(db, current_user.tenant_id)
    try:
        cancelados = await svc.cancelar_lote(lote_id=body.lote_id, current_user=current_user)
    except TransicionInvalidaError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        )
    return [_to_read(c) for c in cancelados]


# ---------------------------------------------------------------------------
# POST /comunicaciones/aprobar-individual — aprueba un mensaje (7.1)
# ---------------------------------------------------------------------------

@router.post("/aprobar-individual", response_model=ComunicacionRead)
async def aprobar_individual(
    body: IndividualRequest,
    _grant=Depends(require_permission("comunicacion:aprobar")),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ComunicacionRead:
    """
    Aprueba un mensaje específico para despacho.

    Retorna 404 si el mensaje no existe en el tenant del actor.
    """
    domain_user_id = await resolve_domain_user_id(current_user, db)
    svc = _make_service(db, current_user.tenant_id)
    try:
        com = await svc.aprobar_individual(
            comunicacion_id=body.comunicacion_id,
            current_user=current_user,
            domain_user_id=domain_user_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    return _to_read(com)


# ---------------------------------------------------------------------------
# POST /comunicaciones/cancelar-individual — cancela un mensaje (7.1)
# ---------------------------------------------------------------------------

@router.post("/cancelar-individual", response_model=ComunicacionRead)
async def cancelar_individual(
    body: IndividualRequest,
    _grant=Depends(require_permission("comunicacion:aprobar")),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ComunicacionRead:
    """
    Cancela un mensaje específico.

    Retorna 409 si el mensaje está en estado no cancelable (Enviado, Error).
    """
    svc = _make_service(db, current_user.tenant_id)
    try:
        com = await svc.cancelar_individual(
            comunicacion_id=body.comunicacion_id,
            current_user=current_user,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except TransicionInvalidaError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    return _to_read(com)


# ---------------------------------------------------------------------------
# GET /comunicaciones/lote/{lote_id} — estado del lote (7.1)
# ---------------------------------------------------------------------------

@router.get("/lote/{lote_id}", response_model=LoteStatusResponse)
async def get_lote(
    lote_id: uuid.UUID,
    _grant=Depends(require_permission("comunicacion:enviar")),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> LoteStatusResponse:
    """
    Retorna el estado actual de un lote de comunicaciones.

    Aislado por tenant: el usuario solo ve lotes de su propio tenant.
    """
    repo = ComunicacionRepository(session=db, tenant_id=current_user.tenant_id)
    mensajes = await repo.list_by_lote(lote_id)

    from app.models.comunicacion import ComunicacionEstado as ModelEstado
    return LoteStatusResponse(
        lote_id=lote_id,
        total=len(mensajes),
        pendientes=sum(1 for m in mensajes if m.estado == ModelEstado.Pendiente),
        enviados=sum(1 for m in mensajes if m.estado == ModelEstado.Enviado),
        fallidos=sum(1 for m in mensajes if m.estado == ModelEstado.Error),
        cancelados=sum(1 for m in mensajes if m.estado == ModelEstado.Cancelado),
        mensajes=[_to_read(m) for m in mensajes],
    )


# ---------------------------------------------------------------------------
# GET /comunicaciones/pendientes-aprobacion — lista paginada para aprobador
# ---------------------------------------------------------------------------

@router.get("/pendientes-aprobacion", response_model=PendientesAprobacionResponse)
async def get_pendientes_aprobacion(
    offset: int = Query(default=0, ge=0, description="Paginación: inicio"),
    limit: int = Query(default=50, ge=1, le=200, description="Paginación: cantidad máxima"),
    _grant=Depends(require_permission("comunicacion:aprobar")),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PendientesAprobacionResponse:
    """
    Retorna todos los mensajes en estado Pendiente del tenant, paginados.

    Destinado al aprobador para revisar y actuar sobre las comunicaciones
    que aguardan aprobación antes de ser despachadas.

    La identidad y tenant_id SIEMPRE vienen del JWT — nunca de body ni URL.
    Requiere permiso: comunicacion:aprobar (D2).
    Scoped al tenant del JWT (multi-tenancy automático en el repositorio).

    Query params:
        offset: default 0
        limit: default 50, max 200
    """
    svc = _make_service(db, current_user.tenant_id)
    items, total = await svc.listar_pendientes_aprobacion(offset=offset, limit=limit)
    return PendientesAprobacionResponse(
        items=items,
        total=total,
        offset=offset,
        limit=limit,
    )


# ---------------------------------------------------------------------------
# GET /comunicaciones/mis-envios — historial del remitente (C-27)
# ---------------------------------------------------------------------------

@router.get("/mis-envios", response_model=MisEnviosResponse)
async def get_mis_envios(
    estado: Optional[str] = Query(default=None, description="Filtro opcional por estado"),
    offset: int = Query(default=0, ge=0, description="Paginación: inicio"),
    limit: int = Query(default=20, ge=1, le=100, description="Paginación: cantidad máxima"),
    _grant=Depends(require_permission("comunicacion:enviar")),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MisEnviosResponse:
    """
    Retorna el historial de comunicaciones enviadas por el usuario autenticado.

    Identidad del remitente SIEMPRE desde el JWT (resolve_domain_user_id).
    Nunca acepta un sender_id como query param.

    Requiere permiso: comunicacion:enviar (D6 — reutiliza el mismo permiso que encolar).
    Scoped al tenant del JWT (multi-tenancy automático en el repositorio).

    Query params opcionales:
        estado: uno de Pendiente|Enviando|Enviado|Error|Cancelado
        offset: default 0
        limit: default 20, max 100
    """
    from app.models.comunicacion import ComunicacionEstado as ModelEstado

    # D3 — identidad del remitente SIEMPRE desde el JWT
    domain_user_id = await resolve_domain_user_id(current_user, db)

    # Parsear estado si se proveyó
    estado_enum: Optional[ModelEstado] = None
    if estado is not None:
        try:
            estado_enum = ModelEstado(estado)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Estado inválido: '{estado}'. Valores permitidos: Pendiente, Enviando, Enviado, Error, Cancelado.",
            )

    repo = ComunicacionRepository(session=db, tenant_id=current_user.tenant_id)
    items, total = await repo.list_by_sender(
        sender_id=domain_user_id,
        estado=estado_enum,
        offset=offset,
        limit=limit,
    )

    return MisEnviosResponse(
        total=total,
        offset=offset,
        limit=limit,
        items=[_to_read(m) for m in items],
    )
