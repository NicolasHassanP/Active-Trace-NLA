"""
evaluacion_repository.py — Repositorios para C-14 evaluaciones-y-coloquios.

Repositorios:
    EvaluacionRepository        — CRUD + listar_con_metricas (métricas derivadas).
    TurnoEvaluacionRepository   — alta de turnos, get_for_update, conteo reservas.
    CandidatoEvaluacionRepository — import idempotente, existencia de candidato,
                                    listar_convocatorias_del_alumno (HU-47).
    ReservaEvaluacionRepository  — alta, cancelación, conteos.
    ResultadoEvaluacionRepository — upsert, consultas.

Design decisions:
    D2  — cupos_libres y reservas_activas SIEMPRE derivados en query (nunca denormalizados).
    D3  — get_for_update usa SELECT ... FOR UPDATE (lock pesimista).
    Multi-tenancy: siempre filtrado por tenant_id (base repo scope).
    Soft delete: repositorio base provee delete() (sets deleted_at).

Queries ONLY here — never in services or routers.
snake_case; ≤500 LOC.
"""
import uuid
from datetime import date
from typing import Any, Dict, List, Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.evaluacion import (
    CandidatoEvaluacion,
    Evaluacion,
    ReservaEvaluacion,
    ReservaEstado,
    ResultadoEvaluacion,
    TurnoEvaluacion,
)
from app.repositories.base import TenantScopedRepository


# ---------------------------------------------------------------------------
# EvaluacionRepository
# ---------------------------------------------------------------------------

class EvaluacionRepository(TenantScopedRepository[Evaluacion]):
    """Repository for Evaluacion (convocatoria), always tenant-scoped."""

    def __init__(self, session: AsyncSession, tenant_id: uuid.UUID) -> None:
        super().__init__(Evaluacion, session, tenant_id)

    async def listar_con_metricas(self) -> List[Dict[str, Any]]:
        """
        List all active evaluaciones with derived metrics:
            convocados      — count of CandidatoEvaluacion (not soft-deleted)
            reservas_activas — count of ReservaEvaluacion with estado=Activa
            cupos_libres    — sum(turno.cupo_total) - reservas_activas

        Metrics are ALWAYS derived at query time (D2 — no denormalization).
        """
        # Subquery for convocados count
        cand_count = (
            select(
                CandidatoEvaluacion.evaluacion_id,
                func.count(CandidatoEvaluacion.id).label("convocados"),
            )
            .where(
                CandidatoEvaluacion.tenant_id == self._tenant_id,
                CandidatoEvaluacion.deleted_at.is_(None),
            )
            .group_by(CandidatoEvaluacion.evaluacion_id)
            .subquery()
        )

        # Subquery for reservas_activas count
        res_count = (
            select(
                ReservaEvaluacion.evaluacion_id,
                func.count(ReservaEvaluacion.id).label("reservas_activas"),
            )
            .where(
                ReservaEvaluacion.tenant_id == self._tenant_id,
                ReservaEvaluacion.estado == ReservaEstado.Activa,
                ReservaEvaluacion.deleted_at.is_(None),
            )
            .group_by(ReservaEvaluacion.evaluacion_id)
            .subquery()
        )

        # Subquery for total cupo across all active turns
        cupo_total_sq = (
            select(
                TurnoEvaluacion.evaluacion_id,
                func.coalesce(func.sum(TurnoEvaluacion.cupo_total), 0).label("cupo_total"),
            )
            .where(
                TurnoEvaluacion.tenant_id == self._tenant_id,
                TurnoEvaluacion.deleted_at.is_(None),
            )
            .group_by(TurnoEvaluacion.evaluacion_id)
            .subquery()
        )

        stmt = (
            select(
                Evaluacion,
                func.coalesce(cand_count.c.convocados, 0).label("convocados"),
                func.coalesce(res_count.c.reservas_activas, 0).label("reservas_activas"),
                func.coalesce(cupo_total_sq.c.cupo_total, 0).label("cupo_total_sum"),
            )
            .outerjoin(cand_count, cand_count.c.evaluacion_id == Evaluacion.id)
            .outerjoin(res_count, res_count.c.evaluacion_id == Evaluacion.id)
            .outerjoin(cupo_total_sq, cupo_total_sq.c.evaluacion_id == Evaluacion.id)
            .where(
                Evaluacion.tenant_id == self._tenant_id,
                Evaluacion.deleted_at.is_(None),
            )
        )

        result = await self._session.execute(stmt)
        rows = result.all()

        metrics = []
        for row in rows:
            ev = row[0]
            convocados = int(row[1])
            reservas_activas = int(row[2])
            cupo_total = int(row[3])
            metrics.append({
                "id": ev.id,
                "evaluacion": ev,
                "convocados": convocados,
                "reservas_activas": reservas_activas,
                "cupos_libres": cupo_total - reservas_activas,
            })
        return metrics


