"""
Repositories tenant-scoped para C-07 usuarios y asignaciones.

D10: UsuarioRepository y AsignacionRepository sobre TenantScopedRepository.

UsuarioRepository:
    - Hereda: add, get_by_id, list, delete (soft).
    - Agrega: get_by_email_hash (unicidad por blind index).
    - Agrega: update (PATCH parcial).

AsignacionRepository:
    - Hereda: add, get_by_id, list, delete (soft).
    - Agrega: list(usuario_id=..., rol=..., responsable_id=...) con filtros opcionales.
    - Agrega: update (PATCH parcial).
    - C-08 Agrega: list_by_equipo, bulk_add, bulk_update_vigencia.

snake_case; ≤500 LOC. Queries SOLO en repositories (regla dura #11).
"""
import uuid
from datetime import date
from typing import List, Optional

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.usuario import Asignacion, RolAsignacion, Usuario
from app.repositories.base import TenantScopedRepository


# ---------------------------------------------------------------------------
# UsuarioRepository
# ---------------------------------------------------------------------------

class UsuarioRepository(TenantScopedRepository[Usuario]):
    """
    Repository tenant-scoped para Usuario.

    Hereda de TenantScopedRepository: add, get_by_id, list, delete (soft).
    Agrega get_by_email_hash para chequeo de unicidad en el service.
    """

    def __init__(self, session: AsyncSession, tenant_id: uuid.UUID) -> None:
        super().__init__(Usuario, session, tenant_id)

    async def get_by_email_hash(self, email_hash: str) -> Optional[Usuario]:
        """
        Busca un usuario no borrado por (tenant_id, email_hash).
        Retorna None si no existe.
        Usado para validación de unicidad (D3).
        """
        stmt = (
            select(Usuario)
            .where(
                Usuario.tenant_id == self._tenant_id,
                Usuario.email_hash == email_hash,
                Usuario.deleted_at.is_(None),
            )
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def update(self, obj: Usuario, **kwargs) -> Usuario:
        """
        Actualiza campos del usuario y persiste.
        Solo modifica los campos provistos en kwargs.
        """
        for key, value in kwargs.items():
            setattr(obj, key, value)
        await self._session.commit()
        await self._session.refresh(obj)
        return obj


# ---------------------------------------------------------------------------
# AsignacionRepository
# ---------------------------------------------------------------------------

class AsignacionRepository(TenantScopedRepository[Asignacion]):
    """
    Repository tenant-scoped para Asignacion.

    Hereda de TenantScopedRepository: add, get_by_id, list, delete (soft).
    Agrega:
        - list(usuario_id=..., rol=..., responsable_id=...): filtros opcionales.
        - update: PATCH parcial.
    """

    def __init__(self, session: AsyncSession, tenant_id: uuid.UUID) -> None:
        super().__init__(Asignacion, session, tenant_id)

    async def list(
        self,
        *,
        include_deleted: bool = False,
        usuario_id: Optional[uuid.UUID] = None,
        rol: Optional[RolAsignacion] = None,
        responsable_id: Optional[uuid.UUID] = None,
    ) -> List[Asignacion]:
        """
        Lista asignaciones de este tenant con filtros opcionales.

        Todos los filtros son AND. Si no se provee ninguno, devuelve todas las
        asignaciones activas (o todas si include_deleted=True) del tenant.
        """
        stmt = self._base_query(include_deleted=include_deleted)
        if usuario_id is not None:
            stmt = stmt.where(Asignacion.usuario_id == usuario_id)
        if rol is not None:
            stmt = stmt.where(Asignacion.rol == rol)
        if responsable_id is not None:
            stmt = stmt.where(Asignacion.responsable_id == responsable_id)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def update(self, obj: Asignacion, **kwargs) -> Asignacion:
        """
        Actualiza campos de la asignación y persiste.
        Solo modifica los campos provistos en kwargs.
        """
        for key, value in kwargs.items():
            setattr(obj, key, value)
        await self._session.commit()
        await self._session.refresh(obj)
        return obj

    # ------------------------------------------------------------------
    # C-08 — Equipo docente (proyección derivada de Asignacion)
    # ------------------------------------------------------------------

    async def list_by_equipo(
        self,
        materia_id: uuid.UUID,
        carrera_id: uuid.UUID,
        cohorte_id: uuid.UUID,
        *,
        rol: Optional[RolAsignacion] = None,
        responsable_id: Optional[uuid.UUID] = None,
    ) -> List[Asignacion]:
        """
        Lista asignaciones del equipo definido por (materia_id, carrera_id, cohorte_id)
        dentro del tenant scope. Excluye soft-deleted. Filtros opcionales: rol, responsable.
        """
        stmt = self._base_query(include_deleted=False)
        stmt = stmt.where(
            Asignacion.materia_id == materia_id,
            Asignacion.carrera_id == carrera_id,
            Asignacion.cohorte_id == cohorte_id,
        )
        if rol is not None:
            stmt = stmt.where(Asignacion.rol == rol)
        if responsable_id is not None:
            stmt = stmt.where(Asignacion.responsable_id == responsable_id)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def bulk_add(self, asignaciones: List[Asignacion]) -> List[Asignacion]:
        """
        Persiste múltiples Asignacion en un único commit (operación atómica).
        Fuerza tenant_id desde el scope del repo en cada objeto (D5).
        """
        for obj in asignaciones:
            obj.tenant_id = self._tenant_id
            self._session.add(obj)
        await self._session.commit()
        for obj in asignaciones:
            await self._session.refresh(obj)
        return asignaciones

    async def bulk_update_vigencia(
        self,
        materia_id: uuid.UUID,
        carrera_id: uuid.UUID,
        cohorte_id: uuid.UUID,
        desde: date,
        hasta: Optional[date],
    ) -> int:
        """
        Actualiza desde/hasta de todas las asignaciones activas del equipo.
        Retorna la cantidad de filas afectadas.
        Solo afecta asignaciones del tenant scope (no soft-deleted).
        """
        stmt = (
            update(Asignacion)
            .where(
                Asignacion.tenant_id == self._tenant_id,
                Asignacion.materia_id == materia_id,
                Asignacion.carrera_id == carrera_id,
                Asignacion.cohorte_id == cohorte_id,
                Asignacion.deleted_at.is_(None),
            )
            .values(desde=desde, hasta=hasta)
            .execution_options(synchronize_session="fetch")
        )
        result = await self._session.execute(stmt)
        await self._session.commit()
        return result.rowcount
