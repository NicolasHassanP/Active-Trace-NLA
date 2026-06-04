"""
Modelos SQLAlchemy para C-13 encuentros-y-guardias.

Entidades:
    DiaSemana                — enum del día de la semana (DB enum 'dia_semana').
    InstanciaEncuentroEstado — enum de estado de instancia (DB enum 'instancia_encuentro_estado').
    GuardiaEstado            — enum de estado de guardia (DB enum 'guardia_estado').
    SlotEncuentro            — plantilla de encuentro (recurrente o único).
    InstanciaEncuentro       — evento concreto derivado del slot.
    Guardia                  — guardia de atención de un tutor.

Design decisions:
    D1  — Todos heredan TenantScopedBase (soft-delete, timestamps, tenant_id FK).
    D2  — Enums mapeados con create_type=False (migración 011 los crea).
    D3  — SlotEncuentro y InstanciaEncuentro son independientes (RN-14):
          slot_id en instancia es nullable con ON DELETE SET NULL.
    D4  — Guardia: asignacion_id resuelto desde el service layer (CurrentUser),
          nunca desde el body del request (regla dura #8).
    D5  — __repr__ muestra solo id + campos clave (sin PII).

snake_case; ≤500 LOC.
"""
import enum
import uuid
from datetime import date, datetime, time
from typing import Optional

from sqlalchemy import Date, DateTime, Enum as SAEnum, ForeignKey, Integer, String, Text, Time
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.mixins import TenantScopedBase


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class DiaSemana(str, enum.Enum):
    """Día de la semana. Mapeado al DB enum 'dia_semana' (migración 011)."""
    Lunes = "Lunes"
    Martes = "Martes"
    Miercoles = "Miércoles"
    Jueves = "Jueves"
    Viernes = "Viernes"
    Sabado = "Sábado"
    Domingo = "Domingo"


class InstanciaEncuentroEstado(str, enum.Enum):
    """Estado del ciclo de vida de una instancia de encuentro."""
    Programado = "Programado"
    Realizado = "Realizado"
    Cancelado = "Cancelado"


class GuardiaEstado(str, enum.Enum):
    """Estado del ciclo de vida de una guardia."""
    Pendiente = "Pendiente"
    Realizada = "Realizada"
    Cancelada = "Cancelada"


# ---------------------------------------------------------------------------
# SlotEncuentro — plantilla de encuentro
# ---------------------------------------------------------------------------

class SlotEncuentro(Base, TenantScopedBase):
    """
    Plantilla de encuentro: define el patrón recurrente o único.

    Dos modos excluyentes (RN-13):
        Recurrente: dia_semana + fecha_inicio + cant_semanas > 0
        Único:      fecha_unica (cant_semanas = 0)

    La validación de modo exclusivo ocurre en el service layer
    (EncuentroValidationError 422).
    """
    __tablename__ = "slot_encuentro"

    # --- Contexto ---
    asignacion_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("asignacion.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    materia_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("materia.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    # --- Contenido ---
    titulo: Mapped[str] = mapped_column(Text, nullable=False)
    hora: Mapped[time] = mapped_column(Time, nullable=False)

    # --- Modo recurrente ---
    dia_semana: Mapped[Optional[DiaSemana]] = mapped_column(
        SAEnum(
            DiaSemana,
            name="dia_semana",
            create_type=False,
            values_callable=lambda e: [m.value for m in e],
        ),
        nullable=True,
        default=None,
    )
    fecha_inicio: Mapped[Optional[date]] = mapped_column(Date, nullable=True, default=None)
    cant_semanas: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # --- Modo único ---
    fecha_unica: Mapped[Optional[date]] = mapped_column(Date, nullable=True, default=None)

    # --- Opcionales ---
    meet_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True, default=None)
    vig_desde: Mapped[Optional[date]] = mapped_column(Date, nullable=True, default=None)
    vig_hasta: Mapped[Optional[date]] = mapped_column(Date, nullable=True, default=None)

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"<SlotEncuentro id={self.id} tenant={self.tenant_id} "
            f"titulo={self.titulo!r} cant_semanas={self.cant_semanas}>"
        )


# ---------------------------------------------------------------------------
# InstanciaEncuentro — evento concreto
# ---------------------------------------------------------------------------

class InstanciaEncuentro(Base, TenantScopedBase):
    """
    Evento concreto derivado de un slot.

    Estado independiente del slot y de los demás hermanos (RN-14).
    slot_id es nullable con ON DELETE SET NULL: las instancias sobreviven
    al borrado del slot (para mantener el historial).
    """
    __tablename__ = "instancia_encuentro"

    # --- Origen (nullable: independencia D3) ---
    slot_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("slot_encuentro.id", ondelete="SET NULL"),
        nullable=True,
        default=None,
        index=True,
    )
    materia_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("materia.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    # --- Datos del evento ---
    fecha: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    hora: Mapped[time] = mapped_column(Time, nullable=False)
    titulo: Mapped[str] = mapped_column(Text, nullable=False)

    # --- Estado ---
    estado: Mapped[InstanciaEncuentroEstado] = mapped_column(
        SAEnum(
            InstanciaEncuentroEstado,
            name="instancia_encuentro_estado",
            create_type=False,
            values_callable=lambda e: [m.value for m in e],
        ),
        nullable=False,
        default=InstanciaEncuentroEstado.Programado,
    )

    # --- URLs opcionales ---
    meet_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True, default=None)
    video_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True, default=None)

    # --- Notas ---
    comentario: Mapped[str] = mapped_column(Text, nullable=False, default="")

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"<InstanciaEncuentro id={self.id} tenant={self.tenant_id} "
            f"fecha={self.fecha} estado={self.estado}>"
        )


# ---------------------------------------------------------------------------
# Guardia — guardia de atención de tutor
# ---------------------------------------------------------------------------

class Guardia(Base, TenantScopedBase):
    """
    Guardia de atención registrada por un TUTOR.

    asignacion_id se resuelve en el service desde current_user — nunca del body.
    Tenant-scoped: tenant_id siempre desde el repo scope.
    """
    __tablename__ = "guardia"

    # --- Contexto del actor (D4 — resuelto por service, no por body) ---
    asignacion_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("asignacion.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
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
    )
    cohorte_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("cohorte.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    # --- Horario ---
    dia: Mapped[DiaSemana] = mapped_column(
        SAEnum(
            DiaSemana,
            name="dia_semana",
            create_type=False,
            values_callable=lambda e: [m.value for m in e],
        ),
        nullable=False,
    )
    horario: Mapped[str] = mapped_column(Text, nullable=False)

    # --- Estado ---
    estado: Mapped[GuardiaEstado] = mapped_column(
        SAEnum(
            GuardiaEstado,
            name="guardia_estado",
            create_type=False,
            values_callable=lambda e: [m.value for m in e],
        ),
        nullable=False,
        default=GuardiaEstado.Pendiente,
    )

    # --- Notas ---
    comentarios: Mapped[str] = mapped_column(Text, nullable=False, default="")

    # --- Timestamp de registro (business field, distinto de created_at del mixin) ---
    creada_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"<Guardia id={self.id} tenant={self.tenant_id} "
            f"dia={self.dia} estado={self.estado}>"
        )
