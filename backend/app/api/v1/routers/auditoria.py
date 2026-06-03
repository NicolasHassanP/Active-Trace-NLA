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

Identity comes EXCLUSIVELY from the verified JWT (rule #8).
Never reads identity from URL params, body, or headers.
"""
import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import CurrentUser, get_current_user, get_db, require_permission
from app.core.request_context import extract_request_context
from app.models.audit import AuditAction, AuditResultado
from app.models.rbac import PermisoScope
from app.repositories.audit_repository import AuditRepository
from app.schemas.audit import AuditEventRead
from app.services.audit_service import AuditService
from app.services.authorization_service import PermissionGrant

router = APIRouter(prefix="/auditoria", tags=["auditoria"])


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

    return [AuditEventRead.model_validate(e) for e in events]
