"""
AuditoriaPanelService — orchestrates audit panel aggregations (C-19).

Design decisions:
    D3 — scope propio/global translates to actor_filter (UUID | None),
         applied to ALL views (not only the log).
    D4 — limite validation: default=AUDIT_PANEL_LOG_MAX, reject >max or <1.
    D5 — no SQL here; all queries delegated to AuditMetricsRepository.
    D6 — this service does NOT emit AUDITORIA_CONSULTA events. The
         endpoints use require_permission but do not record audit events
         for panel queries (panel endpoints may be polled frequently).

Clean Architecture rule: this service holds a repository reference,
NOT an AsyncSession. No direct DB access.

≤500 LOC; snake_case.
"""
import uuid
from datetime import datetime
from typing import List, Optional

from app.core.dependencies import CurrentUser
from app.models.comunicacion import ComunicacionEstado
from app.models.rbac import PermisoScope
from app.repositories.audit_metrics_repository import (
    AccionesPorDiaRow,
    AuditMetricsRepository,
    ComunicacionesDocenteRow,
    InteraccionesDocenteMateriaRow,
    InteraccionesDocenteRow,
)
from app.services.authorization_service import PermissionGrant


class AuditoriaPanelService:
    """
    Orchestrates read-only audit panel views.

    Translates the PermissionGrant scope (propio/global) into an
    actor_filter: Optional[UUID] that is threaded through all repository
    calls (D3). Validates the limite parameter for the log endpoint (D4).

    Usage::

        repo = AuditMetricsRepository(session=db, tenant_id=current_user.tenant_id)
        svc = AuditoriaPanelService(repository=repo, settings=settings)
        rows = await svc.acciones_por_dia(current_user=user, grant=grant)
    """

    def __init__(
        self,
        repository: AuditMetricsRepository,
        settings,  # app.core.config.Settings (any object with AUDIT_PANEL_LOG_MAX)
    ) -> None:
        self._repo = repository
        self._settings = settings

    # ------------------------------------------------------------------
    # Internal helpers (pure functions — no DB access)
    # ------------------------------------------------------------------

    def _resolve_actor_filter(
        self, current_user: CurrentUser, grant: PermissionGrant
    ) -> Optional[uuid.UUID]:
        """
        Translate scope to a row-level actor filter (D3).

        PermisoScope.propio  → filter to current_user.user_id
        PermisoScope.global_ → no filter (returns None)
        """
        if grant.scope == PermisoScope.propio:
            return current_user.user_id
        return None

    def _validate_limite(self, limite: Optional[int]) -> int:
        """
        Validate and resolve the limite parameter (D4).

        None    → AUDIT_PANEL_LOG_MAX (default)
        1..max  → passed through as-is
        >max    → ValueError
        <1      → ValueError
        """
        max_val = self._settings.AUDIT_PANEL_LOG_MAX
        if limite is None:
            return max_val
        if limite < 1:
            raise ValueError(
                f"limite must be >= 1; got {limite}"
            )
        if limite > max_val:
            raise ValueError(
                f"limite {limite} exceeds maximum allowed value {max_val} (AUDIT_PANEL_LOG_MAX)"
            )
        return limite

    # ------------------------------------------------------------------
    # Public service methods
    # ------------------------------------------------------------------

    async def acciones_por_dia(
        self,
        *,
        current_user: CurrentUser,
        grant: PermissionGrant,
        desde: Optional[datetime] = None,
        hasta: Optional[datetime] = None,
        materia_id: Optional[str] = None,
    ) -> List[AccionesPorDiaRow]:
        """Return time series of actions grouped by day."""
        actor_filter = self._resolve_actor_filter(current_user, grant)
        return await self._repo.acciones_por_dia(
            actor_user_id=actor_filter,
            desde=desde,
            hasta=hasta,
            materia_id=materia_id,
        )

    async def interacciones_docente(
        self,
        *,
        current_user: CurrentUser,
        grant: PermissionGrant,
        actor_user_id: Optional[uuid.UUID] = None,
        desde: Optional[datetime] = None,
        hasta: Optional[datetime] = None,
    ) -> List[InteraccionesDocenteRow]:
        """Return aggregate (actor, accion, total) rows."""
        actor_filter = self._resolve_actor_filter(current_user, grant)
        # If scope is propio the grant's actor_filter takes precedence;
        # an explicit actor_user_id query param is only respected on global scope.
        effective_actor = actor_filter if actor_filter is not None else actor_user_id
        return await self._repo.interacciones_por_docente(
            actor_user_id=effective_actor,
            desde=desde,
            hasta=hasta,
        )

    async def interacciones_docente_materia(
        self,
        *,
        current_user: CurrentUser,
        grant: PermissionGrant,
        actor_user_id: Optional[uuid.UUID] = None,
        materia_id: Optional[str] = None,
        desde: Optional[datetime] = None,
        hasta: Optional[datetime] = None,
    ) -> List[InteraccionesDocenteMateriaRow]:
        """Return aggregate (actor, materia_id|None, total) rows (D1)."""
        actor_filter = self._resolve_actor_filter(current_user, grant)
        effective_actor = actor_filter if actor_filter is not None else actor_user_id
        return await self._repo.interacciones_por_docente_materia(
            actor_user_id=effective_actor,
            materia_id=materia_id,
            desde=desde,
            hasta=hasta,
        )

    async def comunicaciones_por_docente(
        self,
        *,
        current_user: CurrentUser,
        grant: PermissionGrant,
        estado: Optional[ComunicacionEstado] = None,
    ) -> List[ComunicacionesDocenteRow]:
        """Return distribution (enviado_por, estado, total) over comunicacion (D2)."""
        actor_filter = self._resolve_actor_filter(current_user, grant)
        return await self._repo.comunicaciones_por_docente(
            actor_user_id=actor_filter,
            estado=estado,
        )

    async def ultimas_acciones(
        self,
        *,
        current_user: CurrentUser,
        grant: PermissionGrant,
        limite: Optional[int] = None,
        actor_user_id: Optional[uuid.UUID] = None,
        desde: Optional[datetime] = None,
        hasta: Optional[datetime] = None,
        materia_id: Optional[str] = None,
    ):
        """
        Return the most recent audit events (D4).

        Validates limite against AUDIT_PANEL_LOG_MAX before querying.
        """
        resolved_limite = self._validate_limite(limite)
        actor_filter = self._resolve_actor_filter(current_user, grant)
        effective_actor = actor_filter if actor_filter is not None else actor_user_id
        return await self._repo.ultimas_acciones(
            limite=resolved_limite,
            actor_user_id=effective_actor,
            desde=desde,
            hasta=hasta,
            materia_id=materia_id,
        )
