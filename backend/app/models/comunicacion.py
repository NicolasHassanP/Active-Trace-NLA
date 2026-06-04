"""
Modelo Comunicacion para C-12 comunicaciones-cola-worker.

Design decisions:
    D2 — destinatario cifrado con EncryptedString (AES-256-GCM, app-layer).
    D3 — estado enum ComunicacionEstado (DB enum comunicacion_estado).
    D5 — lote_id UUID para agrupación de envíos masivos.
    D6 — TenantScopedBase (soft-delete, timestamps).
    D7 — __repr__ NUNCA expone destinatario (PII) en texto plano.

snake_case; ≤500 LOC.
"""
import enum
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Enum as SAEnum, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.core.security.crypto import EncryptedString
from app.models.mixins import TenantScopedBase


# ---------------------------------------------------------------------------
# ComunicacionEstado — mirrored from comunicacion_estados.py for DB mapping
# ---------------------------------------------------------------------------

class ComunicacionEstado(str, enum.Enum):
    """
    Estados del ciclo de vida de una Comunicacion (espejo del enum en comunicacion_estados.py).

    El DB enum se llama 'comunicacion_estado' (creado en migración 009).
    Terminales (OQ-5): Error, Enviado, Cancelado — sin reintento.
    """
    Pendiente = "Pendiente"
    Enviando = "Enviando"
    Enviado = "Enviado"
    Error = "Error"
    Cancelado = "Cancelado"


# ---------------------------------------------------------------------------
# Comunicacion — mensaje saliente con destinatario cifrado (D2, D6, D7)
# ---------------------------------------------------------------------------

class Comunicacion(Base, TenantScopedBase):
    """
    Mensaje de comunicación saliente (email) con destinatario cifrado en reposo.

    PII cifrada (EncryptedString, AES-256-GCM, no determinístico):
        destinatario — dirección de email del receptor.

    lote_id: UUID que agrupa todos los mensajes de un mismo envío masivo.
    estado: enum comunicacion_estado (Pendiente/Enviando/Enviado/Error/Cancelado).
    enviado_por: FK nullable a usuario (quién encoló el mensaje).
    aprobado_por: FK nullable a usuario (quién aprobó el despacho).
    enviado_at: timestamp del envío efectivo (NULL hasta que el worker despacha).
    error_detalle: detalle del error si estado=Error (NULL en los demás estados).

    __repr__: NUNCA expone destinatario en texto plano.
    """
    __tablename__ = "comunicacion"

    # --- Destinatario (PII cifrada) ---
    destinatario: Mapped[str] = mapped_column(EncryptedString, nullable=False)

    # --- Contenido ---
    asunto: Mapped[str] = mapped_column(Text, nullable=False)
    cuerpo: Mapped[str] = mapped_column(Text, nullable=False)

    # --- Estado (DB enum) ---
    estado: Mapped[ComunicacionEstado] = mapped_column(
        SAEnum(
            ComunicacionEstado,
            name="comunicacion_estado",
            create_type=False,  # Creado por migración 009
            values_callable=lambda e: [m.value for m in e],
        ),
        nullable=False,
        default=ComunicacionEstado.Pendiente,
    )

    # --- Agrupación por lote ---
    lote_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        nullable=False,
        index=True,
    )

    # --- Atribución (FKs nullable RESTRICT → SET NULL) ---
    enviado_por: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("usuario.id", ondelete="SET NULL"),
        nullable=True,
        default=None,
    )
    aprobado_por: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("usuario.id", ondelete="SET NULL"),
        nullable=True,
        default=None,
    )

    # --- Timestamps de despacho / error ---
    enviado_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=None,
    )
    error_detalle: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        default=None,
    )

    def __repr__(self) -> str:  # pragma: no cover
        # NUNCA incluye el destinatario (PII) en texto plano
        return (
            f"<Comunicacion id={self.id} tenant={self.tenant_id} "
            f"estado={self.estado} lote={self.lote_id}>"
        )
