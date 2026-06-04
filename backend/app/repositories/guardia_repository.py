"""
guardia_repository.py — Repositorio de guardias de atención.

C-13 Design:
    Extiende TenantScopedRepository para Guardia.
    Siempre filtra por tenant_id. Incluye queries filtradas por asignacion,
    materia, estado, carrera, cohorte.

Queries ONLY here — never in services or routers.
snake_case; ≤500 LOC.
"""
import uuid
from typing import List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.encuentro import DiaSemana, Guardia, GuardiaEstado
from app.repositories.base import TenantScopedRepository


class GuardiaRepository(TenantScopedRepository[Guardia]):
    """Repository for Guardia, always tenant-scoped."""

    def __init__(self, session: AsyncSession, tenant_id: uuid.UUID) -> None:
        super().__init__(Guardia, session, tenant_id)

    async def list_filtered(
        self,
        materia_id: Optional[uuid.UUID] = None,
        carrera_id: Optional[uuid.UUID] = None,
        cohorte_id: Optional[uuid.UUID] = None,
        dia: Optional[DiaSemana] = None,
        estado: Optional[GuardiaEstado] = None,
        asignacion_ids: Optional[List[uuid.UUID]] = None,
    ) -> List[Guardia]:
        """
        List active guardias with optional filters within this tenant.

        asignacion_ids: if provided, restricts to guardias of those asignaciones
        (used by TUTOR/PROFESOR to see only their own).
        """
        stmt = self._base_query()

        if materia_id is not None:
            stmt = stmt.where(Guardia.materia_id == materia_id)
        if carrera_id is not None:
            stmt = stmt.where(Guardia.carrera_id == carrera_id)
        if cohorte_id is not None:
            stmt = stmt.where(Guardia.cohorte_id == cohorte_id)
        if dia is not None:
            stmt = stmt.where(Guardia.dia == dia)
        if estado is not None:
            stmt = stmt.where(Guardia.estado == estado)
        if asignacion_ids is not None:
            stmt = stmt.where(Guardia.asignacion_id.in_(asignacion_ids))

        result = await self._session.execute(stmt)
        return list(result.scalars().all())
