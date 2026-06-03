"""
RBAC models — rol, permiso, rol_permiso.

C-04: Fine-grained RBAC catalog persisted as data, tenant-scoped.
Each institution can customize its role/permission matrix without affecting others.

Design decisions (design.md D2, D4, D7):
    - All three tables are tenant-scoped (inherit TenantScopedBase).
    - Unicidad por tenant: (tenant_id, nombre) en rol, (tenant_id, codigo) en permiso,
      (tenant_id, rol_id, permiso_id) en rol_permiso.
    - scope en rol_permiso modela alcance propio vs global por par rol×permiso.
    - Default scope = global; 'propio' restringe al endpoint a solo datos del propio usuario.
"""
import enum
import uuid
from typing import Optional

from sqlalchemy import Enum as SAEnum, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.mixins import TenantScopedBase


# ---------------------------------------------------------------------------
# PermisoScope — enum de alcance por par rol×permiso
# ---------------------------------------------------------------------------

class PermisoScope(str, enum.Enum):
    """
    Alcance efectivo del permiso en el par rol×permiso.

    global_ — el rol puede operar sobre todos los datos del tenant.
    propio   — el rol sólo puede operar sobre sus propios datos.
               El endpoint consumidor aplica el filtro row-level.

    NOTE: 'global' es palabra reservada en Python, se usa 'global_' en el enum.
    El valor en DB/seed es la cadena "global".
    """
    global_ = "global"
    propio = "propio"


# ---------------------------------------------------------------------------
# Rol — catálogo de roles por tenant
# ---------------------------------------------------------------------------

class Rol(Base, TenantScopedBase):
    """
    Rol de dominio, tenant-scoped y administrable.

    Unique constraint: (tenant_id, nombre) — el mismo nombre puede existir en
    distintos tenants, pero es único dentro de cada uno.
    Nombres semilla coindicen con los valores que el JWT transporta en `roles`:
    ALUMNO, TUTOR, PROFESOR, COORDINADOR, NEXO, ADMIN, FINANZAS.
    """
    __tablename__ = "rol"
    __table_args__ = (
        UniqueConstraint("tenant_id", "nombre", name="uq_rol_tenant_nombre"),
    )

    nombre: Mapped[str] = mapped_column(String(50), nullable=False)
    descripcion: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, default=None)

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Rol id={self.id} tenant={self.tenant_id} nombre={self.nombre!r}>"


# ---------------------------------------------------------------------------
# Permiso — catálogo de permisos modulo:accion por tenant
# ---------------------------------------------------------------------------

class Permiso(Base, TenantScopedBase):
    """
    Permiso de dominio expresado como 'modulo:accion', tenant-scoped.

    El campo `codigo` es la forma canónica usada en require_permission(...).
    Unique constraint: (tenant_id, codigo) — mismo código puede existir en
    distintos tenants; único dentro de cada uno.
    """
    __tablename__ = "permiso"
    __table_args__ = (
        UniqueConstraint("tenant_id", "codigo", name="uq_permiso_tenant_codigo"),
    )

    codigo: Mapped[str] = mapped_column(String(100), nullable=False)
    modulo: Mapped[str] = mapped_column(String(50), nullable=False)
    accion: Mapped[str] = mapped_column(String(50), nullable=False)
    descripcion: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, default=None)

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Permiso id={self.id} codigo={self.codigo!r}>"


# ---------------------------------------------------------------------------
# RolPermiso — matriz de unión rol × permiso con alcance
# ---------------------------------------------------------------------------

class RolPermiso(Base, TenantScopedBase):
    """
    Tabla de unión que materializa la matriz rol×permiso con su alcance.

    Unique constraint: (tenant_id, rol_id, permiso_id) — un rol puede tener
    cada permiso como máximo una vez por tenant (el alcance está en la fila).

    El campo `scope` determina si el rol accede a todos los datos (global) o
    sólo a sus propios (propio). El endpoint consumidor aplica la restricción
    row-level cuando scope == propio. Ver design.md D4.
    """
    __tablename__ = "rol_permiso"
    __table_args__ = (
        UniqueConstraint("tenant_id", "rol_id", "permiso_id", name="uq_rol_permiso"),
    )

    rol_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("rol.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    permiso_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("permiso.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    scope: Mapped[PermisoScope] = mapped_column(
        SAEnum(
            PermisoScope,
            name="permiso_scope",
            create_type=False,  # Created by migration 003; do not auto-create
            values_callable=lambda e: [m.value for m in e],
        ),
        nullable=False,
        default=PermisoScope.global_,
    )

    # Relationship to load Permiso eagerly when needed (used by RbacRepository)
    permiso: Mapped["Permiso"] = relationship("Permiso", lazy="raise")

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"<RolPermiso rol={self.rol_id} permiso={self.permiso_id} scope={self.scope}>"
        )
