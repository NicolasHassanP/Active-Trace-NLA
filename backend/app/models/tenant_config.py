"""
Modelo TenantConfig para C-12 comunicaciones-cola-worker.

Design decisions:
    D6 — Tabla tenant_config: clave/valor por tenant.
         UNIQUE (tenant_id, clave) WHERE deleted_at IS NULL (en migración 009).
    D7 — TenantScopedBase (soft-delete + timestamps).
    D8 — Llave principal de uso: 'aprobacion_comunicacion_requerida' (bool como string).

snake_case; ≤500 LOC.
"""
from sqlalchemy import Index, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.mixins import TenantScopedBase


# ---------------------------------------------------------------------------
# TenantConfig — configuración clave/valor por tenant (D6)
# ---------------------------------------------------------------------------

class TenantConfig(Base, TenantScopedBase):
    """
    Configuración clave/valor por tenant.

    Unicidad: UNIQUE (tenant_id, clave) WHERE deleted_at IS NULL
    — garantizada por índice parcial en migración 009.

    Valores se almacenan como TEXT; el repositorio los castea al tipo apropiado.
    Ejemplo: clave='aprobacion_comunicacion_requerida', valor='true'/'false'.
    """
    __tablename__ = "tenant_config"
    __table_args__ = (
        # Partial unique enforced at DB via migration 009; replicated here
        # so create_all in tests also creates the constraint.
        # The migration uses a WHERE deleted_at IS NULL partial index, but
        # SQLAlchemy create_all cannot create partial indexes — so we use a
        # full unique constraint for test schema compatibility. Production uses
        # the partial index from the migration.
        UniqueConstraint("tenant_id", "clave", name="uq_tenant_config_tenant_clave_full"),
    )

    clave: Mapped[str] = mapped_column(Text, nullable=False)
    valor: Mapped[str] = mapped_column(Text, nullable=False)

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"<TenantConfig id={self.id} tenant={self.tenant_id} "
            f"clave={self.clave!r}>"
        )
