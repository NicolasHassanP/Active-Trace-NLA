"""
Repositories para C-06 estructura académica.

D7: Tres repositories tenant-scoped sobre TenantScopedRepository.
    CarreraRepository, CohorteRepository, MateriaRepository.

Métodos comunes (via TenantScopedRepository): add, get_by_id, list, delete (soft).
Métodos auxiliares de unicidad:
    - get_by_codigo(codigo)     → Carrera / Materia, scoped por tenant, deleted_at IS NULL.
    - get_by_carrera_nombre(carrera_id, nombre) → Cohorte, scoped por tenant, deleted_at IS NULL.
    - list(carrera_id=...)      → CohorteRepository: filtrar por carrera.

snake_case; ≤500 LOC.
"""
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.estructura import Carrera, Cohorte, EstadoEstructura, Materia
from app.repositories.base import TenantScopedRepository

# Type alias: {entity_id: nombre}
NombreMap = Dict[uuid.UUID, str]


# ---------------------------------------------------------------------------
# CarreraRepository
# ---------------------------------------------------------------------------

class CarreraRepository(TenantScopedRepository[Carrera]):
    """
    Repository tenant-scoped para Carrera.

    Hereda de TenantScopedRepository: add, get_by_id, list, delete (soft).
    Agrega get_by_codigo para chequeo de unicidad en el service.
    """

    def __init__(self, session: AsyncSession, tenant_id: uuid.UUID) -> None:
        super().__init__(Carrera, session, tenant_id)

    async def get_by_codigo(self, codigo: str) -> Optional[Carrera]:
        """
        Busca una carrera no borrada por (tenant_id, codigo).
        Retorna None si no existe.
        """
        stmt = (
            select(Carrera)
            .where(
                Carrera.tenant_id == self._tenant_id,
                Carrera.codigo == codigo,
                Carrera.deleted_at.is_(None),
            )
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_open_cohortes(self, carrera_id: uuid.UUID) -> int:
        """
        Cuenta cohortes abiertas (estado=activa y vig_hasta IS NULL y deleted_at IS NULL)
        para la carrera dada dentro de este tenant.
        Usado para validar el bloqueo de desactivación (D6).
        """
        stmt = (
            select(Cohorte)
            .where(
                Cohorte.tenant_id == self._tenant_id,
                Cohorte.carrera_id == carrera_id,
                Cohorte.estado == EstadoEstructura.activa,
                Cohorte.vig_hasta.is_(None),
                Cohorte.deleted_at.is_(None),
            )
        )
        result = await self._session.execute(stmt)
        return len(result.scalars().all())

    async def get_nombres_por_ids(self, ids: List[uuid.UUID]) -> NombreMap:
        """
        Batch-fetch de nombre para un conjunto de carrera_ids.

        Emite un único SELECT con IN, scoped a tenant + soft-delete.
        Retorna un dict {carrera_id: nombre}.
        Los ids no encontrados quedan ausentes del dict.
        """
        if not ids:
            return {}
        stmt = (
            select(Carrera.id, Carrera.nombre)
            .where(
                Carrera.tenant_id == self._tenant_id,
                Carrera.id.in_(ids),
                Carrera.deleted_at.is_(None),
            )
        )
        result = await self._session.execute(stmt)
        return {row.id: row.nombre for row in result.fetchall()}

    async def update(self, obj: Carrera, **kwargs) -> Carrera:
        """
        Actualiza campos de la carrera y persiste.
        Sólo modifica los campos provistos en kwargs.
        """
        for key, value in kwargs.items():
            setattr(obj, key, value)
        await self._session.commit()
        await self._session.refresh(obj)
        return obj


# ---------------------------------------------------------------------------
# MateriaRepository
# ---------------------------------------------------------------------------

class MateriaRepository(TenantScopedRepository[Materia]):
    """
    Repository tenant-scoped para Materia.

    Hereda de TenantScopedRepository: add, get_by_id, list, delete (soft).
    Agrega get_by_codigo para chequeo de unicidad en el service.
    """

    def __init__(self, session: AsyncSession, tenant_id: uuid.UUID) -> None:
        super().__init__(Materia, session, tenant_id)

    async def get_by_codigo(self, codigo: str) -> Optional[Materia]:
        """
        Busca una materia no borrada por (tenant_id, codigo).
        Retorna None si no existe.
        """
        stmt = (
            select(Materia)
            .where(
                Materia.tenant_id == self._tenant_id,
                Materia.codigo == codigo,
                Materia.deleted_at.is_(None),
            )
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_nombres_por_ids(self, ids: List[uuid.UUID]) -> NombreMap:
        """
        Batch-fetch de nombre para un conjunto de materia_ids.

        Emite un único SELECT con IN, scoped a tenant + soft-delete.
        Retorna un dict {materia_id: nombre}.
        Los ids no encontrados quedan ausentes del dict.
        """
        if not ids:
            return {}
        stmt = (
            select(Materia.id, Materia.nombre)
            .where(
                Materia.tenant_id == self._tenant_id,
                Materia.id.in_(ids),
                Materia.deleted_at.is_(None),
            )
        )
        result = await self._session.execute(stmt)
        return {row.id: row.nombre for row in result.fetchall()}

    async def update(self, obj: Materia, **kwargs) -> Materia:
        """
        Actualiza campos de la materia y persiste.
        """
        for key, value in kwargs.items():
            setattr(obj, key, value)
        await self._session.commit()
        await self._session.refresh(obj)
        return obj


# ---------------------------------------------------------------------------
# CohorteRepository
# ---------------------------------------------------------------------------

class CohorteRepository(TenantScopedRepository[Cohorte]):
    """
    Repository tenant-scoped para Cohorte.

    Hereda de TenantScopedRepository: add, get_by_id, list, delete (soft).
    Agrega:
        - get_by_carrera_nombre: chequeo de unicidad (tenant_id, carrera_id, nombre).
        - list(carrera_id=...): filtrar por carrera.
    """

    def __init__(self, session: AsyncSession, tenant_id: uuid.UUID) -> None:
        super().__init__(Cohorte, session, tenant_id)

    async def get_by_carrera_nombre(
        self, carrera_id: uuid.UUID, nombre: str
    ) -> Optional[Cohorte]:
        """
        Busca una cohorte no borrada por (tenant_id, carrera_id, nombre).
        Retorna None si no existe.
        """
        stmt = (
            select(Cohorte)
            .where(
                Cohorte.tenant_id == self._tenant_id,
                Cohorte.carrera_id == carrera_id,
                Cohorte.nombre == nombre,
                Cohorte.deleted_at.is_(None),
            )
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def list(
        self,
        *,
        include_deleted: bool = False,
        carrera_id: Optional[uuid.UUID] = None,
    ) -> List[Cohorte]:
        """
        Lista cohortes de este tenant, opcionalmente filtrado por carrera_id.
        """
        stmt = self._base_query(include_deleted=include_deleted)
        if carrera_id is not None:
            stmt = stmt.where(Cohorte.carrera_id == carrera_id)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def get_nombres_por_ids(self, ids: List[uuid.UUID]) -> NombreMap:
        """
        Batch-fetch de nombre para un conjunto de cohorte_ids.

        Emite un único SELECT con IN, scoped a tenant + soft-delete.
        Retorna un dict {cohorte_id: nombre}.
        Los ids no encontrados quedan ausentes del dict.
        """
        if not ids:
            return {}
        stmt = (
            select(Cohorte.id, Cohorte.nombre)
            .where(
                Cohorte.tenant_id == self._tenant_id,
                Cohorte.id.in_(ids),
                Cohorte.deleted_at.is_(None),
            )
        )
        result = await self._session.execute(stmt)
        return {row.id: row.nombre for row in result.fetchall()}

    async def update(self, obj: Cohorte, **kwargs) -> Cohorte:
        """
        Actualiza campos de la cohorte y persiste.
        """
        for key, value in kwargs.items():
            setattr(obj, key, value)
        await self._session.commit()
        await self._session.refresh(obj)
        return obj
