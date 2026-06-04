"""
encuentro_repository.py — Repositorio de slots e instancias de encuentro.

C-13 Design:
    Extiende TenantScopedRepository para SlotEncuentro e InstanciaEncuentro.
    Siempre filtra por tenant_id. Incluye queries adicionales por slot y materia.

Queries ONLY here — never in services or routers.
snake_case; ≤500 LOC.
"""
import uuid
from datetime import date
from typing import List, Optional

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.encuentro import (
    InstanciaEncuentro,
    InstanciaEncuentroEstado,
    SlotEncuentro,
)
from app.repositories.base import TenantScopedRepository


# ---------------------------------------------------------------------------
# SlotEncuentroRepository
# ---------------------------------------------------------------------------

class SlotEncuentroRepository(TenantScopedRepository[SlotEncuentro]):
    """Repository for SlotEncuentro, always tenant-scoped."""

    def __init__(self, session: AsyncSession, tenant_id: uuid.UUID) -> None:
        super().__init__(SlotEncuentro, session, tenant_id)

    async def list_by_asignacion(self, asignacion_id: uuid.UUID) -> List[SlotEncuentro]:
        """List all active slots for a given asignacion within this tenant."""
        stmt = self._base_query().where(
            SlotEncuentro.asignacion_id == asignacion_id
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def list_by_materia(self, materia_id: uuid.UUID) -> List[SlotEncuentro]:
        """List all active slots for a given materia within this tenant."""
        stmt = self._base_query().where(
            SlotEncuentro.materia_id == materia_id
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def bulk_add(self, slots: List[SlotEncuentro]) -> List[SlotEncuentro]:
        """Persist multiple slots at once, forcing tenant_id from scope."""
        for slot in slots:
            slot.tenant_id = self._tenant_id
            self._session.add(slot)
        await self._session.commit()
        for slot in slots:
            await self._session.refresh(slot)
        return slots


# ---------------------------------------------------------------------------
# InstanciaEncuentroRepository
# ---------------------------------------------------------------------------

class InstanciaEncuentroRepository(TenantScopedRepository[InstanciaEncuentro]):
    """Repository for InstanciaEncuentro, always tenant-scoped."""

    def __init__(self, session: AsyncSession, tenant_id: uuid.UUID) -> None:
        super().__init__(InstanciaEncuentro, session, tenant_id)

    async def list_by_slot(self, slot_id: uuid.UUID) -> List[InstanciaEncuentro]:
        """List all active instances for a given slot within this tenant."""
        stmt = self._base_query().where(
            InstanciaEncuentro.slot_id == slot_id
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def list_by_materia(
        self,
        materia_id: Optional[uuid.UUID] = None,
        asignacion_ids: Optional[List[uuid.UUID]] = None,
    ) -> List[InstanciaEncuentro]:
        """
        List instances filtered by materia and/or slot asignacion scope.

        For COORDINADOR/ADMIN: pass materia_id only (no asignacion restriction).
        For PROFESOR: pass asignacion_ids to scope to their own slots.
        """
        stmt = self._base_query()

        if materia_id is not None:
            stmt = stmt.where(InstanciaEncuentro.materia_id == materia_id)

        if asignacion_ids is not None:
            # Join through slot to filter by asignacion
            slot_ids_subq = (
                select(SlotEncuentro.id)
                .where(
                    SlotEncuentro.asignacion_id.in_(asignacion_ids),
                    SlotEncuentro.tenant_id == self._tenant_id,
                    SlotEncuentro.deleted_at.is_(None),
                )
            )
            stmt = stmt.where(
                InstanciaEncuentro.slot_id.in_(slot_ids_subq)
            )

        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def bulk_add(self, instancias: List[InstanciaEncuentro]) -> List[InstanciaEncuentro]:
        """Persist multiple instancias at once, forcing tenant_id from scope."""
        for inst in instancias:
            inst.tenant_id = self._tenant_id
            self._session.add(inst)
        await self._session.commit()
        for inst in instancias:
            await self._session.refresh(inst)
        return instancias
