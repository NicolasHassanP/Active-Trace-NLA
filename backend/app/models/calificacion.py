"""
Modelos Calificacion y UmbralMateria para C-10 calificaciones y umbral.

Design decisions:
    D2 — Calificacion cuelga de EntradaPadron (FK RESTRICT), materia_id desnormalizado.
    D3 — aprobado persistido (BOOLEAN NOT NULL), calculado al importar por derive_aprobado.
    D5 — UmbralMateria: unicidad por (tenant_id, asignacion_id, materia_id) WHERE deleted_at IS NULL.
    D8 — importado_por: FK→usuario ON DELETE SET NULL; forma parte de la clave única de upsert.

__repr__ NUNCA expone PII (emails, nombres del alumno).
snake_case; ≤500 LOC.
"""
import enum
import uuid
from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, Text, func
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.mixins import TenantScopedBase


# ---------------------------------------------------------------------------
# CalificacionOrigen — closed enum (persistence origin)
# ---------------------------------------------------------------------------

class CalificacionOrigen(str, enum.Enum):
    """
    Origen de la calificación:
        Importado — importada desde archivo del LMS.
        Manual    — ingresada manualmente (scope de C-11+, modelo lo soporta).
    """
    Importado = "Importado"
    Manual = "Manual"


# ---------------------------------------------------------------------------
# Calificacion — nota por alumno×materia×actividad (D2, D3, D8)
# ---------------------------------------------------------------------------

class Calificacion(Base, TenantScopedBase):
    """
    Calificación de un alumno en una actividad de una materia.

    entrada_padron_id: FK → entrada_padron (ON DELETE RESTRICT) — raíz del alumno.
    materia_id: FK → materia (desnormalizado para queries directas en C-11).
    importado_por: FK → usuario (ON DELETE SET NULL) — forma parte del scope de upsert.
    aprobado: derivado por derive_aprobado() al importar, persistido (D3).
    origen: 'Importado' | 'Manual' (calificacion_origen enum, create_type=False).

    __repr__ no expone PII (la identidad del alumno está en EntradaPadron).
    """
    __tablename__ = "calificacion"

    # --- FK a entrada_padron (NOT NULL, RESTRICT) ---
    entrada_padron_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("entrada_padron.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    # --- FK a materia (desnormalizado, RESTRICT) ---
    materia_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("materia.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    # --- FK nullable al importador (SET NULL si usuario es eliminado) ---
    importado_por: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("usuario.id", ondelete="SET NULL"),
        nullable=True,
    )

    # --- Datos de la actividad ---
    actividad: Mapped[str] = mapped_column(Text, nullable=False)

    # --- Nota numérica (nullable) ---
    nota_numerica: Mapped[Optional[Decimal]] = mapped_column(
        Numeric,
        nullable=True,
    )

    # --- Nota textual (nullable) ---
    nota_textual: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # --- Aprobado derivado (D3) — NEVER set by client ---
    aprobado: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )

    # --- Origen (D8) ---
    origen: Mapped[CalificacionOrigen] = mapped_column(
        SAEnum(
            CalificacionOrigen,
            name="calificacion_origen",
            create_type=False,  # Created by migration 008
            values_callable=lambda e: [m.value for m in e],
        ),
        nullable=False,
        default=CalificacionOrigen.Importado,
    )

    # --- Timestamp de importación ---
    importado_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    def __repr__(self) -> str:  # pragma: no cover
        # NUNCA incluye PII del alumno
        return (
            f"<Calificacion id={self.id} tenant={self.tenant_id} "
            f"entrada_padron={self.entrada_padron_id} materia={self.materia_id} "
            f"actividad={self.actividad!r} aprobado={self.aprobado}>"
        )


# ---------------------------------------------------------------------------
# UmbralMateria — criterio de aprobación por Asignacion×Materia (D5)
# ---------------------------------------------------------------------------

class UmbralMateria(Base, TenantScopedBase):
    """
    Umbral de aprobación configurado por un docente para una asignación×materia.

    asignacion_id: FK → asignacion (RESTRICT) — el docente que lo configuró.
    materia_id: FK → materia (RESTRICT) — la materia sobre la que aplica.
    umbral_pct: porcentaje mínimo aprobatorio para notas numéricas (defecto 60).
    valores_aprobatorios: lista JSONB de valores textuales que cuentan como aprobado.

    Unicidad: (tenant_id, asignacion_id, materia_id) WHERE deleted_at IS NULL
    asegurada por el índice uq_um_asignacion_materia en la migración 008.

    __repr__ no expone PII.
    """
    __tablename__ = "umbral_materia"

    # --- FK a asignacion (NOT NULL, RESTRICT) ---
    asignacion_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("asignacion.id", ondelete="RESTRICT"),
        nullable=False,
    )

    # --- FK a materia (NOT NULL, RESTRICT) ---
    materia_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("materia.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    # --- Umbral numérico (defecto 60%) ---
    umbral_pct: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=60,
    )

    # --- Valores textuales aprobatorios (JSONB list[str]) ---
    valores_aprobatorios: Mapped[List[str]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
    )

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"<UmbralMateria id={self.id} tenant={self.tenant_id} "
            f"asignacion={self.asignacion_id} materia={self.materia_id} "
            f"umbral_pct={self.umbral_pct}>"
        )
