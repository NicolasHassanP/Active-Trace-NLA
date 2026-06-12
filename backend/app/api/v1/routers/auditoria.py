"""
Auditoria router — read-only endpoint for audit events.

C-05: Design decision D8.

    GET /api/v1/auditoria
        - Protected by require_permission("auditoria:ver").
        - scope=propio  → only events whose actor_user_id = current user.
        - scope=global  → all events of the tenant.
        - Paginado via limit/offset query params.
        - Response: list of AuditEventRead (Pydantic v2, extra='forbid').
        - Registers AUDITORIA_CONSULTA event on every call (OQ-2 resolved).

C-19: panel metrics endpoints.
    GET /api/v1/auditoria/metricas/acciones-por-dia
    GET /api/v1/auditoria/metricas/interacciones-docente
    GET /api/v1/auditoria/metricas/interacciones-docente-materia
    GET /api/v1/auditoria/metricas/comunicaciones-por-docente
    GET /api/v1/auditoria/ultimas-acciones
        - All protected by require_permission("auditoria:ver").
        - scope=propio / global applied to ALL views (D3).
        - NO AUDITORIA_CONSULTA registered (D6).

Enrichment (display names):
    actor_nombre: resolved via UsuarioRepository.get_nombres_por_auth_identity_ids.
        actor_user_id IS the auth_identity.id (JWT sub), NOT usuario.id.
        One SELECT IN per endpoint batch, never per-row.
    entidad_nombre: resolved via MateriaRepository / CarreraRepository /
        CohorteRepository.get_nombres_por_ids for the supported entity types.
        One SELECT IN per entity type per batch.

Identity comes EXCLUSIVELY from the verified JWT (rule #8).
Never reads identity from URL params, body, or headers.
"""
import uuid
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.dependencies import CurrentUser, get_current_user, get_db, require_permission
from app.core.request_context import extract_request_context
from app.models.audit import AuditAction, AuditResultado
from app.models.comunicacion import ComunicacionEstado
from app.models.rbac import PermisoScope
from app.repositories.audit_metrics_repository import AuditMetricsRepository
from app.repositories.audit_repository import AuditRepository
from app.repositories.estructura_repository import (
    CarreraRepository,
    CohorteRepository,
    MateriaRepository,
)
from app.repositories.usuario_repository import UsuarioRepository
from app.schemas.audit import AuditEventRead
from app.schemas.auditoria_metricas import (
    AccionesPorDiaItem,
    AccionesPorDiaResponse,
    ComunicacionesPorDocenteItem,
    ComunicacionesPorDocenteResponse,
    InteraccionesDocenteItem,
    InteraccionesDocenteMateriaItem,
    InteraccionesDocenteMateriaResponse,
    InteraccionesDocenteResponse,
    UltimaAccionItem,
)
from app.services.audit_service import AuditService
from app.services.auditoria_panel_service import AuditoriaPanelService
from app.services.authorization_service import PermissionGrant

router = APIRouter(prefix="/auditoria", tags=["auditoria"])


# ---------------------------------------------------------------------------
# Enrichment helpers — pure functions, one SELECT IN per call.
# All queries go through repositories (rule #11).
# ---------------------------------------------------------------------------

async def _resolve_actor_nombres(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    actor_ids: List[uuid.UUID],
) -> Dict[uuid.UUID, str]:
    """
    Batch-resolve actor display names by auth_identity_id.

    actor_user_id in AuditEvent = JWT sub = auth_identity.id, NOT usuario.id.
    One SELECT IN, scoped to tenant. Returns {auth_identity_id: "Nombre Apellidos"}.
    Missing actors (orphan identities) are absent from the dict.
    """
    if not actor_ids:
        return {}
    repo = UsuarioRepository(session=db, tenant_id=tenant_id)
    return await repo.get_nombres_por_auth_identity_ids(list(set(actor_ids)))


