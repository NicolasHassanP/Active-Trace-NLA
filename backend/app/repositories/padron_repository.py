"""
padron_repository.py — Repository tenant-scoped para padrón versionado.

C-09 Design Decisions:
    D2 — activa como cursor: UPDATE prior active + INSERT new, misma transacción.
    D4 — usuario_id nullable en EntradaPadron.
    D6 — soft delete de versión + entradas en misma transacción.

PadronRepository(TenantScopedRepository[VersionPadron]):
    - get_active_version(materia_id, cohorte_id) → VersionPadron | None
    - create_and_activate(version_data, entries_data) → VersionPadron
    - soft_delete_version(version_id, current_time) → None

Queries SOLO en repositories (regla dura #11).
snake_case; ≤500 LOC.
"""
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.padron import EntradaPadron, VersionPadron
from app.repositories.base import TenantScopedRepository


class PadronRepository(TenantScopedRepository[VersionPadron]):
    """
    Repository tenant-scoped para VersionPadron y EntradaPadron.

    Hereda de TenantScopedRepository: add, get_by_id, list, delete.
    Agrega:
        get_active_version: única versión activa para materia×cohorte.
        create_and_activate: UPDATE prior active + INSERT new + INSERT entries (misma tx).
        soft_delete_version: soft-delete de versión + todas sus entradas.
    """

    def __init__(self, session: AsyncSession, tenant_id: uuid.UUID) -> None:
        super().__init__(VersionPadron, session, tenant_id)

    # -----------------------------------------------------------------------
    # Lectura
    # -----------------------------------------------------------------------

    async def get_active_version(
        self,
        materia_id: uuid.UUID,
        cohorte_id: uuid.UUID,
    ) -> Optional[VersionPadron]:
        """
        Retorna la versión activa para (tenant_id, materia_id, cohorte_id).

        Returns None si no existe ninguna versión activa para esa combinación.
        Defense extra: ORDER BY cargado_at DESC LIMIT 1 para unicidad robusta.
        """
        stmt = (
            select(VersionPadron)
            .where(
                VersionPadron.tenant_id == self._tenant_id,
                VersionPadron.materia_id == materia_id,
                VersionPadron.cohorte_id == cohorte_id,
                VersionPadron.activa.is_(True),
                VersionPadron.deleted_at.is_(None),
            )
            .order_by(VersionPadron.cargado_at.desc())
            .limit(1)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    # -----------------------------------------------------------------------
    # Escritura atómica
    # -----------------------------------------------------------------------

    async def create_and_activate(
        self,
        version_data: dict[str, Any],
        entries_data: list[dict[str, Any]],
    ) -> VersionPadron:
        """
        Crea una nueva VersionPadron y la activa desactivando la anterior.

        Algoritmo (D2):
            1. UPDATE prior active version SET activa=False WHERE (tenant, materia, cohorte, activa=True)
            2. INSERT new VersionPadron con activa=True
            3. INSERT all EntradaPadron para la nueva versión

        Todo en la misma transacción de la sesión DB (commit al final).

        Nota: usa `synchronize_session="evaluate"` en el UPDATE para evitar conflictos
        de autoflush con asyncpg en Python 3.14.

        Args:
            version_data: dict con campos para VersionPadron (sin entries).
            entries_data: list de dicts con campos para EntradaPadron.

        Returns:
            La nueva VersionPadron con activa=True.
        """
        from app.core.security.crypto import encrypt as _encrypt

        materia_id = version_data["materia_id"]
        cohorte_id = version_data["cohorte_id"]
        cargado_por = version_data.get("cargado_por")
        new_version_id = uuid.uuid4()

        # 1. Desactivar versión previa (D2 — UPDATE primero, misma tx)
        # synchronize_session=False evita que el ORM haga un flush auto antes del UPDATE.
        await self._session.execute(
            update(VersionPadron)
            .where(
                VersionPadron.tenant_id == self._tenant_id,
                VersionPadron.materia_id == materia_id,
                VersionPadron.cohorte_id == cohorte_id,
                VersionPadron.activa.is_(True),
                VersionPadron.deleted_at.is_(None),
            )
            .values(activa=False)
            .execution_options(synchronize_session=False)
        )

        # 2. Insertar nueva versión via ORM (sin flush, sin RETURNING conflict)
        new_version = VersionPadron(
            id=new_version_id,
            tenant_id=self._tenant_id,
            materia_id=materia_id,
            cohorte_id=cohorte_id,
            cargado_por=cargado_por,
            activa=True,
        )
        self._session.add(new_version)

        # 3. Insertar entradas via ORM (agrupadas antes del commit)
        for entry in entries_data:
            # email_encrypted is stored as plaintext in entry_data;
            # the ORM's EncryptedString TypeDecorator encrypts it on flush.
            ep = EntradaPadron(
                tenant_id=self._tenant_id,
                version_id=new_version_id,
                nombre=entry.get("nombre", ""),
                apellidos=entry.get("apellidos", ""),
                email_encrypted=entry.get("email_encrypted", ""),
                comision=entry.get("comision"),
                regional=entry.get("regional"),
                usuario_id=entry.get("usuario_id"),
            )
            self._session.add(ep)

        # Commit flushes all pending ORM objects in ONE trip, avoiding
        # asyncpg "another operation in progress" errors from multiple flush() calls.
        await self._session.commit()

        # Reload the version via ORM (already in session identity map after commit)
        stmt = select(VersionPadron).where(VersionPadron.id == new_version_id)
        result = await self._session.execute(stmt)
        new_version = result.scalar_one()
        return new_version

    # -----------------------------------------------------------------------
    # Soft delete de versión + entradas
    # -----------------------------------------------------------------------

    async def soft_delete_version(
        self,
        version_id: uuid.UUID,
        current_time: Optional[datetime] = None,
    ) -> None:
        """
        Soft-delete de una VersionPadron y todas sus EntradaPadron activas.

        Pasos:
            1. UPDATE entrada_padron SET deleted_at=now WHERE version_id AND deleted_at IS NULL
            2. UPDATE version_padron SET activa=False, deleted_at=now WHERE id

        Args:
            version_id: ID de la versión a eliminar.
            current_time: timestamp a usar (defecto: now() UTC).
        """
        if current_time is None:
            current_time = datetime.now(tz=timezone.utc)

        # 1. Soft-delete todas las entradas de esta versión
        await self._session.execute(
            update(EntradaPadron)
            .where(
                EntradaPadron.version_id == version_id,
                EntradaPadron.deleted_at.is_(None),
            )
            .values(deleted_at=current_time)
        )

        # 2. Soft-delete + desactivar la versión
        await self._session.execute(
            update(VersionPadron)
            .where(VersionPadron.id == version_id)
            .values(activa=False, deleted_at=current_time)
        )

        await self._session.commit()
