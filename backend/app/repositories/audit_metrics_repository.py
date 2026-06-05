"""
AuditMetricsRepository — read-only aggregate queries for C-19 panel.

C-19: Design decisions D1 (materia derivation), D3 (scope in all views),
      D5 (aggregations in SQL, not Python).

This repository ONLY exposes SELECT queries — no record(), no write ops.
All queries are automatically scoped to self._tenant_id (rule #9).

Decisions:
    D1 — materia_id is derived from entidad_id WHERE entidad_tipo='Materia'.
         Events with other entidad_tipo fall under materia_id=None.
    D3 — actor_filter (UUID | None) applies WHERE actor_user_id = actor_filter
         when provided (scope propio). None means global (no actor filter).
    D5 — GROUP BY aggregations happen in SQL, not in Python.
    D6 — This repository does NOT write audit events. No AUDITORIA_CONSULTA
         is emitted from here (the service decides).

≤500 LOC; snake_case throughout.
"""
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional

from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditAction, AuditEvent
from app.models.comunicacion import Comunicacion, ComunicacionEstado


# ---------------------------------------------------------------------------
# Result dataclasses (plain data — not Pydantic, no DB ORM mapping)
# ---------------------------------------------------------------------------

@dataclass
class AccionesPorDiaRow:
    """One bucket in the acciones-por-dia series."""
    dia: datetime        # date_trunc('day') result — timezone-aware
    total: int


@dataclass
class InteraccionesDocenteRow:
    """One (actor, accion, total) aggregate row."""
    actor_user_id: uuid.UUID
    accion: AuditAction
    total: int


@dataclass
class InteraccionesDocenteMateriaRow:
    """One (actor, materia_id|None, total) aggregate row (D1)."""
    actor_user_id: uuid.UUID
    materia_id: Optional[str]   # entidad_id where entidad_tipo='Materia', else None
    total: int


@dataclass
class ComunicacionesDocenteRow:
    """One (enviado_por, estado, total) aggregate row."""
    enviado_por: Optional[uuid.UUID]
    estado: ComunicacionEstado
    total: int


# ---------------------------------------------------------------------------
# Helpers (private)
# ---------------------------------------------------------------------------

def _apply_actor_filter(stmt, actor_user_id: Optional[uuid.UUID]):
    """Apply WHERE actor_user_id = actor_user_id when provided (D3)."""
    if actor_user_id is not None:
        stmt = stmt.where(AuditEvent.actor_user_id == actor_user_id)
    return stmt


def _apply_date_range(stmt, desde: Optional[datetime], hasta: Optional[datetime]):
    """Apply WHERE created_at >= desde AND created_at <= hasta when provided."""
    if desde is not None:
        stmt = stmt.where(AuditEvent.created_at >= desde)
    if hasta is not None:
        stmt = stmt.where(AuditEvent.created_at <= hasta)
    return stmt


# ---------------------------------------------------------------------------
# AuditMetricsRepository
# ---------------------------------------------------------------------------