async def _resolve_entidad_nombres(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    entidad_tipo: str,
    entidad_ids: List[str],
) -> Dict[str, str]:
    """
    Batch-resolve entity display names for supported entity types.

    Supported: Materia, Carrera, Cohorte.
    Returns {entidad_id_str: nombre}. Empty dict for unsupported types.
    One SELECT IN per call, scoped to tenant.
    """
    if not entidad_ids:
        return {}

    # Parse UUIDs — skip malformed ones
    valid_ids: List[uuid.UUID] = []
    for eid in entidad_ids:
        try:
            valid_ids.append(uuid.UUID(eid))
        except (ValueError, AttributeError):
            pass

    if not valid_ids:
        return {}

    if entidad_tipo == "Materia":
        repo = MateriaRepository(session=db, tenant_id=tenant_id)
        result = await repo.get_nombres_por_ids(valid_ids)
    elif entidad_tipo == "Carrera":
        repo = CarreraRepository(session=db, tenant_id=tenant_id)
        result = await repo.get_nombres_por_ids(valid_ids)
    elif entidad_tipo == "Cohorte":
        repo = CohorteRepository(session=db, tenant_id=tenant_id)
        result = await repo.get_nombres_por_ids(valid_ids)
    else:
        return {}

    # Convert UUID keys back to str for uniform lookup by callers
    return {str(k): v for k, v in result.items()}


async def _resolve_mixed_entidad_nombres(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    tipo_id_pairs: List[tuple[str, Optional[str]]],
) -> Dict[tuple[str, str], str]:
    """
    Batch-resolve entity names for a mixed list of (entidad_tipo, entidad_id) pairs.

    Groups by tipo and emits one SELECT IN per supported type.
    Returns {(entidad_tipo, entidad_id_str): nombre}.
    """
    from collections import defaultdict

    by_tipo: dict[str, list[str]] = defaultdict(list)
    for tipo, eid in tipo_id_pairs:
        if eid and tipo in ("Materia", "Carrera", "Cohorte"):
            by_tipo[tipo].append(eid)

    result: Dict[tuple[str, str], str] = {}
    for tipo, ids in by_tipo.items():
        nombres = await _resolve_entidad_nombres(db, tenant_id, tipo, ids)
        for eid, nombre in nombres.items():
            result[(tipo, eid)] = nombre

    return result


# ---------------------------------------------------------------------------
# GET /auditoria — list audit events (scoped by permission grant)
# ---------------------------------------------------------------------------

