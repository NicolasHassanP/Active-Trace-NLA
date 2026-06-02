# Models package — import all models here so Alembic can discover them.
from app.models.mixins import (  # noqa: F401
    SoftDeleteMixin,
    TenantMixin,
    TenantScopedBase,
    TimestampMixin,
    UUIDMixin,
)
from app.models.tenant import Tenant, TenantEstado  # noqa: F401
