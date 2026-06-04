"""
Modelos VersionPadron y EntradaPadron para C-09 padrón ingesta.

Design decisions:
    D2 — activa como cursor de versión activa única por (tenant_id, materia_id, cohorte_id).
    D3 — EntradaPadron.email_encrypted cifrado con EncryptedString (AES-256-GCM).
         Sin blind index (no hay caso de uso de búsqueda por email en C-09).
    D4 — usuario_id nullable (FK→usuario, ON DELETE SET NULL): alumno sin cuenta es válido.
    D9 — Patrón de archivo igual a C-07 (models/padron.py).

__repr__ NUNCA expone email_encrypted (PII).
snake_case; ≤500 LOC.
"""
import uuid
from datetime import datetime
from typing import List, Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Text, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.core.security.crypto import EncryptedString
from app.models.mixins import TenantScopedBase


# ---------------------------------------------------------------------------
# VersionPadron — versión de padrón por materia×cohorte (D2)
# ---------------------------------------------------------------------------

class VersionPadron(Base, TenantScopedBase):
    """
    Versión del padrón de alumnos para una materia×cohorte específica.

    Una sola versión puede estar activa (activa=True) por (tenant_id, materia_id, cohorte_id).
    La activación de una nueva versión SIEMPRE desactiva la anterior en la misma transacción.
    El historial se conserva (versiones inactivas no se borran físicamente — soft delete).

    cargado_por: nullable (ON DELETE SET NULL) — si el usuario se elimina, la referencia
                 queda en None pero la versión permanece para auditoría.
    """
    __tablename__ = "version_padron"

    # --- Contexto materia×cohorte (NOT NULL, RESTRICT) ---
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

    # --- Auditoría de carga ---
    cargado_por: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("usuario.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    cargado_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # --- Cursor de versión activa (D2) ---
    activa: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )

    # --- Relación inversa hacia entradas ---
    entradas: Mapped[List["EntradaPadron"]] = relationship(
        "EntradaPadron",
        back_populates="version",
        lazy="noload",
    )

    def __repr__(self) -> str:  # pragma: no cover
        # NUNCA incluye email_encrypted ni PII
        return (
            f"<VersionPadron id={self.id} tenant={self.tenant_id} "
            f"materia={self.materia_id} cohorte={self.cohorte_id} activa={self.activa}>"
        )


# ---------------------------------------------------------------------------
# EntradaPadron — fila del padrón de alumnos (D3, D4)
# ---------------------------------------------------------------------------

class EntradaPadron(Base, TenantScopedBase):
    """
    Entrada individual del padrón: un alumno en una versión de padrón.

    email_encrypted: PII cifrada con EncryptedString (AES-256-GCM). Sin blind index
    porque no hay caso de uso de búsqueda exacta por email en C-09.

    usuario_id: nullable — un alumno puede existir en el padrón antes de tener cuenta.
    ON DELETE SET NULL: si el usuario se elimina, la referencia queda en None pero
    la entrada permanece para historial.
    """
    __tablename__ = "entrada_padron"

    # --- FK a la versión (NOT NULL RESTRICT) ---
    version_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("version_padron.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    # --- FK nullable al usuario (D4) ---
    usuario_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("usuario.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # --- Datos del alumno (no cifrados, para búsqueda) ---
    nombre: Mapped[str] = mapped_column(Text, nullable=False)
    apellidos: Mapped[str] = mapped_column(Text, nullable=False)

    # --- PII cifrada (D3) --- AES-256-GCM via EncryptedString
    email_encrypted: Mapped[str] = mapped_column(EncryptedString, nullable=False)

    # --- Contexto académico (opcional) ---
    comision: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    regional: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # --- Relación inversa a la versión ---
    version: Mapped["VersionPadron"] = relationship(
        "VersionPadron",
        back_populates="entradas",
        lazy="noload",
    )

    def __repr__(self) -> str:  # pragma: no cover
        # NUNCA incluye email_encrypted (PII)
        return (
            f"<EntradaPadron id={self.id} tenant={self.tenant_id} "
            f"version={self.version_id} nombre={self.nombre!r}>"
        )
