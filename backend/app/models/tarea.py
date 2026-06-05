"""
Modelos Tarea y ComentarioTarea para C-16 tareas-internas.

Design decisions:
    D1  — Dos tablas: tarea + comentario_tarea, tenant-scoped, soft-delete, UUID PK.
    D2  — Enum tarea_estado (Pendiente|EnProgreso|Resuelta|Cancelada), create_type=False.
    D4  — contexto_id UUID NULL sin FK (referencia blanda polimórfica) + contexto_tipo VARCHAR(50).
          materia_id es FK explícita a materia.
    D5  — ComentarioTarea con flag es_sistema para comentarios generados por delegación.
    D11 — Relaciones lazy="noload" para evitar N+1 (alto uso).

snake_case; ≤500 LOC.
"""
import enum
import uuid
from typing import Optional

from sqlalchemy import Boolean, Enum as SAEnum, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.mixins import TenantScopedBase


# ---------------------------------------------------------------------------
# TareaEstado — enum de estados del workflow FL-05 (D2)
# ---------------------------------------------------------------------------

class TareaEstado(str, enum.Enum):
    """
    Estado del workflow de una tarea interna.

    Transitions enforced by the service layer (D3):
        Pendiente  → {EnProgreso, Resuelta, Cancelada}
        EnProgreso → {Pendiente, Resuelta, Cancelada}
        Resuelta   → {EnProgreso} (reopen, FL-05 §7)
        Cancelada  → {} (terminal-final)

    create_type=False: the enum is created by migration 014.
    """
    Pendiente = "Pendiente"
    EnProgreso = "EnProgreso"
    Resuelta = "Resuelta"
    Cancelada = "Cancelada"


# ---------------------------------------------------------------------------
# Tarea (D1)
# ---------------------------------------------------------------------------

class Tarea(Base, TenantScopedBase):
    """
    Tarea interna del tenant (FL-05, F8.1–F8.3).

    Multi-tenancy: tenant_id (from TenantScopedBase) on every row.
    Soft-delete: deleted_at (from TenantScopedBase).
    UUID PK: id (from TenantScopedBase).

    Assignee fields:
        asignado_a  — the docente who resolves the task (FK usuario.id).
        asignado_por — the actor who assigned/last-delegated (FK usuario.id; identity from JWT).

    Polymorphic soft reference (D4):
        contexto_id   — UUID nullable, no FK (polymorphic reference).
        contexto_tipo — VARCHAR(50) nullable, discriminator (e.g. "Encuentro").
        Both null OR both present; validated in schema layer.

    materia_id — explicit nullable FK to materia (used in admin filter F8.3).

    estado — maps to tarea_estado DB enum (create_type=False).
    Initial state is always Pendiente; set by the service.
    """
    __tablename__ = "tarea"

    # --- Assignee fields ---
    asignado_a: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("usuario.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    asignado_por: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("usuario.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    # --- Content ---
    descripcion: Mapped[str] = mapped_column(Text, nullable=False)

    # --- Estado workflow (D2) ---
    estado: Mapped[TareaEstado] = mapped_column(
        SAEnum(
            TareaEstado,
            name="tarea_estado",
            create_type=False,
            values_callable=lambda e: [m.value for m in e],
        ),
        nullable=False,
    )

    # --- Optional materia FK (D4, explicit) ---
    materia_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("materia.id", ondelete="RESTRICT"),
        nullable=True,
        default=None,
        index=True,
    )

    # --- Polymorphic soft reference (D4) ---
    # contexto_id: UUID nullable, NO FK constraint (soft reference)
    contexto_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        nullable=True,
        default=None,
    )
    # contexto_tipo: discriminator (e.g. "Encuentro", "Coloquio", "Alumno")
    contexto_tipo: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        default=None,
    )

    # --- Relationships (D11: lazy="noload" for performance) ---
    comentarios: Mapped[list["ComentarioTarea"]] = relationship(
        "ComentarioTarea",
        back_populates="tarea",
        lazy="noload",
    )

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"<Tarea id={self.id} tenant={self.tenant_id} "
            f"estado={self.estado} asignado_a={self.asignado_a}>"
        )


# ---------------------------------------------------------------------------
# ComentarioTarea (D1, D5)
# ---------------------------------------------------------------------------

class ComentarioTarea(Base, TenantScopedBase):
    """
    Comentario en el hilo de una tarea.

    Append-style (soft-delete only). tarea_id FK to tarea.id.
    autor_id FK to usuario.id — ALWAYS from JWT, never from body.
    es_sistema: True for system-generated comments (e.g. delegation events).
    cuerpo: text content of the comment.

    lazy="noload" on relationship (D11).
    """
    __tablename__ = "comentario_tarea"

    tarea_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("tarea.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    autor_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("usuario.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    cuerpo: Mapped[str] = mapped_column(Text, nullable=False)
    es_sistema: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )

    # --- Relationship hacia Tarea ---
    tarea: Mapped["Tarea"] = relationship(
        "Tarea",
        back_populates="comentarios",
        lazy="noload",
    )

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"<ComentarioTarea id={self.id} tenant={self.tenant_id} "
            f"tarea={self.tarea_id} autor={self.autor_id} sistema={self.es_sistema}>"
        )
