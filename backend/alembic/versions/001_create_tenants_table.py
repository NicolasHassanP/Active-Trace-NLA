"""001 — create tenants table

Revision ID: 001
Revises:
Create Date: 2026-06-02

C-02: Tenant root entity. Stores the lifecycle state of each institution.
One migration per schema change (ADR convention).
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Use raw SQL for full control (avoids SA DDL enum auto-creation edge cases)
    op.execute("""
        CREATE TYPE tenant_estado AS ENUM ('activo', 'inactivo')
    """)
    op.execute("""
        CREATE TABLE tenants (
            id          UUID        NOT NULL DEFAULT gen_random_uuid(),
            nombre      VARCHAR(256) NOT NULL,
            estado      tenant_estado NOT NULL,
            created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
            deleted_at  TIMESTAMPTZ,
            PRIMARY KEY (id)
        )
    """)
    op.create_index("ix_tenants_deleted_at", "tenants", ["deleted_at"])
    op.create_index("ix_tenants_estado", "tenants", ["estado"])


def downgrade() -> None:
    op.drop_index("ix_tenants_estado", table_name="tenants")
    op.drop_index("ix_tenants_deleted_at", table_name="tenants")
    op.drop_table("tenants")
    op.execute("DROP TYPE IF EXISTS tenant_estado")
