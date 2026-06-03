"""
AuditRepository — append-only, tenant-scoped repository for audit events.

C-05: Design decisions D6.
    - Constructed with (session, tenant_id) — same pattern as RbacRepository.
    - Does NOT inherit TenantScopedRepository (which exposes delete()).
    - Exposes only: record(), list(), get_by_id().
    - record() OVERRIDES tenant_id from scope (same safety as TenantScopedRepository.add).
    - NO update() method, NO delete() method.

The structural absence of mutation methods makes it impossible for any caller
to accidentally corrupt the audit trail through the repository interface.
"""
import uuid
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditEvent


class AuditRepository:
    """
    Append-only repository for AuditEvent records.

    Bound to a single tenant at construction time.  Only write operation
    is record() (INSERT only).  No update, no delete.

    Usage::

        repo = AuditRepository(session=db, tenant_id=current_user.tenant_id)
        event = await repo.record(audit_event_obj)
        events = await repo.list()
        single = await repo.get_by_id(event_id)
    """

    def __init__(self, session: AsyncSession, tenant_id: uuid.UUID) -> None:
        self._session = session
        self._tenant_id = tenant_id

    # ------------------------------------------------------------------
    # Write operation — INSERT only
    # ------------------------------------------------------------------

    async def record(self, event: AuditEvent) -> AuditEvent:
        """
        Persist *event* within this tenant scope.

        Overrides event.tenant_id with the scope tenant_id to prevent
        any caller from assigning a record to a foreign tenant (same
        safety guarantee as TenantScopedRepository.add).

        Returns the persisted event with DB-assigned created_at.
        """
        event.tenant_id = self._tenant_id
        self._session.add(event)
        await self._session.commit()
        await self._session.refresh(event)
        return event

    # ------------------------------------------------------------------
    # Read operations — always scoped to this tenant
    # ------------------------------------------------------------------

    async def list(
        self,
        *,
        actor_user_id: Optional[uuid.UUID] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[AuditEvent]:
        """
        Return audit events for this tenant.

        actor_user_id — if provided, filters to only events where
                        actor_user_id matches (for scope 'propio').
        Results are ordered by created_at DESC (most recent first).
        """
        stmt = (
            select(AuditEvent)
            .where(AuditEvent.tenant_id == self._tenant_id)
            .order_by(AuditEvent.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        if actor_user_id is not None:
            stmt = stmt.where(AuditEvent.actor_user_id == actor_user_id)

        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_id(self, event_id: uuid.UUID) -> Optional[AuditEvent]:
        """
        Return the audit event with the given id, scoped to this tenant.
        Returns None if not found or if it belongs to a different tenant.
        """
        stmt = select(AuditEvent).where(
            AuditEvent.id == event_id,
            AuditEvent.tenant_id == self._tenant_id,
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()
