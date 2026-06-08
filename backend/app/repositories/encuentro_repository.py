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
        scope_materia_ids: Optional[List[uuid.UUID]] = None,
    ) -> List[InstanciaEncuentro]:
        """
        List instances filtered by materia and/or materia scope.

        For COORDINADOR/ADMIN: pass materia_id only (no scope restriction).
        For PROFESOR: pass scope_materia_ids to restrict to materias where
        they have an asignacion — filters directly on InstanciaEncuentro.materia_id.
        """
        stmt = self._base_query()

        if materia_id is not None:
            stmt = stmt.where(InstanciaEncuentro.materia_id == materia_id)

        if scope_materia_ids is not None:
            stmt = stmt.where(
                InstanciaEncuentro.materia_id.in_(scope_materia_ids)
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