@router.get("", response_model=List[AuditEventRead])
async def list_audit_events(
    request: Request,
    grant: PermissionGrant = Depends(require_permission("auditoria:ver")),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> List[AuditEventRead]:
    """
    List audit events for the current tenant.

    Scope resolution (D8):
        - PermisoScope.propio  → only events for this user (actor_user_id filter).
        - PermisoScope.global_ → all tenant events.

    Always records a AUDITORIA_CONSULTA event (OQ-2: no blind spots).
    """
    repo = AuditRepository(session=db, tenant_id=current_user.tenant_id)
    svc = AuditService(repository=repo)

    # Determine row-level filter from permission scope (D8)
    actor_filter: Optional[uuid.UUID] = None
    if grant.scope == PermisoScope.propio:
        actor_filter = current_user.user_id

    events = await repo.list(
        actor_user_id=actor_filter,
        limit=limit,
        offset=offset,
    )

    # Extract request context (IP and user-agent — informative, not identity)
    ctx = extract_request_context(request)

    # Record the audit query itself (OQ-2 resolved: always register)
    await svc.record(
        actor=current_user,
        action=AuditAction.AUDITORIA_CONSULTA,
        modulo="auditoria",
        entidad_tipo="AuditEvent",
        resultado=AuditResultado.ok,
        registros_afectados=len(events),
        ip=ctx.ip,
        user_agent=ctx.user_agent,
    )

    # Batch-resolve display names (one SELECT IN per dimension)
    actor_nombres = await _resolve_actor_nombres(
        db, current_user.tenant_id,
        [e.actor_user_id for e in events],
    )
    entidad_nombres = await _resolve_mixed_entidad_nombres(
        db, current_user.tenant_id,
        [(e.entidad_tipo, e.entidad_id) for e in events],
    )

    enriched = []
    for e in events:
        item = AuditEventRead.model_validate(e)
        item.actor_nombre = actor_nombres.get(e.actor_user_id)
        item.entidad_nombre = entidad_nombres.get((e.entidad_tipo, e.entidad_id))
        enriched.append(item)

    return enriched


# ---------------------------------------------------------------------------
# C-19: Metrics endpoints (D6: no AUDITORIA_CONSULTA registration)
# ---------------------------------------------------------------------------

def _panel_service(db: AsyncSession, current_user: CurrentUser) -> AuditoriaPanelService:
    """Build AuditoriaPanelService with the correct tenant scope."""
    settings = Settings()
    repo = AuditMetricsRepository(session=db, tenant_id=current_user.tenant_id)
    return AuditoriaPanelService(repository=repo, settings=settings)


# --- 5.1 --- acciones-por-dia -----------------------------------------------

@router.get("/metricas/acciones-por-dia", response_model=AccionesPorDiaResponse)
async def get_acciones_por_dia(
    grant: PermissionGrant = Depends(require_permission("auditoria:ver")),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    desde: Optional[str] = Query(default=None, description="ISO date lower bound (YYYY-MM-DD)"),
    hasta: Optional[str] = Query(default=None, description="ISO date upper bound (YYYY-MM-DD)"),
    materia_id: Optional[str] = Query(default=None),
    actor_user_id: Optional[uuid.UUID] = Query(default=None),
) -> AccionesPorDiaResponse:
    """
    GET /api/v1/auditoria/metricas/acciones-por-dia

    Time series of actions grouped by calendar day (D5).
    Scope propio restricts to current user's events (D3). No auto-audit (D6).
    """
    from datetime import datetime, timezone
    svc = _panel_service(db, current_user)

    # Resolve optional actor override (only respected on global scope)
    effective_grant = grant
    if grant.scope == PermisoScope.propio:
        actor_user_id = None  # scope overrides any query param actor filter

    desde_dt = datetime.fromisoformat(desde).replace(tzinfo=timezone.utc) if desde else None
    hasta_dt = datetime.fromisoformat(hasta).replace(tzinfo=timezone.utc) if hasta else None

    rows = await svc.acciones_por_dia(
        current_user=current_user,
        grant=grant,
        desde=desde_dt,
        hasta=hasta_dt,
        materia_id=materia_id,
    )
    items = [AccionesPorDiaItem(dia=r.dia, total=r.total) for r in rows]
    return AccionesPorDiaResponse(items=items)


# --- 5.2 --- interacciones-docente ------------------------------------------

@router.get("/metricas/interacciones-docente", response_model=InteraccionesDocenteResponse)
async def get_interacciones_docente(
    grant: PermissionGrant = Depends(require_permission("auditoria:ver")),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    actor_user_id: Optional[uuid.UUID] = Query(default=None),
    desde: Optional[str] = Query(default=None),
    hasta: Optional[str] = Query(default=None),
) -> InteraccionesDocenteResponse:
    """GET /api/v1/auditoria/metricas/interacciones-docente (D5, D6)."""
    from datetime import datetime, timezone
    svc = _panel_service(db, current_user)

    desde_dt = datetime.fromisoformat(desde).replace(tzinfo=timezone.utc) if desde else None
    hasta_dt = datetime.fromisoformat(hasta).replace(tzinfo=timezone.utc) if hasta else None

    rows = await svc.interacciones_docente(
        current_user=current_user,
        grant=grant,
        actor_user_id=actor_user_id,
        desde=desde_dt,
        hasta=hasta_dt,
    )

    actor_nombres = await _resolve_actor_nombres(
        db, current_user.tenant_id,
        [r.actor_user_id for r in rows],
    )
    items = [
        InteraccionesDocenteItem(
            actor_user_id=r.actor_user_id,
            accion=r.accion,
            total=r.total,
            actor_nombre=actor_nombres.get(r.actor_user_id),
        )
        for r in rows
    ]
    return InteraccionesDocenteResponse(items=items)


# --- 5.3 --- interacciones-docente-materia ----------------------------------

@router.get("/metricas/interacciones-docente-materia", response_model=InteraccionesDocenteMateriaResponse)
async def get_interacciones_docente_materia(
    grant: PermissionGrant = Depends(require_permission("auditoria:ver")),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    actor_user_id: Optional[uuid.UUID] = Query(default=None),
    materia_id: Optional[str] = Query(default=None),
    desde: Optional[str] = Query(default=None),
    hasta: Optional[str] = Query(default=None),
) -> InteraccionesDocenteMateriaResponse:
    """GET /api/v1/auditoria/metricas/interacciones-docente-materia (D1, D5, D6)."""
    from datetime import datetime, timezone
    svc = _panel_service(db, current_user)

    desde_dt = datetime.fromisoformat(desde).replace(tzinfo=timezone.utc) if desde else None
    hasta_dt = datetime.fromisoformat(hasta).replace(tzinfo=timezone.utc) if hasta else None

    rows = await svc.interacciones_docente_materia(
        current_user=current_user,
        grant=grant,
        actor_user_id=actor_user_id,
        materia_id=materia_id,
        desde=desde_dt,
        hasta=hasta_dt,
    )

    actor_nombres = await _resolve_actor_nombres(
        db, current_user.tenant_id,
        [r.actor_user_id for r in rows],
    )
    # Resolve materia names: filter rows where materia_id is set
    materia_ids_str = [r.materia_id for r in rows if r.materia_id]
    materia_nombres_map = await _resolve_entidad_nombres(
        db, current_user.tenant_id, "Materia", materia_ids_str,
    )
    items = [
        InteraccionesDocenteMateriaItem(
            actor_user_id=r.actor_user_id,
            materia_id=r.materia_id,
            total=r.total,
            actor_nombre=actor_nombres.get(r.actor_user_id),
            materia_nombre=materia_nombres_map.get(r.materia_id) if r.materia_id else None,
        )
        for r in rows
    ]
    return InteraccionesDocenteMateriaResponse(items=items)


# --- 5.4 --- comunicaciones-por-docente -------------------------------------

@router.get("/metricas/comunicaciones-por-docente", response_model=ComunicacionesPorDocenteResponse)
async def get_comunicaciones_por_docente(
    grant: PermissionGrant = Depends(require_permission("auditoria:ver")),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    estado: Optional[ComunicacionEstado] = Query(default=None),
) -> ComunicacionesPorDocenteResponse:
    """GET /api/v1/auditoria/metricas/comunicaciones-por-docente (D2, D5, D6)."""
    svc = _panel_service(db, current_user)
    rows = await svc.comunicaciones_por_docente(
        current_user=current_user,
        grant=grant,
        estado=estado,
    )
    items = [
        ComunicacionesPorDocenteItem(
            enviado_por=r.enviado_por, estado=r.estado, total=r.total
        )
        for r in rows
    ]
    return ComunicacionesPorDocenteResponse(items=items)


# --- 5.5 --- ultimas-acciones -----------------------------------------------

@router.get("/ultimas-acciones", response_model=List[UltimaAccionItem])
async def get_ultimas_acciones(
    grant: PermissionGrant = Depends(require_permission("auditoria:ver")),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    limite: Optional[int] = Query(default=None, ge=1, description="Max records; default AUDIT_PANEL_LOG_MAX"),
    actor_user_id: Optional[uuid.UUID] = Query(default=None),
    desde: Optional[str] = Query(default=None),
    hasta: Optional[str] = Query(default=None),
    materia_id: Optional[str] = Query(default=None),
) -> List[UltimaAccionItem]:
    """
    GET /api/v1/auditoria/ultimas-acciones

    Returns the most recent audit events. limite is validated against
    AUDIT_PANEL_LOG_MAX (D4). No auto-audit (D6).
    """
    from datetime import datetime, timezone
    svc = _panel_service(db, current_user)

    desde_dt = datetime.fromisoformat(desde).replace(tzinfo=timezone.utc) if desde else None
    hasta_dt = datetime.fromisoformat(hasta).replace(tzinfo=timezone.utc) if hasta else None

    try:
        events = await svc.ultimas_acciones(
            current_user=current_user,
            grant=grant,
            limite=limite,
            actor_user_id=actor_user_id,
            desde=desde_dt,
            hasta=hasta_dt,
            materia_id=materia_id,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    # Batch-resolve display names
    actor_nombres = await _resolve_actor_nombres(
        db, current_user.tenant_id,
        [e.actor_user_id for e in events],
    )
    entidad_nombres = await _resolve_mixed_entidad_nombres(
        db, current_user.tenant_id,
        [(e.entidad_tipo, e.entidad_id) for e in events],
    )

    enriched = []
    for e in events:
        item = UltimaAccionItem.model_validate(e)
        item.actor_nombre = actor_nombres.get(e.actor_user_id)
        item.entidad_nombre = entidad_nombres.get((e.entidad_tipo, e.entidad_id))
        enriched.append(item)

    return enriched
