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
from typing import List, NamedTuple, Optional

from sqlalchemy import outerjoin, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.encuentro import DiaSemana, Guardia, GuardiaEstado
from app.models.estructura import Carrera, Cohorte, Materia
from app.models.usuario import Asignacion, Usuario
from app.repositories.base import TenantScopedRepository


class GuardiaExportRow(NamedTuple):
    guardia: Guardia
    materia_nombre: Optional[str]
    carrera_nombre: Optional[str]
    cohorte_nombre: Optional[str]
    docente_nombre: Optional[str]


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

    async def list_filtered_enriquecido(
        self,
        materia_id: Optional[uuid.UUID] = None,
        carrera_id: Optional[uuid.UUID] = None,
        cohorte_id: Optional[uuid.UUID] = None,
        dia: Optional[DiaSemana] = None,
        estado: Optional[GuardiaEstado] = None,
        asignacion_ids: Optional[List[uuid.UUID]] = None,
    ) -> List[GuardiaExportRow]:
        """
        List active guardias with resolved names for CSV export.

        JOINs Materia, Carrera, Cohorte, Asignacion, and Usuario so that
        human-readable names are available alongside the Guardia row.
        outerjoin is used so rows still appear if a related record is missing.
        """
        stmt = (
            select(
                Guardia,
                Materia.nombre.label("materia_nombre"),
                Carrera.nombre.label("carrera_nombre"),
                Cohorte.nombre.label("cohorte_nombre"),
                Usuario.nombre.label("usuario_nombre"),
                Usuario.apellidos.label("usuario_apellidos"),
            )
            .select_from(
                outerjoin(Guardia, Materia, Guardia.materia_id == Materia.id)
                .outerjoin(Carrera, Guardia.carrera_id == Carrera.id)
                .outerjoin(Cohorte, Guardia.cohorte_id == Cohorte.id)
                .outerjoin(Asignacion, Guardia.asignacion_id == Asignacion.id)
                .outerjoin(Usuario, Asignacion.usuario_id == Usuario.id)
            )
            .where(Guardia.tenant_id == self._tenant_id)
            .where(Guardia.deleted_at.is_(None))
        )

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
        rows = result.all()

        return [
            GuardiaExportRow(
                guardia=row.Guardia,
                materia_nombre=row.materia_nombre,
                carrera_nombre=row.carrera_nombre,
                cohorte_nombre=row.cohorte_nombre,
                docente_nombre=(
                    f"{row.usuario_nombre} {row.usuario_apellidos}".strip()
                    if row.usuario_nombre or row.usuario_apellidos
                    else None
                ),
            )
            for row in rows
        ]
