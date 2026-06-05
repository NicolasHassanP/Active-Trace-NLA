"""
academico.py — Modelos SQLAlchemy para C-17 programas-y-fechas-academicas.

Entidades:
    FechaAcademicaTipo  — enum Python local para tipo evaluativo (D2).
    ProgramaMateria     — documento oficial por materia × carrera × cohorte (D1).
    FechaAcademica      — instancia evaluativa por materia × cohorte × número (D1).

Design decisions:
    D1  — Dos modelos en un solo archivo (mismo change, < 500 LOC).
    D2  — FechaAcademica.tipo reutiliza el DB enum 'evaluacion_tipo' ya creado
          en migración 012 (create_type=False). Clase Python local FechaAcademicaTipo
          (no se importa EvaluacionTipo de evaluacion.py para evitar acoplamiento).
    D3  — referencia_archivo es string opaco (Text NOT NULL); el service nunca
          interpreta ni valida su contenido.
    D4  — FKs materia_id, carrera_id, cohorte_id con ON DELETE RESTRICT, indexadas.
    D5  — Unicidad parcial (WHERE deleted_at IS NULL) en migración 015.

snake_case; ≤500 LOC.
"""
import enum
import uuid
from datetime import date, datetime
from typing import Optional

from sqlalchemy import Date, DateTime, Enum as SAEnum, ForeignKey, Integer, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.mixins import TenantScopedBase


# ---------------------------------------------------------------------------
# FechaAcademicaTipo — enum Python local (D2)
# ---------------------------------------------------------------------------

class FechaAcademicaTipo(str, enum.Enum):
    """
    Tipo de instancia evaluativa.

    D2: mismo conjunto de valores que EvaluacionTipo (Parcial/TP/Coloquio/
    Recuperatorio). Se define localmente para evitar acoplamiento entre módulos
    de dominio distintos (C-14 vs C-17). Se mapea al DB enum 'evaluacion_tipo'
    ya existente (create_type=False).
    """
    Parcial = "Parcial"
    TP = "TP"
    Coloquio = "Coloquio"
    Recuperatorio = "Recuperatorio"


# ---------------------------------------------------------------------------
# ProgramaMateria — documento oficial por materia × carrera × cohorte
# ---------------------------------------------------------------------------

class ProgramaMateria(Base, TenantScopedBase):
    """
    Programa oficial de una materia para una combinación carrera × cohorte.

    Design:
        D1  — Un archivo, dos modelos (mismo change).
        D3  — referencia_archivo es puntero opaco; el service NO lo interpreta.
        D4  — FKs RESTRICT: materia, carrera, cohorte deben existir al registrar.
        D5  — Unicidad parcial por (tenant, materia, carrera, cohorte) WHERE
              deleted_at IS NULL, definida en migración 015.

    Atributos:
        materia_id          — FK → materia.id (RESTRICT, indexada)
        carrera_id          — FK → carrera.id (RESTRICT, indexada)
        cohorte_id          — FK → cohorte.id (RESTRICT, indexada)
        titulo              — texto descriptivo del programa (NOT NULL)
        referencia_archivo  — puntero opaco al servicio de almacenamiento (NOT NULL)
        cargado_at          — timestamp de carga del archivo (nullable, negocio)
    """
    __tablename__ = "programa_materia"

    # --- Contexto académico (D4) ---
    materia_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("materia.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    carrera_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("carrera.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    cohorte_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("cohorte.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    # --- Contenido (D3) ---
    titulo: Mapped[str] = mapped_column(Text, nullable=False)
    referencia_archivo: Mapped[str] = mapped_column(Text, nullable=False)

    # --- Timestamp de carga del archivo (negocio, nullable) ---
    cargado_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=None,
    )

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"<ProgramaMateria id={self.id} tenant={self.tenant_id} "
            f"materia={self.materia_id} titulo={self.titulo!r}>"
        )


# ---------------------------------------------------------------------------
# FechaAcademica — instancia evaluativa por materia × cohorte × número
# ---------------------------------------------------------------------------

class FechaAcademica(Base, TenantScopedBase):
    """
    Fecha de evaluación para una materia × cohorte × número de instancia.

    Design:
        D2  — tipo mapeado al DB enum 'evaluacion_tipo' con create_type=False.
        D4  — FKs RESTRICT: materia, cohorte deben existir.
        D5  — Unicidad parcial por (tenant, materia, cohorte, tipo, numero, periodo)
              WHERE deleted_at IS NULL, definida en migración 015.

    Atributos:
        materia_id  — FK → materia.id (RESTRICT, indexada)
        cohorte_id  — FK → cohorte.id (RESTRICT, indexada)
        tipo        — tipo evaluativo (FechaAcademicaTipo, mapeado a evaluacion_tipo)
        numero      — número de instancia (1er Parcial, 2do Parcial…)
        periodo     — período académico (formato "AAAA-N", ej. "2026-1")
        fecha       — fecha del evento evaluativo
        titulo      — descripción textual
    """
    __tablename__ = "fecha_academica"

    # --- Contexto académico (D4) ---
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

    # --- Tipo evaluativo (D2: reutiliza DB enum evaluacion_tipo) ---
    tipo: Mapped[FechaAcademicaTipo] = mapped_column(
        SAEnum(
            FechaAcademicaTipo,
            name="evaluacion_tipo",
            create_type=False,
            values_callable=lambda e: [m.value for m in e],
        ),
        nullable=False,
    )

    # --- Identificación de instancia ---
    numero: Mapped[int] = mapped_column(Integer, nullable=False)
    periodo: Mapped[str] = mapped_column(Text, nullable=False)
    fecha: Mapped[date] = mapped_column(Date, nullable=False)
    titulo: Mapped[str] = mapped_column(Text, nullable=False)

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"<FechaAcademica id={self.id} tenant={self.tenant_id} "
            f"tipo={self.tipo} numero={self.numero} fecha={self.fecha}>"
        )
