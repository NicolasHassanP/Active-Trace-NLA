"""
Modelos de mensajería interna para C-20.

D4 — Tres tablas: hilos_mensaje, mensajes, hilo_participantes.
D5 — Leído = last_read_at por participante (granularidad por hilo).
D6 — Módulo independiente de comunicaciones (sin cola, sin estados de envío).
D7 — Remitente SIEMPRE desde el JWT; participación desde hilo_participantes.

Hilos estrictamente 1:1 en esta iteración (OQ-3 cerrada).
El modelo soporta grupal en el futuro sin cambio de schema.

tenant_id en las tres tablas (regla multi-tenancy #9).
soft delete en HiloMensaje y Mensaje (regla #13).
snake_case; ≤500 LOC. __repr__ NUNCA expone PII ni cuerpo del mensaje.
"""
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.mixins import TenantScopedBase


# ---------------------------------------------------------------------------
# HiloMensaje — conversación entre dos usuarios (1:1 en esta iteración)
# ---------------------------------------------------------------------------

class HiloMensaje(Base, TenantScopedBase):
    """
    Contenedor de una conversación interna entre usuarios del sistema.

    En esta iteración: estrictamente 1:1 (validado en el service).
    El modelo soporta grupal en el futuro sin cambio de schema.

    tenant_id: FK → tenants.id (multi-tenancy row-level).
    deleted_at: soft delete (auditoría append-only).
    """
    __tablename__ = "hilos_mensaje"

    asunto: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Relaciones (lazy noload — evitar N+1)
    mensajes: Mapped[list["Mensaje"]] = relationship(
        "Mensaje",
        back_populates="hilo",
        foreign_keys="[Mensaje.hilo_id]",
        lazy="noload",
    )
    participantes: Mapped[list["HiloParticipante"]] = relationship(
        "HiloParticipante",
        back_populates="hilo",
        foreign_keys="[HiloParticipante.hilo_id]",
        lazy="noload",
    )

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"<HiloMensaje id={self.id} tenant={self.tenant_id}>"
        )


# ---------------------------------------------------------------------------
# Mensaje — mensaje dentro de un hilo
# ---------------------------------------------------------------------------

class Mensaje(Base, TenantScopedBase):
    """
    Mensaje dentro de un HiloMensaje.

    remitente_id: FK → usuario.id (RESTRICT) — el remitente SIEMPRE
    se atribuye desde el JWT en el service; nunca de la petición.
    tenant_id: FK → tenants.id (row-level isolation).
    deleted_at: soft delete (historial completo para auditoría).

    asunto y cuerpo son obligatorios.
    """
    __tablename__ = "mensajes"

    hilo_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("hilos_mensaje.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    remitente_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("usuario.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    asunto: Mapped[str] = mapped_column(String(255), nullable=False)
    cuerpo: Mapped[str] = mapped_column(Text, nullable=False)

    # Relación inversa al hilo
    hilo: Mapped["HiloMensaje"] = relationship(
        "HiloMensaje",
        back_populates="mensajes",
        foreign_keys=[hilo_id],
        lazy="noload",
    )

    def __repr__(self) -> str:  # pragma: no cover
        # NUNCA expone el cuerpo del mensaje
        return (
            f"<Mensaje id={self.id} hilo={self.hilo_id} "
            f"remitente={self.remitente_id}>"
        )


# ---------------------------------------------------------------------------
# HiloParticipante — participación de un usuario en un hilo + estado de leído
# ---------------------------------------------------------------------------

class HiloParticipante(Base):
    """
    Participación de un usuario en un HiloMensaje.

    Registra el estado de leído por hilo + participante mediante last_read_at.
    no-leídos = mensajes con created_at > last_read_at (D5).

    No hereda TenantScopedBase (no tiene deleted_at — la participación es
    permanente; soft-delete del hilo la cubre). Sí tiene tenant_id para
    filtrado eficiente.
    """
    __tablename__ = "hilo_participantes"

    # Composite PK: (hilo_id, usuario_id)
    hilo_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("hilos_mensaje.id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
    )
    usuario_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("usuario.id", ondelete="RESTRICT"),
        primary_key=True,
        nullable=False,
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    # Estado de leído: None = nunca abrió el hilo
    last_read_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=None,
    )

    # Relación inversa al hilo
    hilo: Mapped["HiloMensaje"] = relationship(
        "HiloMensaje",
        back_populates="participantes",
        foreign_keys=[hilo_id],
        lazy="noload",
    )

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"<HiloParticipante hilo={self.hilo_id} usuario={self.usuario_id} "
            f"tenant={self.tenant_id}>"
        )
