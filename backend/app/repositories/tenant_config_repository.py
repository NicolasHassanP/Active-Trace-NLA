"""
TenantConfigRepository — tenant-scoped repository para TenantConfig.

C-12 Design Decisions:
    D6 — Extiende TenantScopedRepository; tenant_id es estado del repo, no param.
    D7 — get_bool(clave, default): lee el flag por clave y lo castea a bool.
    D8 — set_config(clave, valor): upsert (crea si no existe, actualiza si sí).
    D9 — Aislamiento multi-tenant: tenant A no puede leer config de tenant B.

snake_case; ≤500 LOC.
"""
import uuid
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tenant_config import TenantConfig
from app.repositories.base import TenantScopedRepository


class TenantConfigRepository(TenantScopedRepository[TenantConfig]):
    """
    Repository de TenantConfig scoped a un tenant.

    Hereda de TenantScopedRepository:
        - list() → todas las config activas del tenant
        - get_by_id() → por UUID, scoped al tenant
        - add() → persiste y asigna tenant_id
        - delete() → soft-delete (marca deleted_at)
    """

    def __init__(self, session: AsyncSession, tenant_id: uuid.UUID) -> None:
        super().__init__(TenantConfig, session, tenant_id)

    # -----------------------------------------------------------------------
    # get_bool — lee un flag booleano de tenant_config
    # -----------------------------------------------------------------------

    async def get_bool(self, clave: str, *, default: bool = False) -> bool:
        """
        Lee el valor de la clave en tenant_config y lo castea a bool.

        Valores truthy: 'true', '1', 'yes', 'on' (case-insensitive).
        Cualquier otro valor se considera False.
        Si la fila no existe (o está soft-deleted), retorna `default`.

        Args:
            clave: nombre de la configuración a leer.
            default: valor a retornar si la clave no existe.

        Returns:
            El valor booleano de la configuración, o `default` si no existe.
        """
        stmt = self._base_query().where(
            TenantConfig.clave == clave
        ).limit(1)
        result = await self._session.execute(stmt)
        cfg = result.scalar_one_or_none()

        if cfg is None:
            return default

        return cfg.valor.lower().strip() in ("true", "1", "yes", "on")

    # -----------------------------------------------------------------------
    # set_config — upsert de configuración clave/valor
    # -----------------------------------------------------------------------

    async def set_config(self, clave: str, valor: str) -> TenantConfig:
        """
        Crea o actualiza la configuración clave/valor para este tenant.

        Si la clave ya existe (no borrada), actualiza su valor.
        Si no existe, crea una fila nueva.

        Args:
            clave: nombre de la configuración.
            valor: valor a almacenar (siempre TEXT).

        Returns:
            El TenantConfig creado o actualizado.
        """
        stmt = self._base_query().where(
            TenantConfig.clave == clave
        ).limit(1)
        result = await self._session.execute(stmt)
        existing = result.scalar_one_or_none()

        if existing is not None:
            existing.valor = valor
            await self._session.commit()
            await self._session.refresh(existing)
            return existing

        new_cfg = TenantConfig(
            tenant_id=self._tenant_id,
            clave=clave,
            valor=valor,
        )
        return await self.add(new_cfg)
