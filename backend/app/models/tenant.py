"""
Tenant model — root entity for multi-tenant isolation.

Design (D2 from design.md):
    Tenant = Base + UUIDMixin + TimestampMixin + SoftDeleteMixin
    (NO TenantMixin — Tenant is the root, not an entity scoped to a tenant)

Table: tenants
"""
import enum

from sqlalchemy import Enum as SAEnum, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.mixins import SoftDeleteMixin, TimestampMixin, UUIDMixin


class TenantEstado(str, enum.Enum):
    """Lifecycle state of a tenant."""
    ACTIVO = "activo"
    INACTIVO = "inactivo"


class Tenant(Base, UUIDMixin, TimestampMixin, SoftDeleteMixin):
    """
    Root entity: each institution (tenant) has exactly one Tenant record.

    Does NOT carry a tenant_id column — it IS the tenant.
    """
    __tablename__ = "tenants"

    nombre: Mapped[str] = mapped_column(String(256), nullable=False)
    estado: Mapped[TenantEstado] = mapped_column(
        SAEnum(
            TenantEstado,
            name="tenant_estado",
            create_type=False,  # Created by migration; do not auto-create
            values_callable=lambda e: [m.value for m in e],
        ),
        nullable=False,
        default=TenantEstado.ACTIVO,
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Tenant id={self.id} nombre={self.nombre!r} estado={self.estado}>"