# ---------------------------------------------------------------------------
# TurnoEvaluacionRepository
# ---------------------------------------------------------------------------

class TurnoEvaluacionRepository(TenantScopedRepository[TurnoEvaluacion]):
    """Repository for TurnoEvaluacion, always tenant-scoped."""

    def __init__(self, session: AsyncSession, tenant_id: uuid.UUID) -> None:
        super().__init__(TurnoEvaluacion, session, tenant_id)

    async def list_by_evaluacion(self, evaluacion_id: uuid.UUID) -> List[TurnoEvaluacion]:
        """List all active turns for a given evaluacion."""
        stmt = self._base_query().where(
            TurnoEvaluacion.evaluacion_id == evaluacion_id
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def get_for_update(self, turno_id: uuid.UUID) -> Optional[TurnoEvaluacion]:
        """
        Get the turno with a row-level lock (SELECT ... FOR UPDATE).

        Used by crear_reserva to prevent over-booking under concurrency (D3).
        The lock is held until the transaction commits or rolls back.
        """
        stmt = (
            select(TurnoEvaluacion)
            .where(
                TurnoEvaluacion.id == turno_id,
                TurnoEvaluacion.tenant_id == self._tenant_id,
                TurnoEvaluacion.deleted_at.is_(None),
            )
            .with_for_update()
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def count_reservas_activas(self, turno_id: uuid.UUID) -> int:
        """Count active reservations for a specific turn."""
        stmt = (
            select(func.count(ReservaEvaluacion.id))
            .where(
                ReservaEvaluacion.turno_id == turno_id,
                ReservaEvaluacion.tenant_id == self._tenant_id,
                ReservaEvaluacion.estado == ReservaEstado.Activa,
                ReservaEvaluacion.deleted_at.is_(None),
            )
        )
        result = await self._session.execute(stmt)
        return result.scalar() or 0

    async def bulk_add(self, turnos: List[TurnoEvaluacion]) -> List[TurnoEvaluacion]:
        """Persist multiple turns at once, forcing tenant_id from scope."""
        for turno in turnos:
            turno.tenant_id = self._tenant_id
            self._session.add(turno)
        await self._session.commit()
        for turno in turnos:
            await self._session.refresh(turno)
        return turnos


# ---------------------------------------------------------------------------
# CandidatoEvaluacionRepository
# ---------------------------------------------------------------------------

class CandidatoEvaluacionRepository(TenantScopedRepository[CandidatoEvaluacion]):
    """Repository for CandidatoEvaluacion, always tenant-scoped."""

    def __init__(self, session: AsyncSession, tenant_id: uuid.UUID) -> None:
        super().__init__(CandidatoEvaluacion, session, tenant_id)

    async def list_by_evaluacion(self, evaluacion_id: uuid.UUID) -> List[CandidatoEvaluacion]:
        """List all active candidates for a given evaluacion."""
        stmt = self._base_query().where(
            CandidatoEvaluacion.evaluacion_id == evaluacion_id
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def import_idempotente(
        self,
        evaluacion_id: uuid.UUID,
        alumno_ids: List[uuid.UUID],
    ) -> List[CandidatoEvaluacion]:
        """
        Import a list of alumnos as candidates for a convocatoria.

        Idempotent: if a (evaluacion_id, alumno_id) pair already exists
        (not soft-deleted), it is not duplicated.
        """
        result = []
        for alumno_id in alumno_ids:
            # Check if already exists
            stmt = self._base_query().where(
                CandidatoEvaluacion.evaluacion_id == evaluacion_id,
                CandidatoEvaluacion.alumno_id == alumno_id,
            )
            existing = await self._session.execute(stmt)
            cand = existing.scalar_one_or_none()
            if cand is None:
                cand = CandidatoEvaluacion(
                    tenant_id=self._tenant_id,
                    evaluacion_id=evaluacion_id,
                    alumno_id=alumno_id,
                )
                self._session.add(cand)
                await self._session.flush()
            result.append(cand)
        await self._session.commit()
        return result

    async def is_candidato(
        self,
        evaluacion_id: uuid.UUID,
        alumno_id: uuid.UUID,
    ) -> bool:
        """Return True if the alumno is an active candidate of the evaluacion."""
        stmt = self._base_query().where(
            CandidatoEvaluacion.evaluacion_id == evaluacion_id,
            CandidatoEvaluacion.alumno_id == alumno_id,
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def listar_convocatorias_del_alumno(
        self,
        alumno_id: uuid.UUID,
    ) -> list:
        """
        HU-47 — Lista las convocatorias donde el alumno es candidato (no cerradas).

        Por cada convocatoria retorna los turnos con cupos_disponibles derivados (D2).
        Retorna una lista de ConvocatoriasAlumnoRead (importada aquí para evitar
        dependencia circular con schemas — se construye el dict directamente).
        """
        from app.models.estructura import Materia
        from app.schemas.evaluacion import ConvocatoriasAlumnoRead, TurnoConCupoRead

        # Paso 1: obtener evaluacion_ids donde el alumno es candidato (activas, no cerradas)
        stmt_evals = (
            select(Evaluacion)
            .join(CandidatoEvaluacion, CandidatoEvaluacion.evaluacion_id == Evaluacion.id)
            .where(
                CandidatoEvaluacion.alumno_id == alumno_id,
                CandidatoEvaluacion.tenant_id == self._tenant_id,
                CandidatoEvaluacion.deleted_at.is_(None),
                Evaluacion.tenant_id == self._tenant_id,
                Evaluacion.cerrada.is_(False),
                Evaluacion.deleted_at.is_(None),
            )
        )
        result_evals = await self._session.execute(stmt_evals)
        evaluaciones = list(result_evals.scalars().all())

        if not evaluaciones:
            return []

        # Paso 2: para cada evaluacion cargar materia_nombre + turnos con cupos derivados
        output: list = []
        for ev in evaluaciones:
            # Materia nombre
            stmt_mat = select(Materia.nombre).where(
                Materia.id == ev.materia_id,
                Materia.deleted_at.is_(None),
            )
            materia_nombre = (await self._session.execute(stmt_mat)).scalar_one_or_none() or ""

            # Turnos de la evaluacion
            stmt_turnos = (
                select(TurnoEvaluacion)
                .where(
                    TurnoEvaluacion.evaluacion_id == ev.id,
                    TurnoEvaluacion.tenant_id == self._tenant_id,
                    TurnoEvaluacion.deleted_at.is_(None),
                )
            )
            result_turnos = await self._session.execute(stmt_turnos)
            turnos = list(result_turnos.scalars().all())

            # Cupos disponibles por turno (D2 — derivados en query)
            turnos_read: list = []
            for turno in turnos:
                stmt_res = (
                    select(func.count(ReservaEvaluacion.id))
                    .where(
                        ReservaEvaluacion.turno_id == turno.id,
                        ReservaEvaluacion.tenant_id == self._tenant_id,
                        ReservaEvaluacion.estado == ReservaEstado.Activa,
                        ReservaEvaluacion.deleted_at.is_(None),
                    )
                )
                activas = (await self._session.execute(stmt_res)).scalar() or 0
                cupos_disponibles = max(0, turno.cupo_total - activas)
                turnos_read.append(
                    TurnoConCupoRead(
                        id=turno.id,
                        evaluacion_id=turno.evaluacion_id,
                        fecha=turno.fecha,
                        cupo_total=turno.cupo_total,
                        franja=turno.franja,
                        cupos_disponibles=cupos_disponibles,
                    )
                )

            # Reserva activa del alumno en esta convocatoria (D4 — al menos una activa)
            stmt_reserva = (
                select(ReservaEvaluacion.id)
                .where(
                    ReservaEvaluacion.alumno_id == alumno_id,
                    ReservaEvaluacion.evaluacion_id == ev.id,
                    ReservaEvaluacion.tenant_id == self._tenant_id,
                    ReservaEvaluacion.estado == ReservaEstado.Activa,
                    ReservaEvaluacion.deleted_at.is_(None),
                )
                .limit(1)
            )
            reserva_activa_id = (await self._session.execute(stmt_reserva)).scalar_one_or_none()

            output.append(
                ConvocatoriasAlumnoRead(
                    evaluacion_id=ev.id,
                    materia_nombre=materia_nombre,
                    instancia=ev.instancia,
                    tipo=ev.tipo,
                    turnos=turnos_read,
                    reserva_activa_id=reserva_activa_id,
                )
            )

        return output


# ---------------------------------------------------------------------------
# ReservaEvaluacionRepository
# ---------------------------------------------------------------------------

class ReservaEvaluacionRepository(TenantScopedRepository[ReservaEvaluacion]):
    """Repository for ReservaEvaluacion, always tenant-scoped."""

    def __init__(self, session: AsyncSession, tenant_id: uuid.UUID) -> None:
        super().__init__(ReservaEvaluacion, session, tenant_id)

    async def count_activas_by_turno(self, turno_id: uuid.UUID) -> int:
        """Count active reservations for a specific turn."""
        stmt = (
            select(func.count(ReservaEvaluacion.id))
            .where(
                ReservaEvaluacion.turno_id == turno_id,
                ReservaEvaluacion.tenant_id == self._tenant_id,
                ReservaEvaluacion.estado == ReservaEstado.Activa,
                ReservaEvaluacion.deleted_at.is_(None),
            )
        )
        result = await self._session.execute(stmt)
        return result.scalar() or 0

    async def count_activas_por_alumno_convocatoria(
        self,
        alumno_id: uuid.UUID,
        evaluacion_id: uuid.UUID,
    ) -> int:
        """
        Count active reservations for an alumno across all turns of a convocatoria.

        Used to enforce the one-active-reservation-per-convocatoria rule (D4).
        """
        stmt = (
            select(func.count(ReservaEvaluacion.id))
            .where(
                ReservaEvaluacion.alumno_id == alumno_id,
                ReservaEvaluacion.evaluacion_id == evaluacion_id,
                ReservaEvaluacion.tenant_id == self._tenant_id,
                ReservaEvaluacion.estado == ReservaEstado.Activa,
                ReservaEvaluacion.deleted_at.is_(None),
            )
        )
        result = await self._session.execute(stmt)
        return result.scalar() or 0

    async def get_activa_por_alumno_convocatoria(
        self,
        alumno_id: uuid.UUID,
        evaluacion_id: uuid.UUID,
    ) -> Optional[ReservaEvaluacion]:
        """Get the active reservation (if any) of an alumno for a convocatoria."""
        stmt = self._base_query().where(
            ReservaEvaluacion.alumno_id == alumno_id,
            ReservaEvaluacion.evaluacion_id == evaluacion_id,
            ReservaEvaluacion.estado == ReservaEstado.Activa,
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def cancelar(self, reserva: ReservaEvaluacion) -> ReservaEvaluacion:
        """Set reserva.estado = Cancelada (frees the cupo, D2 — cupo is derived)."""
        reserva.estado = ReservaEstado.Cancelada
        await self._session.commit()
        await self._session.refresh(reserva)
        return reserva

    async def list_agenda(
        self,
        materia_id: Optional[uuid.UUID] = None,
        fecha_desde: Optional[date] = None,
        fecha_hasta: Optional[date] = None,
    ):
        """
        Return active reservations for the agenda view (F7.5).

        Filters: materia_id, date range.
        Only Activa reservations (Cancelada excluded from agenda).
        """
        stmt = (
            select(ReservaEvaluacion)
            .join(TurnoEvaluacion, TurnoEvaluacion.id == ReservaEvaluacion.turno_id)
            .join(Evaluacion, Evaluacion.id == ReservaEvaluacion.evaluacion_id)
            .where(
                ReservaEvaluacion.tenant_id == self._tenant_id,
                ReservaEvaluacion.estado == ReservaEstado.Activa,
                ReservaEvaluacion.deleted_at.is_(None),
                TurnoEvaluacion.deleted_at.is_(None),
                Evaluacion.deleted_at.is_(None),
            )
        )
        if materia_id is not None:
            stmt = stmt.where(Evaluacion.materia_id == materia_id)
        if fecha_desde is not None:
            stmt = stmt.where(TurnoEvaluacion.fecha >= fecha_desde)
        if fecha_hasta is not None:
            stmt = stmt.where(TurnoEvaluacion.fecha <= fecha_hasta)

        result = await self._session.execute(stmt)
        return list(result.scalars().all())


# ---------------------------------------------------------------------------
# ResultadoEvaluacionRepository
# ---------------------------------------------------------------------------

class ResultadoEvaluacionRepository(TenantScopedRepository[ResultadoEvaluacion]):
    """Repository for ResultadoEvaluacion, always tenant-scoped."""

    def __init__(self, session: AsyncSession, tenant_id: uuid.UUID) -> None:
        super().__init__(ResultadoEvaluacion, session, tenant_id)

    async def upsert(
        self,
        evaluacion_id: uuid.UUID,
        alumno_id: uuid.UUID,
        nota_final: str,
    ) -> ResultadoEvaluacion:
        """
        Insert or update the nota_final for (evaluacion_id, alumno_id).

        If a ResultadoEvaluacion already exists for this pair (not soft-deleted),
        update nota_final in place. Otherwise, create a new one.
        """
        stmt = self._base_query().where(
            ResultadoEvaluacion.evaluacion_id == evaluacion_id,
            ResultadoEvaluacion.alumno_id == alumno_id,
        )
        result = await self._session.execute(stmt)
        existing = result.scalar_one_or_none()

        if existing is not None:
            existing.nota_final = nota_final
            await self._session.commit()
            await self._session.refresh(existing)
            return existing

        nuevo = ResultadoEvaluacion(
            tenant_id=self._tenant_id,
            evaluacion_id=evaluacion_id,
            alumno_id=alumno_id,
            nota_final=nota_final,
        )
        self._session.add(nuevo)
        await self._session.commit()
        await self._session.refresh(nuevo)
        return nuevo

    async def list_by_evaluacion(self, evaluacion_id: uuid.UUID) -> List[ResultadoEvaluacion]:
        """List all results for a given evaluacion (academic register)."""
        stmt = self._base_query().where(
            ResultadoEvaluacion.evaluacion_id == evaluacion_id
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_alumno(
        self,
        evaluacion_id: uuid.UUID,
        alumno_id: uuid.UUID,
    ) -> Optional[ResultadoEvaluacion]:
        """Return the result for a specific alumno in a convocatoria (own only)."""
        stmt = self._base_query().where(
            ResultadoEvaluacion.evaluacion_id == evaluacion_id,
            ResultadoEvaluacion.alumno_id == alumno_id,
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()
