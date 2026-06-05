"""
fecha_academica_repository.py — Repository para FechaAcademica.

C-17 Design Decisions:
    D7 — listar() y listar_calendario() comparten la misma fuente de datos,
         distinta proyección/orden.
    Queries ONLY here — never in services or routers.
    Multi-tenancy: siempre filtrado por tenant_id.

snake_case; ≤500 LOC.
"""
import uuid
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.academico import FechaAcademica, FechaAcademicaTipo
from app.repositories.base import TenantScopedRepository


class FechaAcademicaRepository(TenantScopedRepository[FechaAcademica]):
    """
    Repository for FechaAcademica, always tenant-scoped.

    Provides:
        listar(filtros)                     — filtered list (tabular view)
        listar_calendario(materia, cohorte)  — ordered by fecha ASC (calendar view)
        existe_activo_para_combo(...)        — duplicate-check before insert
    """

    def __init__(self, session: AsyncSession, tenant_id: uuid.UUID) -> None:
        super().__init__(FechaAcademica, session, tenant_id)

    async def listar(
        self,
        materia_id: Optional[uuid.UUID] = None,
        cohorte_id: Optional[uuid.UUID] = None,
        tipo: Optional[FechaAcademicaTipo] = None,
        periodo: Optional[str] = None,
    ) -> List[FechaAcademica]:
        """
        List active fechas académicas for this tenant, with optional filters.

        All filter parameters are optional; when supplied, only records
        matching ALL provided filters are returned (AND logic).
        Soft-deleted records are always excluded.

        D7: tabular view — no ordering guaranteed (let client/UI sort).
        """
        stmt = self._base_query()

        if materia_id is not None:
            stmt = stmt.where(FechaAcademica.materia_id == materia_id)
        if cohorte_id is not None:
            stmt = stmt.where(FechaAcademica.cohorte_id == cohorte_id)
        if tipo is not None:
            stmt = stmt.where(FechaAcademica.tipo == tipo)
        if periodo is not None:
            stmt = stmt.where(FechaAcademica.periodo == periodo)

        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def listar_calendario(
        self,
        materia_id: uuid.UUID,
        cohorte_id: uuid.UUID,
    ) -> List[FechaAcademica]:
        """
        List active fechas académicas for a materia × cohorte, ordered by fecha ASC.

        D7: same data as listar() but ordered chronologically.
        The client (C-23) receives them ready for calendar rendering.
        """
        stmt = (
            self._base_query()
            .where(FechaAcademica.materia_id == materia_id)
            .where(FechaAcademica.cohorte_id == cohorte_id)
            .order_by(FechaAcademica.fecha.asc())
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def existe_activo_para_combo(
        self,
        materia_id: uuid.UUID,
        cohorte_id: uuid.UUID,
        tipo: FechaAcademicaTipo,
        numero: int,
        periodo: str,
    ) -> bool:
        """
        Return True if an active (non-deleted) fecha exists for the given
        (tenant, materia, cohorte, tipo, numero, periodo) combination.

        Used by FechaAcademicaService to enforce D5 uniqueness before
        inserting, providing a clear 409 error instead of relying on
        DB IntegrityError alone.
        """
        stmt = self._base_query().where(
            FechaAcademica.materia_id == materia_id,
            FechaAcademica.cohorte_id == cohorte_id,
            FechaAcademica.tipo == tipo,
            FechaAcademica.numero == numero,
            FechaAcademica.periodo == periodo,
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none() is not None
