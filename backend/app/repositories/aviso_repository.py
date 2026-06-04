"""
aviso_repository.py — Repositorios para C-15 avisos-y-acknowledgment.

Repositorios:
    AvisoRepository          — CRUD + recipient feed + pending feed.
    AcknowledgmentRepository — CRUD + derived ack COUNT.

Design decisions:
    D3  — Audiencia vive aquí en una sola query tenant-scoped (4 ramas OR).
    D4  — ack count = COUNT sobre acknowledgment_aviso, nunca columna denormalizada.
    D5  — Pending feed: requiere_ack=True AND NOT EXISTS ack activo del usuario.
    OQ-1 — user↔materia via Asignacion.materia_id (subquery de asignaciones activas).

Multi-tenancy: SIEMPRE filtrado por tenant_id.
Soft delete: repositories excluyen deleted_at IS NOT NULL por defecto.
Queries ONLY here — never in services or routers.
snake_case; ≤500 LOC.
"""
import uuid
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import exists, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.aviso import (
    AcknowledgmentAviso,
    Aviso,
    AvisoAlcance,
)
from app.models.usuario import Asignacion as AsignacionModel
from app.repositories.base import TenantScopedRepository


# ---------------------------------------------------------------------------
# AvisoRepository
# ---------------------------------------------------------------------------

class AvisoRepository(TenantScopedRepository[Aviso]):
    """Repository for Aviso, always tenant-scoped."""

    def __init__(self, session: AsyncSession, tenant_id: uuid.UUID) -> None:
        super().__init__(Aviso, session, tenant_id)

    # -----------------------------------------------------------------------
    # Recipient feed — main query (D3)
    # -----------------------------------------------------------------------

    async def get_recipient_feed(
        self,
        usuario_id: uuid.UUID,
        roles: List[str],
        cohorte_id: Optional[uuid.UUID],
    ) -> List[Aviso]:
        """
        Returns avisos visible to the given user, scoped to this tenant.

        Audience filter (4-branch OR, D3):
            1. Global — matches every user.
            2. PorRol — aviso.rol_destino in user's roles.
            3. PorCohorte — aviso.cohorte_id == user's cohorte_id.
            4. PorMateria — aviso.materia_id in user's linked materias
               (via Asignacion.materia_id IS NOT NULL).

        Validity filter (RN-18):
            activo=True AND inicio_en <= now() <= fin_en.

        Ordering (D9):
            orden ASC, severidad priority (Critico=0 > Advertencia=1 > Info=2).
        """
        now = datetime.now(tz=timezone.utc)

        # Subquery: materias linked to this user via Asignacion
        linked_materias = (
            select(AsignacionModel.materia_id)
            .where(
                AsignacionModel.tenant_id == self._tenant_id,
                AsignacionModel.usuario_id == usuario_id,
                AsignacionModel.materia_id.isnot(None),
                AsignacionModel.deleted_at.is_(None),
            )
            .scalar_subquery()
        )

        # Audience branches
        audience_filter = or_(
            Aviso.alcance == AvisoAlcance.Global,
            *([Aviso.rol_destino.in_(roles)] if roles else []),
            *([Aviso.cohorte_id == cohorte_id] if cohorte_id is not None else []),
            Aviso.materia_id.in_(linked_materias),
        )

        # Severidad ordering: Critico=0, Advertencia=1, Info=2
        from sqlalchemy import case
        severidad_order = case(
            (Aviso.severidad == "Critico", 0),
            (Aviso.severidad == "Advertencia", 1),
            else_=2,
        )

        stmt = (
            select(Aviso)
            .where(
                Aviso.tenant_id == self._tenant_id,
                Aviso.deleted_at.is_(None),
                Aviso.activo.is_(True),
                Aviso.inicio_en <= now,
                Aviso.fin_en >= now,
                audience_filter,
            )
            .order_by(Aviso.orden.asc(), severidad_order.asc())
        )

        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    # -----------------------------------------------------------------------
    # Pending feed — requiere_ack AND no active ack (D5)
    # -----------------------------------------------------------------------

    async def get_pending_feed(
        self,
        usuario_id: uuid.UUID,
        roles: List[str],
        cohorte_id: Optional[uuid.UUID],
    ) -> List[Aviso]:
        """
        Returns avisos that require ack and have NOT been acknowledged by this user.

        Filters the recipient feed further: requiere_ack=True AND NOT EXISTS
        active AcknowledgmentAviso for (aviso_id, usuario_id).

        Avisos with requiere_ack=False never appear here.
        """
        now = datetime.now(tz=timezone.utc)

        linked_materias = (
            select(AsignacionModel.materia_id)
            .where(
                AsignacionModel.tenant_id == self._tenant_id,
                AsignacionModel.usuario_id == usuario_id,
                AsignacionModel.materia_id.isnot(None),
                AsignacionModel.deleted_at.is_(None),
            )
            .scalar_subquery()
        )

        audience_filter = or_(
            Aviso.alcance == AvisoAlcance.Global,
            *([Aviso.rol_destino.in_(roles)] if roles else []),
            *([Aviso.cohorte_id == cohorte_id] if cohorte_id is not None else []),
            Aviso.materia_id.in_(linked_materias),
        )

        # NOT EXISTS active ack for this user and aviso
        has_ack = (
            select(AcknowledgmentAviso.id)
            .where(
                AcknowledgmentAviso.tenant_id == self._tenant_id,
                AcknowledgmentAviso.aviso_id == Aviso.id,
                AcknowledgmentAviso.usuario_id == usuario_id,
                AcknowledgmentAviso.deleted_at.is_(None),
            )
            .correlate(Aviso)
            .exists()
        )

        from sqlalchemy import case
        severidad_order = case(
            (Aviso.severidad == "Critico", 0),
            (Aviso.severidad == "Advertencia", 1),
            else_=2,
        )

        stmt = (
            select(Aviso)
            .where(
                Aviso.tenant_id == self._tenant_id,
                Aviso.deleted_at.is_(None),
                Aviso.activo.is_(True),
                Aviso.inicio_en <= now,
                Aviso.fin_en >= now,
                Aviso.requiere_ack.is_(True),
                ~has_ack,
                audience_filter,
            )
            .order_by(Aviso.orden.asc(), severidad_order.asc())
        )

        result = await self._session.execute(stmt)
        return list(result.scalars().all())


