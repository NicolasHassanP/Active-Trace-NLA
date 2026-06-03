"""
Estructura académica — modelos Carrera, Cohorte, Materia.

C-06: Catálogo estructural del tenant.

Design decisions:
    D2 — EstadoEstructura(str, enum.Enum) compartido por las tres entidades.
    D3 — Modelos sobre TenantScopedBase (UUIDMixin + TenantMixin + TimestampMixin + SoftDeleteMixin).
    D4 — Unicidad parcial (WHERE deleted_at IS NULL) via índices definidos en la migración 005.
    D5 — Cohorte.carrera_id FK obligatoria NOT NULL → carrera.id RESTRICT.
    D10 — Cohorte.anio INT NOT NULL, vig_desde DATE NOT NULL, vig_hasta DATE nullable.

snake_case throughout; ≤500 LOC.
"""
import enum
import uuid
from datetime import date
from typing import Optional

from sqlalchemy import Date, Enum as SAEnum, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.mixins import TenantScopedBase


# ---------------------------------------------------------------------------
# EstadoEstructura — enum compartido (D2)
# ---------------------------------------------------------------------------

class EstadoEstructura(str, enum.Enum):
    """
    Ciclo de vida compartido por Carrera, Cohorte y Materia.

    activa   — entidad operativa.
    inactiva — entidad desactivada (no admite nuevas operaciones).
    """
    activa = "activa"
    inactiva = "inactiva"


# ---------------------------------------------------------------------------
# Carrera (D3)
# ---------------------------------------------------------------------------

class Carrera(Base, TenantScopedBase):
    """
    Programa académico del tenant (carrera de grado/posgrado).

    Unicidad: (tenant_id, codigo) WHERE deleted_at IS NULL
    — garantizada por índice parcial ux_carrera_tenant_codigo en migración 005.
    """
    __tablename__ = "carrera"

    codigo: Mapped[str] = mapped_column(String(50), nullable=False)
    nombre: Mapped[str] = mapped_column(String(200), nullable=False)
    estado: Mapped[EstadoEstructura] = mapped_column(
        SAEnum(
            EstadoEstructura,
            name="estado_estructura",
            create_type=False,  # Creado por migración 005
            values_callable=lambda e: [m.value for m in e],
        ),
        nullable=False,
        default=EstadoEstructura.activa,
    )

    # Relación inversa hacia cohortes (solo para navegación, no cargada por defecto)
    cohortes: Mapped[list["Cohorte"]] = relationship(
        "Cohorte",
        back_populates="carrera",
        lazy="noload",
    )

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"<Carrera id={self.id} tenant={self.tenant_id} "
            f"codigo={self.codigo!r} estado={self.estado}>"
        )


# ---------------------------------------------------------------------------
# Materia (D3, D7)
# ---------------------------------------------------------------------------

class Materia(Base, TenantScopedBase):
    """
    Definición estática del catálogo único de materias del tenant (ADR-006/PA-01).

    Unicidad: (tenant_id, codigo) WHERE deleted_at IS NULL
    — garantizada por índice parcial ux_materia_tenant_codigo en migración 005.

    NO tiene carrera_id: la relación materia ↔ carrera se establece vía Dictado (C-07+).
    """
    __tablename__ = "materia"

    codigo: Mapped[str] = mapped_column(String(50), nullable=False)
    nombre: Mapped[str] = mapped_column(String(200), nullable=False)
    estado: Mapped[EstadoEstructura] = mapped_column(
        SAEnum(
            EstadoEstructura,
            name="estado_estructura",
            create_type=False,  # Compartido con carrera y cohorte
            values_callable=lambda e: [m.value for m in e],
        ),
        nullable=False,
        default=EstadoEstructura.activa,
    )

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"<Materia id={self.id} tenant={self.tenant_id} "
            f"codigo={self.codigo!r} estado={self.estado}>"
        )


# ---------------------------------------------------------------------------
# Cohorte (D3, D5, D10, PA-07)
# ---------------------------------------------------------------------------

class Cohorte(Base, TenantScopedBase):
    """
    Camada de ingreso de UNA carrera (PA-07).

    FK obligatoria: carrera_id → carrera.id RESTRICT.
    Unicidad: (tenant_id, carrera_id, nombre) WHERE deleted_at IS NULL
    — garantizada por índice parcial ux_cohorte_tenant_carrera_nombre en migración 005.

    Cohorte abierta: estado=activa AND vig_hasta IS NULL.
    """
    __tablename__ = "cohorte"

    carrera_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("carrera.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    nombre: Mapped[str] = mapped_column(String(100), nullable=False)
    anio: Mapped[int] = mapped_column(Integer, nullable=False)
    vig_desde: Mapped[date] = mapped_column(Date, nullable=False)
    vig_hasta: Mapped[Optional[date]] = mapped_column(Date, nullable=True, default=None)
    estado: Mapped[EstadoEstructura] = mapped_column(
        SAEnum(
            EstadoEstructura,
            name="estado_estructura",
            create_type=False,  # Compartido con carrera y materia
            values_callable=lambda e: [m.value for m in e],
        ),
        nullable=False,
        default=EstadoEstructura.activa,
    )

    # Relación hacia Carrera
    carrera: Mapped["Carrera"] = relationship(
        "Carrera",
        back_populates="cohortes",
        lazy="noload",
    )

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"<Cohorte id={self.id} tenant={self.tenant_id} "
            f"carrera={self.carrera_id} nombre={self.nombre!r} estado={self.estado}>"
        )
