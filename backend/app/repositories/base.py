"""
TenantScopedRepository — generic base repository with tenant scope always active.

Design decisions (D3, D4 from design.md):
    - Constructed with (model, session, tenant_id). The tenant_id is STATE of the
      repository, NOT a parameter of each method — it's impossible to forget.
    - All reads automatically filter: tenant_id = scope AND deleted_at IS NULL.
    - add() / create() ALWAYS override tenant_id from the scope.
    - delete() marks deleted_at (soft delete) — NEVER physical DELETE.
    - list(include_deleted=True) bypasses the deleted_at filter for audit paths.

This repository intentionally does NOT handle auth / JWT resolution. The caller
(a FastAPI dependency in C-03) will obtain tenant_id from the verified JWT and
pass it here. C-02 just wires the plumbing.
"""
import uuid
from datetime import datetime, timezone
from typing import Generic, List, Optional, Type, TypeVar

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import Base


ModelT = TypeVar("ModelT", bound=Base)  # type: ignore[type-arg]


class TenantScopedRepository(Generic[ModelT]):
    """
    Generic async repository whose scope is always bound to a single tenant.

    Usage::

        repo = TenantScopedRepository(Alumno, session, tenant_id)
        alumnos = await repo.list()
        alumno  = await repo.get_by_id(some_uuid)
        new     = await repo.add(Alumno(nombre="Ana"))
        await   repo.delete(alumno)
    """

    def __init__(
        self,
        model: Type[ModelT],
        session: AsyncSession,
        tenant_id: uuid.UUID,
    ) -> None:
        self._model = model
        self._session = session
        self._tenant_id = tenant_id

    # ------------------------------------------------------------------
    # Private helper — builds the base WHERE clause for all reads
    # ------------------------------------------------------------------

    def _base_query(self, *, include_deleted: bool = False):
        """Return a SELECT statement pre-filtered by tenant and soft-delete."""
        stmt = select(self._model).where(
            self._model.tenant_id == self._tenant_id  # type: ignore[attr-defined]
        )
        if not include_deleted:
            stmt = stmt.where(
                self._model.deleted_at.is_(None)  # type: ignore[attr-defined]
            )
        return stmt

    # ------------------------------------------------------------------
    # Read operations
    # ------------------------------------------------------------------

    async def list(self, *, include_deleted: bool = False) -> List[ModelT]:
        """Return all active (or all if include_deleted) records for this tenant."""
        result = await self._session.execute(self._base_query(include_deleted=include_deleted))
        return list(result.scalars().all())

    async def get_by_id(
        self, record_id: uuid.UUID, *, include_deleted: bool = False
    ) -> Optional[ModelT]:
        """
        Return the record with the given id scoped to this tenant.
        Returns None if not found OR if it belongs to a different tenant.
        """
        stmt = self._base_query(include_deleted=include_deleted).where(
            self._model.id == record_id  # type: ignore[attr-defined]
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    # ------------------------------------------------------------------
    # Write operations
    # ------------------------------------------------------------------

    async def add(self, obj: ModelT) -> ModelT:
        """
        Persist *obj* within this tenant scope.

        The repository OVERRIDES obj.tenant_id with the scope tenant_id to
        prevent any caller from accidentally (or maliciously) assigning data
        to a foreign tenant.
        """
        obj.tenant_id = self._tenant_id  # type: ignore[attr-defined]
        self._session.add(obj)
        await self._session.commit()
        await self._session.refresh(obj)
        return obj

    # ------------------------------------------------------------------
    # Soft delete
    # ------------------------------------------------------------------

    async def delete(self, obj: ModelT) -> None:
        """
        Soft-delete *obj* by marking deleted_at with the current UTC time.
        Never executes a physical DELETE.
        """
        obj.deleted_at = datetime.now(tz=timezone.utc)  # type: ignore[attr-defined]
        await self._session.commit()
        await self._session.refresh(obj)