class AuditMetricsRepository:
    """
    Read-only aggregate repository for the audit panel (C-19).

    Bound to a single tenant at construction time. Every method applies
    tenant_id to the WHERE clause unconditionally (rule #9).

    Usage::

        repo = AuditMetricsRepository(session=db, tenant_id=current_user.tenant_id)
        rows = await repo.acciones_por_dia()
    """

    def __init__(self, session: AsyncSession, tenant_id: uuid.UUID) -> None:
        self._session = session
        self._tenant_id = tenant_id

    # ------------------------------------------------------------------
    # 2.2 — acciones_por_dia
    # ------------------------------------------------------------------

    async def acciones_por_dia(
        self,
        *,
        actor_user_id: Optional[uuid.UUID] = None,
        desde: Optional[datetime] = None,
        hasta: Optional[datetime] = None,
        materia_id: Optional[str] = None,
    ) -> List[AccionesPorDiaRow]:
        """
        Return a time series grouped by calendar day (D5).

        actor_user_id — scope propio filter (D3).
        desde / hasta  — optional date range filters.
        materia_id     — if provided, restrict to events where
                         entidad_tipo='Materia' AND entidad_id=materia_id (D1).
        """
        dia_col = func.date_trunc("day", AuditEvent.created_at).label("dia")

        stmt = (
            select(dia_col, func.count().label("total"))
            .where(AuditEvent.tenant_id == self._tenant_id)
            .group_by(dia_col)
            .order_by(dia_col.asc())
        )
        stmt = _apply_actor_filter(stmt, actor_user_id)
        stmt = _apply_date_range(stmt, desde, hasta)
        if materia_id is not None:
            stmt = stmt.where(
                AuditEvent.entidad_tipo == "Materia",
                AuditEvent.entidad_id == materia_id,
            )

        result = await self._session.execute(stmt)
        return [AccionesPorDiaRow(dia=row.dia, total=row.total) for row in result]

    # ------------------------------------------------------------------
    # 2.3 — interacciones_por_docente
    # ------------------------------------------------------------------

    async def interacciones_por_docente(
        self,
        *,
        actor_user_id: Optional[uuid.UUID] = None,
        desde: Optional[datetime] = None,
        hasta: Optional[datetime] = None,
    ) -> List[InteraccionesDocenteRow]:
        """
        Return aggregate rows grouped by (actor_user_id, accion) (D5).

        actor_user_id — scope propio filter (D3).
        """
        stmt = (
            select(
                AuditEvent.actor_user_id,
                AuditEvent.accion,
                func.count().label("total"),
            )
            .where(AuditEvent.tenant_id == self._tenant_id)
            .group_by(AuditEvent.actor_user_id, AuditEvent.accion)
            .order_by(AuditEvent.actor_user_id, AuditEvent.accion)
        )
        stmt = _apply_actor_filter(stmt, actor_user_id)
        stmt = _apply_date_range(stmt, desde, hasta)

        result = await self._session.execute(stmt)
        return [
            InteraccionesDocenteRow(
                actor_user_id=row.actor_user_id,
                accion=row.accion,
                total=row.total,
            )
            for row in result
        ]

    # ------------------------------------------------------------------
    # 2.4 — interacciones_por_docente_materia (D1)
    # ------------------------------------------------------------------

    async def interacciones_por_docente_materia(
        self,
        *,
        actor_user_id: Optional[uuid.UUID] = None,
        materia_id: Optional[str] = None,
        desde: Optional[datetime] = None,
        hasta: Optional[datetime] = None,
    ) -> List[InteraccionesDocenteMateriaRow]:
        """
        Return aggregate rows grouped by (actor_user_id, materia_id|None) (D1, D5).

        materia_id is derived from entidad_id WHERE entidad_tipo='Materia'.
        Events with other entidad_tipo fall under materia_id=None.

        materia_id filter — if provided, restrict to entidad_tipo='Materia'
        AND entidad_id = materia_id (excludes the null bucket).
        """
        derived_materia = case(
            (AuditEvent.entidad_tipo == "Materia", AuditEvent.entidad_id),
            else_=None,
        ).label("materia_id")

        stmt = (
            select(
                AuditEvent.actor_user_id,
                derived_materia,
                func.count().label("total"),
            )
            .where(AuditEvent.tenant_id == self._tenant_id)
            .group_by(AuditEvent.actor_user_id, derived_materia)
            .order_by(AuditEvent.actor_user_id)
        )
        stmt = _apply_actor_filter(stmt, actor_user_id)
        stmt = _apply_date_range(stmt, desde, hasta)
        if materia_id is not None:
            stmt = stmt.where(
                AuditEvent.entidad_tipo == "Materia",
                AuditEvent.entidad_id == materia_id,
            )

        result = await self._session.execute(stmt)
        return [
            InteraccionesDocenteMateriaRow(
                actor_user_id=row.actor_user_id,
                materia_id=row.materia_id,
                total=row.total,
            )
            for row in result
        ]

    # ------------------------------------------------------------------
    # 2.5 — comunicaciones_por_docente
    # ------------------------------------------------------------------

    async def comunicaciones_por_docente(
        self,
        *,
        actor_user_id: Optional[uuid.UUID] = None,
        estado: Optional[ComunicacionEstado] = None,
    ) -> List[ComunicacionesDocenteRow]:
        """
        Return distribution of ComunicacionEstado grouped by (enviado_por, estado) (D2, D5).

        actor_user_id — scope propio: filter to enviado_por = actor_user_id (D3).
        estado        — optional filter to a single estado.
        """
        stmt = (
            select(
                Comunicacion.enviado_por,
                Comunicacion.estado,
                func.count().label("total"),
            )
            .where(
                Comunicacion.tenant_id == self._tenant_id,
                Comunicacion.deleted_at.is_(None),
            )
            .group_by(Comunicacion.enviado_por, Comunicacion.estado)
            .order_by(Comunicacion.enviado_por)
        )
        if actor_user_id is not None:
            stmt = stmt.where(Comunicacion.enviado_por == actor_user_id)
        if estado is not None:
            stmt = stmt.where(Comunicacion.estado == estado)

        result = await self._session.execute(stmt)
        return [
            ComunicacionesDocenteRow(
                enviado_por=row.enviado_por,
                estado=row.estado,
                total=row.total,
            )
            for row in result
        ]

    # ------------------------------------------------------------------
    # 2.6 — ultimas_acciones
    # ------------------------------------------------------------------

    async def ultimas_acciones(
        self,
        *,
        limite: int = 200,
        actor_user_id: Optional[uuid.UUID] = None,
        desde: Optional[datetime] = None,
        hasta: Optional[datetime] = None,
        materia_id: Optional[str] = None,
    ) -> List[AuditEvent]:
        """
        Return the most recent audit events, ordered by created_at DESC.

        limite        — maximum rows to return (caller validates against cap).
        actor_user_id — scope propio: filter to actor_user_id (D3).
        desde / hasta — date range filters.
        materia_id    — D1: restrict to entidad_tipo='Materia' AND entidad_id=materia_id.
        """
        stmt = (
            select(AuditEvent)
            .where(AuditEvent.tenant_id == self._tenant_id)
            .order_by(AuditEvent.created_at.desc())
            .limit(limite)
        )
        stmt = _apply_actor_filter(stmt, actor_user_id)
        stmt = _apply_date_range(stmt, desde, hasta)
        if materia_id is not None:
            stmt = stmt.where(
                AuditEvent.entidad_tipo == "Materia",
                AuditEvent.entidad_id == materia_id,
            )

        result = await self._session.execute(stmt)
        return list(result.scalars().all())
