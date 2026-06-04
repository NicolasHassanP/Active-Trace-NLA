"""
Modelos Aviso y AcknowledgmentAviso para C-15 avisos-y-acknowledgment.

Design decisions:
    D1  — Dos tablas: aviso + acknowledgment_aviso, tenant-scoped, soft-delete, UUID PK.
    D2  — Enums: aviso_alcance (Global|PorMateria|PorCohorte|PorRol),
                  aviso_severidad (Info|Advertencia|Critico). create_type=False.
    D6  — Índice parcial único uq_ack_aviso_usuario en migración 013.
    OQ-2 — rol_destino: String nullable (un único rol por aviso, nullable=Global).
    OQ-3 — Sin counter de vistas; solo ack explícito.

snake_case; ≤500 LOC.
"""
import enum
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, Enum as SAEnum, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.mixins import TenantScopedBase


# ---------------------------------------------------------------------------
# AvisoAlcance — enum de audiencia (D2)
# ---------------------------------------------------------------------------

class AvisoAlcance(str, enum.Enum):
    """
    Audiencia destino del aviso.

    Global    — todos los usuarios del tenant.
    PorMateria — usuarios con asignación a la materia indicada.
    PorCohorte — usuarios con asignación a la cohorte indicada.
    PorRol     — usuarios con el rol indicado en rol_destino.
    """
    Global = "Global"
    PorMateria = "PorMateria"
    PorCohorte = "PorCohorte"
    PorRol = "PorRol"


# ---------------------------------------------------------------------------
# AvisoSeveridad — enum de urgencia (D2)
# ---------------------------------------------------------------------------

class AvisoSeveridad(str, enum.Enum):
    """
    Nivel de urgencia / presentación del aviso.

    Info       — informativo, sin urgencia.
    Advertencia — requiere atención del destinatario.
    Critico    — urgente, aparece destacado.
    """
    Info = "Info"
    Advertencia = "Advertencia"
    Critico = "Critico"


# ---------------------------------------------------------------------------
# Aviso (D1)
# ---------------------------------------------------------------------------

class Aviso(Base, TenantScopedBase):
    """
    Tablero de avisos del tenant.

    Unicidad: no hay restricción única natural (mismo título/alcance puede
    publicarse varias veces en ventanas distintas).
    Soft-delete: deleted_at set via repo.delete().

    Columnas de audiencia (nullables según alcance):
        materia_id  — requerido cuando alcance=PorMateria.
        cohorte_id  — requerido cuando alcance=PorCohorte.
        rol_destino — requerido cuando alcance=PorRol (String, no enum FK).

    Ventana de validez: inicio_en .. fin_en (inclusive, UTC).
    orden: menor = mayor prioridad (ascendente en la query).
    """
    __tablename__ = "aviso"

    # --- Audiencia ---
    alcance: Mapped[AvisoAlcance] = mapped_column(
        SAEnum(
            AvisoAlcance,
            name="aviso_alcance",
            create_type=False,
            values_callable=lambda e: [m.value for m in e],
        ),
        nullable=False,
    )
    materia_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("materia.id", ondelete="RESTRICT"),
        nullable=True,
        default=None,
        index=True,
    )
    cohorte_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("cohorte.id", ondelete="RESTRICT"),
        nullable=True,
        default=None,
        index=True,
    )
    # rol_destino: String — references role catalog by name (e.g. "COORDINADOR")
    rol_destino: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        default=None,
    )

    # --- Contenido ---
    severidad: Mapped[AvisoSeveridad] = mapped_column(
        SAEnum(
            AvisoSeveridad,
            name="aviso_severidad",
            create_type=False,
            values_callable=lambda e: [m.value for m in e],
        ),
        nullable=False,
        default=AvisoSeveridad.Info,
    )
    titulo: Mapped[str] = mapped_column(String(200), nullable=False)
    cuerpo: Mapped[str] = mapped_column(String(4000), nullable=False)

    # --- Ventana de validez (UTC timestamps) ---
    inicio_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    fin_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    # --- Configuración ---
    orden: Mapped[int] = mapped_column(Integer, nullable=False, default=100)
    activo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    requiere_ack: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # --- Relación inversa a acknowledgments ---
    acknowledgments: Mapped[list["AcknowledgmentAviso"]] = relationship(
        "AcknowledgmentAviso",
        back_populates="aviso",
        lazy="noload",
    )

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"<Aviso id={self.id} tenant={self.tenant_id} "
            f"alcance={self.alcance} titulo={self.titulo!r}>"
        )


# ---------------------------------------------------------------------------
# AcknowledgmentAviso (D1, D6)
# ---------------------------------------------------------------------------

class AcknowledgmentAviso(Base, TenantScopedBase):
    """
    Confirmación de lectura de un aviso por un usuario.

    Idempotencia: índice parcial único uq_ack_aviso_usuario en migración 013
    sobre (tenant_id, aviso_id, usuario_id) WHERE deleted_at IS NULL.
    Soft-delete: ack borrado no cuenta (excluded by deleted_at IS NULL).

    usuario_id: FK a usuario.id — SIEMPRE del JWT, nunca del request body.
    confirmado_at: timestamp UTC de la confirmación.
    """
    __tablename__ = "acknowledgment_aviso"

    aviso_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("aviso.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    usuario_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("usuario.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    confirmado_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    # --- Relación hacia Aviso ---
    aviso: Mapped["Aviso"] = relationship(
        "Aviso",
        back_populates="acknowledgments",
        lazy="noload",
    )

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"<AcknowledgmentAviso id={self.id} tenant={self.tenant_id} "
            f"aviso={self.aviso_id} usuario={self.usuario_id}>"
        )
