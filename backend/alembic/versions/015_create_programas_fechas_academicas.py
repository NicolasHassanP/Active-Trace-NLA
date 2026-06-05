"""015 — programas y fechas académicas

Revision ID: 015
Revises: 014
Create Date: 2026-06-05

C-17: Programas y Fechas Académicas (F5.1–F5.4).

Design decisions:
    D8  — revision="015", down_revision="014".
    D8  — Extend audit_action: PROGRAMA_GESTIONAR, FECHA_ACADEMICA_GESTIONAR (idempotente).
    D2  — NO crear enum nuevo — reutilizar 'evaluacion_tipo' existente (migración 012).
    D1  — Tablas: programa_materia, fecha_academica (tenant-scoped, soft-delete).
    D4  — FKs RESTRICT: materia, carrera, cohorte.
    D5  — Índices parciales únicos WHERE deleted_at IS NULL.
    D8  — downgrade: DROP TABLE programa_materia, fecha_academica.
          Los valores de audit_action NO son reversibles en PostgreSQL.
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers
revision = "015"
down_revision = "014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- D8: Extend audit_action enum idempotently ---
    for action in ("PROGRAMA_GESTIONAR", "FECHA_ACADEMICA_GESTIONAR"):
        op.execute(
            f"DO $$ BEGIN "
            f"  ALTER TYPE audit_action ADD VALUE '{action}'; "
            f"EXCEPTION WHEN duplicate_object THEN NULL; "
            f"END $$;"
        )

    # --- D1/D4: Create table programa_materia ---
    op.execute("""
        CREATE TABLE IF NOT EXISTS programa_materia (
            id                  UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id           UUID        NOT NULL REFERENCES tenants(id) ON DELETE RESTRICT,
            materia_id          UUID        NOT NULL REFERENCES materia(id) ON DELETE RESTRICT,
            carrera_id          UUID        NOT NULL REFERENCES carrera(id) ON DELETE RESTRICT,
            cohorte_id          UUID        NOT NULL REFERENCES cohorte(id) ON DELETE RESTRICT,
            titulo              TEXT        NOT NULL,
            referencia_archivo  TEXT        NOT NULL,
            cargado_at          TIMESTAMPTZ NULL,
            created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
            deleted_at          TIMESTAMPTZ NULL
        )
    """)

    # --- D1/D4: Create table fecha_academica (uses existing evaluacion_tipo enum) ---
    op.execute("""
        CREATE TABLE IF NOT EXISTS fecha_academica (
            id          UUID            PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id   UUID            NOT NULL REFERENCES tenants(id) ON DELETE RESTRICT,
            materia_id  UUID            NOT NULL REFERENCES materia(id) ON DELETE RESTRICT,
            cohorte_id  UUID            NOT NULL REFERENCES cohorte(id) ON DELETE RESTRICT,
            tipo        evaluacion_tipo NOT NULL,
            numero      INTEGER         NOT NULL,
            periodo     TEXT            NOT NULL,
            fecha       DATE            NOT NULL,
            titulo      TEXT            NOT NULL,
            created_at  TIMESTAMPTZ     NOT NULL DEFAULT now(),
            updated_at  TIMESTAMPTZ     NOT NULL DEFAULT now(),
            deleted_at  TIMESTAMPTZ     NULL
        )
    """)

    # --- Standard indexes (hot paths) ---
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_programa_materia_tenant_id "
        "ON programa_materia (tenant_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_programa_materia_materia_id "
        "ON programa_materia (tenant_id, materia_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_programa_materia_cohorte_id "
        "ON programa_materia (tenant_id, cohorte_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_fecha_academica_tenant_id "
        "ON fecha_academica (tenant_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_fecha_academica_materia_cohorte "
        "ON fecha_academica (tenant_id, materia_id, cohorte_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_fecha_academica_fecha "
        "ON fecha_academica (tenant_id, fecha)"
    )

    # --- D5: Partial unique indexes (WHERE deleted_at IS NULL) ---
    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS ux_programa_materia_tenant_combo "
        "ON programa_materia (tenant_id, materia_id, carrera_id, cohorte_id) "
        "WHERE deleted_at IS NULL"
    )
    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS ux_fecha_academica_tenant_combo "
        "ON fecha_academica (tenant_id, materia_id, cohorte_id, tipo, numero, periodo) "
        "WHERE deleted_at IS NULL"
    )


def downgrade() -> None:
    # D5: Drop partial unique indexes first
    op.execute("DROP INDEX IF EXISTS ux_fecha_academica_tenant_combo")
    op.execute("DROP INDEX IF EXISTS ux_programa_materia_tenant_combo")

    # Drop standard indexes
    op.execute("DROP INDEX IF EXISTS ix_fecha_academica_fecha")
    op.execute("DROP INDEX IF EXISTS ix_fecha_academica_materia_cohorte")
    op.execute("DROP INDEX IF EXISTS ix_fecha_academica_tenant_id")
    op.execute("DROP INDEX IF EXISTS ix_programa_materia_cohorte_id")
    op.execute("DROP INDEX IF EXISTS ix_programa_materia_materia_id")
    op.execute("DROP INDEX IF EXISTS ix_programa_materia_tenant_id")

    # D8: Drop tables
    op.execute("DROP TABLE IF EXISTS fecha_academica CASCADE")
    op.execute("DROP TABLE IF EXISTS programa_materia CASCADE")

    # Note: PROGRAMA_GESTIONAR and FECHA_ACADEMICA_GESTIONAR added to audit_action
    # are NOT reversible (PostgreSQL does not support removing enum values).
    # These values remain in the audit_action type after downgrade — inocuous.
