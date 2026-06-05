"""
tarea_repository.py — Repositorios para C-16 tareas-internas.

Repositorios:
    TareaRepository          — CRUD + listar_mias + listar_admin (filtros).
    ComentarioTareaRepository — add comment + list thread.

Design decisions:
    D1  — Todas las queries filtran por tenant_id + deleted_at IS NULL.
    D10 — listar_admin queries viven AQUÍ, nunca en service ni router.
    D11 — lazy="noload" en los modelos (no eager-loading).
    D4  — contexto_id sin FK; no JOIN especial necesario.

Multi-tenancy: SIEMPRE filtrado por tenant_id.
Soft delete: deleted_at IS NULL por defecto.
Queries ONLY here — never in services or routers.
snake_case; ≤500 LOC.
"""
import uuid
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tarea import ComentarioTarea, Tarea, TareaEstado
from app.repositories.base import TenantScopedRepository


# ---------------------------------------------------------------------------
# TareaRepository
# ---------------------------------------------------------------------------

class TareaRepository(TenantScopedRepository[Tarea]):
    """Repository for Tarea, always tenant-scoped."""

    def __init__(self, session: AsyncSession, tenant_id: uuid.UUID) -> None:
        super().__init__(Tarea, session, tenant_id)

    # -----------------------------------------------------------------------
    # Update estado (D3 — state machine logic lives in service)
    # -----------------------------------------------------------------------

    async def update_estado(self, tarea: Tarea, nuevo_estado: TareaEstado) -> Tarea:
        """
        Update tarea estado.

        The state transition validation lives in the service (D3).
        This method just persists the new estado.
        """
        tarea.estado = nuevo_estado
        await self._session.commit()
        await self._session.refresh(tarea)
        return tarea

    # -----------------------------------------------------------------------
    # Update asignacion (used for delegacion D5)
    # -----------------------------------------------------------------------

    async def update_asignacion(
        self,
        tarea: Tarea,
        nuevo_asignado_a: uuid.UUID,
        nuevo_asignado_por: uuid.UUID,
    ) -> Tarea:
        """
        Update asignado_a and asignado_por for delegation (D5).

        Overwrites both fields. The before/after audit is emitted by the service.
        """
        tarea.asignado_a = nuevo_asignado_a
        tarea.asignado_por = nuevo_asignado_por
        await self._session.commit()
        await self._session.refresh(tarea)
        return tarea

    # -----------------------------------------------------------------------
    # listar_mias — self-service query (F8.1)
    # -----------------------------------------------------------------------

    async def listar_mias(self, usuario_id: uuid.UUID) -> List[Tarea]:
        """
        Return tareas where asignado_a == usuario_id, scoped to this tenant.

        Excludes soft-deleted tareas. Ordered by created_at descending.
        """
        stmt = (
            self._base_query()
            .where(Tarea.asignado_a == usuario_id)
            .order_by(Tarea.created_at.desc())
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    # -----------------------------------------------------------------------
    # listar_admin — admin filter query (F8.3, D10)
    # -----------------------------------------------------------------------

    async def listar_admin(
        self,
        asignado_a: Optional[uuid.UUID] = None,
        asignado_por: Optional[uuid.UUID] = None,
        materia_id: Optional[uuid.UUID] = None,
        estado: Optional[TareaEstado] = None,
        q: Optional[str] = None,
    ) -> List[Tarea]:
        """
        Return all non-deleted tareas of this tenant with optional filters (D10).

        Filters:
            asignado_a   — filter by assignee UUID.
            asignado_por — filter by actor who assigned/delegated.
            materia_id   — filter by materia FK.
            estado       — filter by TareaEstado value.
            q            — ILIKE search over descripcion (case-insensitive).

        All filters are AND-combined. ORDER BY created_at DESC.
        Queries live ONLY here — never in service or router (D10).
        """
        stmt = self._base_query().order_by(Tarea.created_at.desc())

        if asignado_a is not None:
            stmt = stmt.where(Tarea.asignado_a == asignado_a)
        if asignado_por is not None:
            stmt = stmt.where(Tarea.asignado_por == asignado_por)
        if materia_id is not None:
            stmt = stmt.where(Tarea.materia_id == materia_id)
        if estado is not None:
            stmt = stmt.where(Tarea.estado == estado)
        if q is not None and q.strip():
            stmt = stmt.where(Tarea.descripcion.ilike(f"%{q}%"))

        result = await self._session.execute(stmt)
        return list(result.scalars().all())


# ---------------------------------------------------------------------------
# ComentarioTareaRepository
# ---------------------------------------------------------------------------

class ComentarioTareaRepository(TenantScopedRepository[ComentarioTarea]):
    """Repository for ComentarioTarea, always tenant-scoped."""

    def __init__(self, session: AsyncSession, tenant_id: uuid.UUID) -> None:
        super().__init__(ComentarioTarea, session, tenant_id)

    async def add_comentario(
        self,
        tarea_id: uuid.UUID,
        autor_id: uuid.UUID,
        cuerpo: str,
        es_sistema: bool = False,
    ) -> ComentarioTarea:
        """
        Add a new comment to the thread.

        autor_id MUST come from the service (JWT), never from the body.
        es_sistema=True for system-generated comments (e.g. delegation; D5).
        Tenant is set by the repository's tenant scope.
        """
        comentario = ComentarioTarea(
            tarea_id=tarea_id,
            autor_id=autor_id,
            cuerpo=cuerpo,
            es_sistema=es_sistema,
        )
        return await self.add(comentario)

    async def listar_hilo(self, tarea_id: uuid.UUID) -> List[ComentarioTarea]:
        """
        Return active comments for a tarea_id, ordered by created_at ASC.

        Scoped to this tenant. Excludes soft-deleted comments.
        """
        stmt = (
            self._base_query()
            .where(ComentarioTarea.tarea_id == tarea_id)
            .order_by(ComentarioTarea.created_at.asc())
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())