# ---------------------------------------------------------------------------
# AcknowledgmentRepository
# ---------------------------------------------------------------------------

class AcknowledgmentRepository(TenantScopedRepository[AcknowledgmentAviso]):
    """Repository for AcknowledgmentAviso, always tenant-scoped."""

    def __init__(self, session: AsyncSession, tenant_id: uuid.UUID) -> None:
        super().__init__(AcknowledgmentAviso, session, tenant_id)

    async def get_by_aviso_usuario(
        self,
        aviso_id: uuid.UUID,
        usuario_id: uuid.UUID,
    ) -> Optional[AcknowledgmentAviso]:
        """
        Return active ack for (aviso_id, usuario_id) or None.

        Used for idempotency check before inserting (D6 service-level guard).
        """
        stmt = self._base_query().where(
            AcknowledgmentAviso.aviso_id == aviso_id,
            AcknowledgmentAviso.usuario_id == usuario_id,
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def count_acks(self, aviso_id: uuid.UUID) -> int:
        """
        Derived ack count for an aviso — excludes soft-deleted acks (D4).

        COUNT(*) over active acknowledgment_aviso for this aviso in this tenant.
        NEVER stored as a denormalized column on Aviso.
        """
        stmt = (
            select(func.count(AcknowledgmentAviso.id))
            .where(
                AcknowledgmentAviso.tenant_id == self._tenant_id,
                AcknowledgmentAviso.aviso_id == aviso_id,
                AcknowledgmentAviso.deleted_at.is_(None),
            )
        )
        result = await self._session.execute(stmt)
        return result.scalar() or 0
