"""
Audit models — AuditAction enum and AuditEvent model.

C-05: Append-only audit log, tenant-scoped and immutable.

Design decisions:
    D2 — AuditEvent does NOT inherit TenantScopedBase (which has updated_at +
         deleted_at). Instead it composes only UUIDMixin + TenantMixin + its own
         created_at. The absence of updated_at/deleted_at makes mutation
         structurally impossible at the model layer.
    D3 — A DB trigger (migration 004) further enforces immutability by rejecting
         UPDATE and DELETE operations at the database layer (defense in depth).
    D4 — AuditAction is a closed enum versionined with the codebase; not a
         per-tenant table. Catalog is identical for all tenants.

snake_case throughout; ≤500 LOC.
"""
import enum
import uuid
from datetime import datetime
from typing import Any, Dict, Optional

from sqlalchemy import DateTime, Enum as SAEnum, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.mixins import TenantMixin, UUIDMixin


# ---------------------------------------------------------------------------
# AuditAction — closed catalog of audit event codes (RN-24, D4)
# ---------------------------------------------------------------------------

class AuditAction(str, enum.Enum):
    """
    Closed catalog of auditable action codes.

    Format: MODULO_ACCION (uppercase).
    Each change that introduces new auditable actions adds values here and
    adds an ALTER TYPE audit_action ADD VALUE migration.

    Initial catalog (OQ-5 resolved):
        IMPERSONACION_INICIO  — actor started an impersonation session.
        IMPERSONACION_FIN     — actor ended an impersonation session.
        AUDITORIA_CONSULTA    — user queried the audit log (OQ-2 resolved).

    Codes outside this catalog are REJECTED by AuditService.record().
    """
    IMPERSONACION_INICIO = "IMPERSONACION_INICIO"
    IMPERSONACION_FIN = "IMPERSONACION_FIN"
    AUDITORIA_CONSULTA = "AUDITORIA_CONSULTA"
    PADRON_CARGAR = "PADRON_CARGAR"
    CALIFICACIONES_IMPORTAR = "CALIFICACIONES_IMPORTAR"
    COMUNICACION_ENVIAR = "COMUNICACION_ENVIAR"
    EQUIPOS_ASIGNACION_MASIVA = "EQUIPOS_ASIGNACION_MASIVA"
    EQUIPOS_CLONAR = "EQUIPOS_CLONAR"
    EQUIPOS_VIGENCIA_GENERAL = "EQUIPOS_VIGENCIA_GENERAL"


# ---------------------------------------------------------------------------
# AuditResultado — outcome enum (OQ-1 resolved)
# ---------------------------------------------------------------------------

class AuditResultado(str, enum.Enum):
    """
    Outcome of the audited operation.

    ok      — operation succeeded.
    fail    — operation failed.
    partial — partial success (some records affected, some not).
    """
    ok = "ok"
    fail = "fail"
    partial = "partial"


# ---------------------------------------------------------------------------
# AuditEvent — append-only audit record (D2)
# ---------------------------------------------------------------------------

class AuditEvent(Base, UUIDMixin, TenantMixin):
    """
    Immutable audit event record.

    Composes UUIDMixin (id UUID PK) + TenantMixin (tenant_id FK) plus
    a dedicated created_at column.  Deliberately OMITS:
        - updated_at (TimestampMixin) — events cannot be updated.
        - deleted_at (SoftDeleteMixin) — events cannot be deleted.

    Structural immutability is reinforced at the DB layer by the trigger
    created in migration 004 (D3).

    Atribución (D5, RN-41):
        actor_user_id         — the real actor, always derived from the JWT.
        impersonated_user_id  — present only when acting under impersonation.
    """

    __tablename__ = "audit_event"

    # ---- attribution ---------------------------------------------------------

    actor_user_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        nullable=False,
        index=True,
    )
    impersonated_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        nullable=True,
        default=None,
    )

    # ---- action catalog & classification ------------------------------------

    accion: Mapped[AuditAction] = mapped_column(
        SAEnum(
            AuditAction,
            name="audit_action",
            create_type=False,  # Created by migration 004; do not auto-create
            values_callable=lambda e: [m.value for m in e],
        ),
        nullable=False,
    )
    modulo: Mapped[str] = mapped_column(String(100), nullable=False)
    entidad_tipo: Mapped[str] = mapped_column(String(100), nullable=False)

    # OQ-3 resolved: entidad_id is VARCHAR nullable
    entidad_id: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        default=None,
    )

    # ---- outcome -------------------------------------------------------------

    resultado: Mapped[AuditResultado] = mapped_column(
        SAEnum(
            AuditResultado,
            name="audit_resultado",
            create_type=False,  # Created by migration 004; do not auto-create
            values_callable=lambda e: [m.value for m in e],
        ),
        nullable=False,
    )
    registros_afectados: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        default=None,
    )

    # ---- request context (informative only, not identity) -------------------

    ip: Mapped[Optional[str]] = mapped_column(String(45), nullable=True, default=None)
    user_agent: Mapped[Optional[str]] = mapped_column(String(500), nullable=True, default=None)

    # ---- before/after state (JSONB, with PII redaction applied upstream) ----

    before: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=True,
        default=None,
    )
    after: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=True,
        default=None,
    )

    # ---- timestamp (NO updated_at, NO deleted_at — append-only D2) ----------

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"<AuditEvent id={self.id} tenant={self.tenant_id} "
            f"accion={self.accion} actor={self.actor_user_id}>"
        )
