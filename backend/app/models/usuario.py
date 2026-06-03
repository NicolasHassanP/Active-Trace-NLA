"""
Modelos Usuario y Asignacion para C-07 usuarios-y-asignaciones.

Design decisions:
    D2 — PII cifrada con EncryptedString (AES-256-GCM, app-layer).
    D3 — Unicidad email via blind index email_hash (HMAC-SHA256).
    D4 — estado_vigencia DERIVADO, nunca columna (ver helper en vigencia.py).
    D5 — responsable_id self-FK a usuario.id RESTRICT nullable.
    D6 — Modelos sobre TenantScopedBase (soft-delete).
    D7 — Enum rol_asignacion (PROFESOR, TUTOR, COORDINADOR, NEXO, ADMIN, FINANZAS).
    D9 — auth_identity_id FK nullable → auth_identities.id ON DELETE SET NULL.
    D11 — Set §E4 completo: PII cifrada + negocio + auth_identity_id.

snake_case; ≤500 LOC. __repr__ NUNCA expone PII en texto plano.
"""
import enum
import uuid
from datetime import date
from typing import List, Optional

from sqlalchemy import Boolean, Date, Enum as SAEnum, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.core.security.crypto import EncryptedString
from app.models.mixins import TenantScopedBase


# ---------------------------------------------------------------------------
# RolAsignacion — enum del equipo docente/administrativo (D7)
# ALUMNO excluido: la condición de alumno se modela en el padrón (C-09).
# ---------------------------------------------------------------------------

class RolAsignacion(str, enum.Enum):
    """
    Roles de asignación (equipo docente/administrativo).

    Excluye ALUMNO: esa condición se modela en el padrón (C-09).
    Enum constante del sistema — no es per-tenant.
    """
    PROFESOR = "PROFESOR"
    TUTOR = "TUTOR"
    COORDINADOR = "COORDINADOR"
    NEXO = "NEXO"
    ADMIN = "ADMIN"
    FINANZAS = "FINANZAS"


# ---------------------------------------------------------------------------
# UsuarioEstado — ciclo de vida del usuario de negocio
# ---------------------------------------------------------------------------

class UsuarioEstado(str, enum.Enum):
    """Estado del usuario de negocio."""
    activo = "activo"
    inactivo = "inactivo"


# ---------------------------------------------------------------------------
# Usuario — identidad de negocio con PII cifrada (D2, D3, D6, D9, D11)
# ---------------------------------------------------------------------------

class Usuario(Base, TenantScopedBase):
    """
    Identidad de negocio del tenant con PII cifrada en reposo.

    PII cifrada (EncryptedString, AES-256-GCM, no determinístico):
        email_encrypted, dni, cuil, cbu, alias_cbu.
    Blind index determinístico: email_hash = HMAC-SHA256(SECRET_KEY, normalize(email)).
    Unicidad: (tenant_id, email_hash) WHERE deleted_at IS NULL
    — garantizada por índice parcial ux_usuario_tenant_email_hash en migración 006.

    auth_identity_id: nullable FK → auth_identities.id ON DELETE SET NULL (D9).
    estado_vigencia: NO es columna — se calcula con el helper en vigencia.py.
    __repr__: NUNCA expone PII en texto plano.
    """
    __tablename__ = "usuario"

    # --- PII cifrada (D2) ---
    email_encrypted: Mapped[str] = mapped_column(EncryptedString, nullable=False)
    email_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    dni: Mapped[Optional[str]] = mapped_column(EncryptedString, nullable=True)
    cuil: Mapped[Optional[str]] = mapped_column(EncryptedString, nullable=True)
    cbu: Mapped[Optional[str]] = mapped_column(EncryptedString, nullable=True)
    alias_cbu: Mapped[Optional[str]] = mapped_column(EncryptedString, nullable=True)

    # --- Identidad / negocio (§E4 completo) ---
    nombre: Mapped[str] = mapped_column(String(200), nullable=False)
    apellidos: Mapped[str] = mapped_column(String(200), nullable=False)
    legajo: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    legajo_profesional: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    banco: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    regional: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    facturador: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    estado: Mapped[UsuarioEstado] = mapped_column(
        SAEnum(
            UsuarioEstado,
            name="usuario_estado",
            create_type=False,  # Creado por migración 006
            values_callable=lambda e: [m.value for m in e],
        ),
        nullable=False,
        default=UsuarioEstado.activo,
    )

    # --- Reconciliación auth (D9) ---
    auth_identity_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("auth_identities.id", ondelete="SET NULL"),
        nullable=True,
        default=None,
        index=True,
    )

    # --- Relación inversa a asignaciones ---
    asignaciones: Mapped[List["Asignacion"]] = relationship(
        "Asignacion",
        back_populates="usuario",
        foreign_keys="[Asignacion.usuario_id]",
        lazy="noload",
    )

    def __repr__(self) -> str:  # pragma: no cover
        # NUNCA incluye PII (email, dni, cuil, cbu) en texto plano
        return (
            f"<Usuario id={self.id} tenant={self.tenant_id} "
            f"estado={self.estado}>"
        )


# ---------------------------------------------------------------------------
# Asignacion — eje de autorización contextual (D4, D5, D6, D7)
# ---------------------------------------------------------------------------

class Asignacion(Base, TenantScopedBase):
    """
    Asignación de un usuario a un rol con contexto opcional y ventana temporal.

    estado_vigencia: DERIVADO en runtime — NOT una columna.
        vigente := desde <= hoy AND (hasta IS NULL OR hasta >= hoy).
    responsable_id: self-FK → usuario.id RESTRICT nullable (D5).
    comisiones: JSONB lista de strings (grupos/comisiones asignadas).
    """
    __tablename__ = "asignacion"

    # --- FK obligatoria al usuario (NOT NULL RESTRICT) ---
    usuario_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("usuario.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    # --- Rol (NOT NULL) ---
    rol: Mapped[RolAsignacion] = mapped_column(
        SAEnum(
            RolAsignacion,
            name="rol_asignacion",
            create_type=False,  # Creado por migración 006
            values_callable=lambda e: [m.value for m in e],
        ),
        nullable=False,
    )

    # --- Contexto (nullable, FKs RESTRICT) ---
    materia_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("materia.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    carrera_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("carrera.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    cohorte_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("cohorte.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )

    # --- Comisiones (JSONB lista vacía por defecto) ---
    comisiones: Mapped[List[str]] = mapped_column(
        JSONB, nullable=False, default=list
    )

    # --- Responsable (self-FK a usuario, nullable RESTRICT) (D5) ---
    responsable_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("usuario.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )

    # --- Ventana temporal (D4) ---
    desde: Mapped[date] = mapped_column(Date, nullable=False)
    hasta: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    # --- Relaciones (lazy noload para evitar N+1) ---
    usuario: Mapped["Usuario"] = relationship(
        "Usuario",
        back_populates="asignaciones",
        foreign_keys=[usuario_id],
        lazy="noload",
    )
    responsable: Mapped[Optional["Usuario"]] = relationship(
        "Usuario",
        foreign_keys=[responsable_id],
        lazy="noload",
    )

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"<Asignacion id={self.id} tenant={self.tenant_id} "
            f"usuario={self.usuario_id} rol={self.rol} "
            f"desde={self.desde} hasta={self.hasta}>"
        )
