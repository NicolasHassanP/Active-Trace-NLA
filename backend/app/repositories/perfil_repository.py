"""
PerfilRepository — C-20 perfil propio.

D1 — Perfil reusa el modelo Usuario; el repository agrega métodos de
     autoservicio (get_self, update_self) sobre TenantScopedRepository.

get_self(usuario_id):
    Busca el usuario por id, scope al tenant. Retorna None si no pertenece
    al tenant o si no existe.

update_self(usuario, **kwargs):
    PATCH parcial sobre campos editables. Solo los kwargs provistos se persisten.
    La PII (cbu, alias_cbu, dni) se cifra automáticamente via EncryptedString.

get_by_email_hash(email_hash):
    Chequeo de unicidad (tenant_id, email_hash) — necesario para validar
    cambio de email en update_self.

Queries SOLO en este repository (regla dura #11).
snake_case; ≤500 LOC.
"""
import uuid
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.usuario import Usuario
from app.repositories.base import TenantScopedRepository


class PerfilRepository(TenantScopedRepository[Usuario]):
    """
    Repository tenant-scoped para el autoservicio de perfil propio.

    Hereda de TenantScopedRepository: add, get_by_id, list, delete (soft).
    Agrega:
        - get_self: get_by_id con scope tenant (alias semántico).
        - update_self: PATCH parcial de campos editables.
        - get_by_email_hash: unicidad por blind index para cambio de email.
    """

    def __init__(self, session: AsyncSession, tenant_id: uuid.UUID) -> None:
        super().__init__(Usuario, session, tenant_id)

    async def get_self(self, usuario_id: uuid.UUID) -> Optional[Usuario]:
        """
        Obtiene el usuario por id, scoped al tenant.

        Retorna None si no existe o no pertenece al tenant del scope.
        Equivale a get_by_id pero con semántica de autoservicio.
        """
        return await self.get_by_id(usuario_id)

    async def update_self(self, obj: Usuario, **kwargs) -> Usuario:
        """
        Actualiza campos del usuario y persiste.

        Solo modifica los campos provistos en kwargs.
        La PII (cbu, alias_cbu, dni) se cifra automáticamente via EncryptedString
        en el ORM al asignar el valor.

        No valida unicidad de email — el service lo hace antes de llamar aquí.
        """
        for key, value in kwargs.items():
            setattr(obj, key, value)
        await self._session.commit()
        await self._session.refresh(obj)
        return obj

    async def get_by_email_hash(self, email_hash: str) -> Optional[Usuario]:
        """
        Busca un usuario no borrado por (tenant_id, email_hash).

        Retorna None si no existe.
        Usado para validar unicidad antes de un cambio de email.
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
