"""
programa_repository.py — Repository para ProgramaMateria.

C-17 Design Decisions:
    D4 — Queries ONLY here — never in services or routers.
    D5 — listar() filtra siempre por tenant (base repo scope).
    D5 — existe_activo_para_combo() chequea unicidad activa antes de insertar.

snake_case; ≤500 LOC.
"""
import uuid
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.academico import ProgramaMateria
from app.repositories.base import TenantScopedRepository


class ProgramaMateriaRepository(TenantScopedRepository[ProgramaMateria]):
    """
    Repository for ProgramaMateria, always tenant-scoped.

    Extends TenantScopedRepository with listar() filtered queries
    and a duplicate-check for the partial unique constraint (D5).
    """

    def __init__(self, session: AsyncSession, tenant_id: uuid.UUID) -> None:
        super().__init__(ProgramaMateria, session, tenant_id)

    async def listar(
        self,
        materia_id: Optional[uuid.UUID] = None,
        carrera_id: Optional[uuid.UUID] = None,
        cohorte_id: Optional[uuid.UUID] = None,
    ) -> List[ProgramaMateria]:
        """
        List active programas for this tenant, with optional filters.

        All three filter parameters are optional; when supplied, only
        programas matching ALL provided filters are returned.
        Soft-deleted records are excluded (base query default).
        """
        stmt = self._base_query()

        if materia_id is not None:
            stmt = stmt.where(ProgramaMateria.materia_id == materia_id)
        if carrera_id is not None:
            stmt = stmt.where(ProgramaMateria.carrera_id == carrera_id)
        if cohorte_id is not None:
            stmt = stmt.where(ProgramaMateria.cohorte_id == cohorte_id)

        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def existe_activo_para_combo(
        self,
        materia_id: uuid.UUID,
        carrera_id: uuid.UUID,
        cohorte_id: uuid.UUID,
    ) -> bool:
        """
        Return True if an active (non-deleted) programa exists for the given
        (tenant, materia, carrera, cohorte) combination.

        Used by ProgramaService to enforce uniqueness before inserting,
        providing a clear 409 error instead of relying on DB exception alone.
        """
        stmt = self._base_query().where(
            ProgramaMateria.materia_id == materia_id,
            ProgramaMateria.carrera_id == carrera_id,
            ProgramaMateria.cohorte_id == cohorte_id,
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none() is not None
