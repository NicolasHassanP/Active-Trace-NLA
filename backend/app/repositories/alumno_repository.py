"""
AlumnoRepository — C-25 alumno-portal.

D6 — Repositorio dedicado, no hereda TenantScopedRepository (joins complejos
     multi-tabla no se adaptan al patrón genérico).

Métodos:
    get_entradas_padron_activas(usuario_id)
        → list[(EntradaPadron, Materia)]  — versiones activas del alumno.

    get_calificaciones_por_entradas(entrada_padron_ids)
        → list[Calificacion]             — calificaciones de esas entradas.

    get_reservas_activas(usuario_id)
        → list[tuple]                    — reservas Activa con datos de turno,
                                           evaluacion y materia.

tenant_id siempre inyectado; deleted_at IS NULL en todos los joins.
Identidad SIEMPRE desde CurrentUser, nunca del body/params.
snake_case; ≤500 LOC.
"""
import uuid
from typing import List, Tuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.calificacion import Calificacion
from app.models.estructura import Materia
from app.models.evaluacion import Evaluacion, ReservaEstado, ReservaEvaluacion, TurnoEvaluacion
from app.models.padron import EntradaPadron, VersionPadron


class AlumnoRepository:
    def __init__(self, session: AsyncSession, tenant_id: uuid.UUID) -> None:
        self._session = session
        self._tenant_id = tenant_id

    # -----------------------------------------------------------------------
    # Task 2.1 — entradas del padrón activas para el alumno
    # -----------------------------------------------------------------------

    async def get_entradas_padron_activas(
        self, usuario_id: uuid.UUID
    ) -> List[Tuple[EntradaPadron, Materia]]:
        """Retorna (EntradaPadron, Materia) de versiones activas del alumno."""
        stmt = (
            select(EntradaPadron, Materia)
            .join(
                VersionPadron,
                (EntradaPadron.version_id == VersionPadron.id)
                & (VersionPadron.tenant_id == self._tenant_id)
                & (VersionPadron.activa.is_(True))
                & (VersionPadron.deleted_at.is_(None)),
            )
            .join(
                Materia,
                (VersionPadron.materia_id == Materia.id)
                & (Materia.tenant_id == self._tenant_id)
                & (Materia.deleted_at.is_(None)),
            )
            .where(
                EntradaPadron.tenant_id == self._tenant_id,
                EntradaPadron.usuario_id == usuario_id,
                EntradaPadron.deleted_at.is_(None),
            )
        )
        result = await self._session.execute(stmt)
        return list(result.all())

    # -----------------------------------------------------------------------
    # Task 2.2 — calificaciones de una lista de entradas
    # -----------------------------------------------------------------------

    async def get_calificaciones_por_entradas(
        self, entrada_padron_ids: List[uuid.UUID]
    ) -> List[Calificacion]:
        """Retorna todas las Calificacion de las EntradaPadron dadas."""
        if not entrada_padron_ids:
            return []
        stmt = select(Calificacion).where(
            Calificacion.tenant_id == self._tenant_id,
            Calificacion.entrada_padron_id.in_(entrada_padron_ids),
            Calificacion.deleted_at.is_(None),
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    # -----------------------------------------------------------------------
    # Task 2.3 — reservas activas del alumno con contexto de turno+materia
    # -----------------------------------------------------------------------

    async def get_reservas_activas(
        self, usuario_id: uuid.UUID
    ) -> List[Tuple[ReservaEvaluacion, TurnoEvaluacion, Evaluacion, Materia]]:
        """Retorna reservas Activa con turno, evaluacion y nombre de materia."""
        stmt = (
            select(ReservaEvaluacion, TurnoEvaluacion, Evaluacion, Materia)
            .join(
                TurnoEvaluacion,
                (ReservaEvaluacion.turno_id == TurnoEvaluacion.id)
                & (TurnoEvaluacion.tenant_id == self._tenant_id)
                & (TurnoEvaluacion.deleted_at.is_(None)),
            )
            .join(
                Evaluacion,
                (ReservaEvaluacion.evaluacion_id == Evaluacion.id)
                & (Evaluacion.tenant_id == self._tenant_id)
                & (Evaluacion.deleted_at.is_(None)),
            )
            .join(
                Materia,
                (Evaluacion.materia_id == Materia.id)
                & (Materia.tenant_id == self._tenant_id)
                & (Materia.deleted_at.is_(None)),
            )
            .where(
                ReservaEvaluacion.tenant_id == self._tenant_id,
                ReservaEvaluacion.alumno_id == usuario_id,
                ReservaEvaluacion.estado == ReservaEstado.Activa,
                ReservaEvaluacion.deleted_at.is_(None),
            )
        )
        result = await self._session.execute(stmt)
        return list(result.all())
