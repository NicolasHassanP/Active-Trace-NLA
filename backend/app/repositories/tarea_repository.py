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
    D12 — Los métodos *_enriquecido(s) resuelven materia_nombre y
           asignado_por_nombre mediante JOINs en el mismo repositorio.
           Devuelven dicts que se validan con TareaRead.model_validate.

Multi-tenancy: SIEMPRE filtrado por tenant_id.
Soft delete: deleted_at IS NULL por defecto.
Queries ONLY here — never in services or routers.
snake_case; ≤500 LOC.
"""
import uuid
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.estructura import Materia
from app.models.tarea import ComentarioTarea, Tarea, TareaEstado
from app.models.usuario import Usuario
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

    async def listar_mias_enriquecidas(self, usuario_id: uuid.UUID) -> List[Dict[str, Any]]:
        """
        Return tareas where asignado_a == usuario_id with materia_nombre and
        asignado_por_nombre resolved via JOIN (D12).

        Returns list of dicts suitable for TareaRead.model_validate.
        """
        tareas = await self.listar_mias(usuario_id)
        return [await self._enriquecer(t) for t in tareas]

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

    async def listar_admin_enriquecidas(
        self,
        asignado_a: Optional[uuid.UUID] = None,
        asignado_por: Optional[uuid.UUID] = None,
        materia_id: Optional[uuid.UUID] = None,
        estado: Optional[TareaEstado] = None,
        q: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Return admin listing with materia_nombre and asignado_por_nombre resolved
        via JOIN (D12).  Accepts the same filters as listar_admin.
        """
        tareas = await self.listar_admin(
            asignado_a=asignado_a,
            asignado_por=asignado_por,
            materia_id=materia_id,
            estado=estado,
            q=q,
        )
        return [await self._enriquecer(t) for t in tareas]

    async def get_by_id_enriquecida(self, tarea_id: uuid.UUID) -> Optional[Dict[str, Any]]:
        """
        Return a single tarea by id with materia_nombre and asignado_por_nombre
        resolved via JOIN (D12).  Returns None if not found.
        """
        tarea = await self.get_by_id(tarea_id)
        if tarea is None:
            return None
        return await self._enriquecer(tarea)

    # -----------------------------------------------------------------------
    # _enriquecer — JOIN helper (D12)
    # -----------------------------------------------------------------------

    async def _enriquecer(self, tarea: Tarea) -> Dict[str, Any]:
        """
        Build a dict from a Tarea instance enriched with human-readable names.

        Resolves:
            materia_nombre     — from materia.nombre WHERE id == tarea.materia_id
            asignado_por_nombre — from usuario.nombre + apellidos WHERE id == tarea.asignado_por

        Both fields fall back to None when the referenced row is not found so that
        soft-deleted or missing records do not cause 500 errors.
        """
        data: Dict[str, Any] = {
            "id": tarea.id,
            "tenant_id": tarea.tenant_id,
            "asignado_a": tarea.asignado_a,
            "asignado_por": tarea.asignado_por,
            "descripcion": tarea.descripcion,
            "estado": tarea.estado,
            "materia_id": tarea.materia_id,
            "contexto_id": tarea.contexto_id,
            "contexto_tipo": tarea.contexto_tipo,
            "created_at": tarea.created_at,
            "updated_at": tarea.updated_at,
            "deleted_at": tarea.deleted_at,
            "materia_nombre": None,
            "asignado_por_nombre": None,
            "asignado_a_nombre": None,
        }

        # Resolve materia_nombre (only when materia_id is set)
        if tarea.materia_id is not None:
            stmt_mat = select(Materia.nombre).where(
                Materia.id == tarea.materia_id,
                Materia.deleted_at.is_(None),
            )
            data["materia_nombre"] = (
                await self._session.execute(stmt_mat)
            ).scalar_one_or_none()

        # Resolve asignado_por_nombre via usuario.nombre + apellidos
        stmt_por = select(Usuario.nombre, Usuario.apellidos).where(
            Usuario.id == tarea.asignado_por,
            Usuario.deleted_at.is_(None),
        )
        row_por = (await self._session.execute(stmt_por)).one_or_none()
        if row_por is not None:
            data["asignado_por_nombre"] = f"{row_por.nombre} {row_por.apellidos}".strip()

        # Resolve asignado_a_nombre via usuario.nombre + apellidos
        stmt_a = select(Usuario.nombre, Usuario.apellidos).where(
            Usuario.id == tarea.asignado_a,
            Usuario.deleted_at.is_(None),
        )
        row_a = (await self._session.execute(stmt_a)).one_or_none()
        if row_a is not None:
            data["asignado_a_nombre"] = f"{row_a.nombre} {row_a.apellidos}".strip()

        return data


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
