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

snake_case; ≤500 LOC. Queries SOLO en repositories (regla dura #11).
"""
import uuid
from typing import List, Optional

from sqlalchemy import select
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
