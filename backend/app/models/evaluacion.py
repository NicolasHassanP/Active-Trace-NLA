"""
Modelos SQLAlchemy para C-14 evaluaciones-y-coloquios.

Entidades:
    EvaluacionTipo  — enum tipo de evaluación (DB enum 'evaluacion_tipo').
    ReservaEstado   — enum estado de reserva (DB enum 'reserva_estado').
    Evaluacion      — convocatoria de evaluación (materia + cohorte + tipo + turnos).
    TurnoEvaluacion — turno reservable de una convocatoria (fecha + cupo_total).
    CandidatoEvaluacion — padrón de candidatos importados a una convocatoria.
    ReservaEvaluacion   — reserva de un alumno sobre un turno.
    ResultadoEvaluacion — nota final por alumno y convocatoria.

Design decisions:
    D1  — Todos heredan TenantScopedBase (soft-delete, timestamps, tenant_id FK).
    D2  — Enums mapeados con create_type=False (migración 012 los crea).
    D3  — TurnoEvaluacion: evaluacion_id con FK ON DELETE RESTRICT.
    D4  — Defensa en profundidad: índice parcial único en reserva_evaluacion
          (evaluacion_id, alumno_id) WHERE estado='Activa' — creado en migración.
    D5  — __repr__ muestra solo id + campos clave (sin PII).

snake_case; ≤500 LOC.
"""
import enum
import uuid
from datetime import date
from typing import Optional

from sqlalchemy import Boolean, Date, Enum as SAEnum, ForeignKey, Integer, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.mixins import TenantScopedBase


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class EvaluacionTipo(str, enum.Enum):
    """Tipo de evaluación. Mapeado al DB enum 'evaluacion_tipo' (migración 012)."""
    Parcial = "Parcial"
    TP = "TP"
    Coloquio = "Coloquio"
    Recuperatorio = "Recuperatorio"


class ReservaEstado(str, enum.Enum):
    """Estado del ciclo de vida de una reserva de turno."""
    Activa = "Activa"
    Cancelada = "Cancelada"


# ---------------------------------------------------------------------------
# Evaluacion — convocatoria de evaluación
# ---------------------------------------------------------------------------

class Evaluacion(Base, TenantScopedBase):
    """
    Convocatoria de evaluación: agrupa los turnos reservables.

    materia_id + cohorte_id definen el contexto académico.
    dias_disponibles es la ventana de inscripción en días (metadato, D1).
    cerrada indica si la convocatoria acepta nuevas reservas.
    """
    __tablename__ = "evaluacion"

    # --- Contexto académico ---
    materia_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("materia.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    cohorte_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("cohorte.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    # --- Clasificación ---
    tipo: Mapped[EvaluacionTipo] = mapped_column(
        SAEnum(
            EvaluacionTipo,
            name="evaluacion_tipo",
            create_type=False,
            values_callable=lambda e: [m.value for m in e],
        ),
        nullable=False,
    )
    instancia: Mapped[str] = mapped_column(Text, nullable=False)

    # --- Ventana de inscripción (metadato, D1) ---
    dias_disponibles: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # --- Estado ---
    cerrada: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"<Evaluacion id={self.id} tenant={self.tenant_id} "
            f"tipo={self.tipo} instancia={self.instancia!r} cerrada={self.cerrada}>"
        )


# ---------------------------------------------------------------------------
# TurnoEvaluacion — turno reservable de una convocatoria
# ---------------------------------------------------------------------------

class TurnoEvaluacion(Base, TenantScopedBase):
    """
    Turno reservable de una convocatoria.

    evaluacion_id FK con RESTRICT: no se puede borrar la convocatoria si tiene turnos.
    franja: campo opcional para descripción horaria (OQ-2).
    """
    __tablename__ = "turno_evaluacion"

    # --- Convocatoria ---
    evaluacion_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("evaluacion.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    # --- Fecha ---
    fecha: Mapped[date] = mapped_column(Date, nullable=False, index=True)

    # --- Cupo ---
    cupo_total: Mapped[int] = mapped_column(Integer, nullable=False)

    # --- Franja horaria descriptiva (OQ-2: opcional) ---
    franja: Mapped[Optional[str]] = mapped_column(Text, nullable=True, default=None)

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"<TurnoEvaluacion id={self.id} tenant={self.tenant_id} "
            f"evaluacion_id={self.evaluacion_id} fecha={self.fecha} cupo={self.cupo_total}>"
        )


# ---------------------------------------------------------------------------
# CandidatoEvaluacion — padrón de candidatos de una convocatoria
# ---------------------------------------------------------------------------

class CandidatoEvaluacion(Base, TenantScopedBase):
    """
    Candidato importado a una convocatoria (F7.2).

    Separado del padrón general. Solo un candidato habilitado puede reservar (D5).
    Import idempotente: un par (evaluacion_id, alumno_id) no se duplica.
    """
    __tablename__ = "candidato_evaluacion"

    evaluacion_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("evaluacion.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    alumno_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("usuario.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"<CandidatoEvaluacion id={self.id} tenant={self.tenant_id} "
            f"evaluacion_id={self.evaluacion_id}>"
        )


# ---------------------------------------------------------------------------
# ReservaEvaluacion — reserva de alumno sobre un turno
# ---------------------------------------------------------------------------

class ReservaEvaluacion(Base, TenantScopedBase):
    """
    Reserva de un alumno sobre un TurnoEvaluacion.

    estado Activa/Cancelada. Cancelar libera el cupo (D2 — cupos derivados).
    Un alumno solo puede tener una reserva Activa por convocatoria (D4).
    El índice parcial único en la migración 012 es defensa en profundidad.
    alumno_id y tenant_id SIEMPRE desde el JWT — nunca del body (regla #8).
    """
    __tablename__ = "reserva_evaluacion"

    turno_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("turno_evaluacion.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    evaluacion_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("evaluacion.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    alumno_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("usuario.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    estado: Mapped[ReservaEstado] = mapped_column(
        SAEnum(
            ReservaEstado,
            name="reserva_estado",
            create_type=False,
            values_callable=lambda e: [m.value for m in e],
        ),
        nullable=False,
        default=ReservaEstado.Activa,
    )

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"<ReservaEvaluacion id={self.id} tenant={self.tenant_id} "
            f"turno_id={self.turno_id} estado={self.estado}>"
        )


# ---------------------------------------------------------------------------
# ResultadoEvaluacion — nota final por alumno y convocatoria
# ---------------------------------------------------------------------------

class ResultadoEvaluacion(Base, TenantScopedBase):
    """
    Nota final de un alumno en una convocatoria de evaluación.

    nota_final es TEXT libre (numérica o cualitativa, §E14).
    Upsert por (evaluacion_id, alumno_id) — nunca se duplica.
    alumno_id y tenant_id SIEMPRE desde JWT — nunca del body.
    """
    __tablename__ = "resultado_evaluacion"

    evaluacion_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("evaluacion.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    alumno_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("usuario.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    nota_final: Mapped[Optional[str]] = mapped_column(Text, nullable=True, default=None)

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"<ResultadoEvaluacion id={self.id} tenant={self.tenant_id} "
            f"evaluacion_id={self.evaluacion_id}>"
        )
