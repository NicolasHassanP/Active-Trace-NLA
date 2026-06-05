"""005 — create estructura academica tables

Revision ID: 005
Revises: 004
Create Date: 2026-06-03

C-06: Catálogo estructural académico del tenant.
Tres tablas: carrera, materia, cohorte.
Enum compartido: estado_estructura ('activa', 'inactiva').

Design decisions:
    D1 — revision="005", down_revision="004".
    D2 — Enum estado_estructura compartido por las tres entidades.
    D3 — TenantScopedBase: id, tenant_id, timestamps, deleted_at.
    D4 — Índices únicos parciales WHERE deleted_at IS NULL.
    D5 — cohorte.carrera_id FK RESTRICT NOT NULL.
    D8 — Seed idempotente del permiso 'estructura:gestionar' + grant a ADMIN.
    D10 — cohorte.anio INT NOT NULL, vig_desde DATE NOT NULL, vig_hasta DATE nullable.

CHECKPOINT RBAC: El seed del permiso 'estructura:gestionar' toca RBAC (CRÍTICO).
  El permiso ya fue sembrado en migración 003 para tenants existentes.
  Esta migración siembra para tenants creados después de 003 (idempotente).
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = "005"
down_revision = "004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- Create estado_estructura enum (idempotente, patrón DO/EXCEPTION de 003/004) ---
    op.execute(
        "DO $$ BEGIN "
        "  CREATE TYPE estado_estructura AS ENUM ('activa', 'inactiva'); "
        "EXCEPTION WHEN duplicate_object THEN NULL; "
        "END $$;"
    )

    # --- CREATE TABLE carrera ---
    op.execute("""
        CREATE TABLE carrera (
            id          UUID                NOT NULL DEFAULT gen_random_uuid(),
            tenant_id   UUID                NOT NULL REFERENCES tenants(id) ON DELETE RESTRICT,
            codigo      VARCHAR(50)         NOT NULL,
            nombre      VARCHAR(200)        NOT NULL,
            estado      estado_estructura   NOT NULL DEFAULT 'activa',
            created_at  TIMESTAMPTZ         NOT NULL DEFAULT now(),
            updated_at  TIMESTAMPTZ         NOT NULL DEFAULT now(),
            deleted_at  TIMESTAMPTZ,
            PRIMARY KEY (id)
        )
    """)
    op.create_index("ix_carrera_tenant_id",  "carrera", ["tenant_id"])
    op.create_index("ix_carrera_deleted_at", "carrera", ["deleted_at"])

    # --- CREATE TABLE materia ---
    op.execute("""
        CREATE TABLE materia (
            id          UUID                NOT NULL DEFAULT gen_random_uuid(),
            tenant_id   UUID                NOT NULL REFERENCES tenants(id) ON DELETE RESTRICT,
            codigo      VARCHAR(50)         NOT NULL,
            nombre      VARCHAR(200)        NOT NULL,
            estado      estado_estructura   NOT NULL DEFAULT 'activa',
            created_at  TIMESTAMPTZ         NOT NULL DEFAULT now(),
            updated_at  TIMESTAMPTZ         NOT NULL DEFAULT now(),
            deleted_at  TIMESTAMPTZ,
            PRIMARY KEY (id)
        )
    """)
    op.create_index("ix_materia_tenant_id",  "materia", ["tenant_id"])
    op.create_index("ix_materia_deleted_at", "materia", ["deleted_at"])

    # --- CREATE TABLE cohorte ---
    op.execute("""
        CREATE TABLE cohorte (
            id          UUID                NOT NULL DEFAULT gen_random_uuid(),
            tenant_id   UUID                NOT NULL REFERENCES tenants(id) ON DELETE RESTRICT,
            carrera_id  UUID                NOT NULL REFERENCES carrera(id) ON DELETE RESTRICT,
            nombre      VARCHAR(100)        NOT NULL,
            anio        INTEGER             NOT NULL,
            vig_desde   DATE                NOT NULL,
            vig_hasta   DATE,
            estado      estado_estructura   NOT NULL DEFAULT 'activa',
            created_at  TIMESTAMPTZ         NOT NULL DEFAULT now(),
            updated_at  TIMESTAMPTZ         NOT NULL DEFAULT now(),
            deleted_at  TIMESTAMPTZ,
            PRIMARY KEY (id)
        )
    """)
    op.create_index("ix_cohorte_tenant_id",       "cohorte", ["tenant_id"])
    op.create_index("ix_cohorte_deleted_at",       "cohorte", ["deleted_at"])
    op.create_index("ix_cohorte_tenant_carrera",   "cohorte", ["tenant_id", "carrera_id"])

    # --- Índices únicos parciales (D4) WHERE deleted_at IS NULL ---
    op.execute("""
        CREATE UNIQUE INDEX ux_carrera_tenant_codigo
        ON carrera (tenant_id, codigo)
        WHERE deleted_at IS NULL
    """)
    op.execute("""
        CREATE UNIQUE INDEX ux_materia_tenant_codigo
        ON materia (tenant_id, codigo)
        WHERE deleted_at IS NULL
    """)
    op.execute("""
        CREATE UNIQUE INDEX ux_cohorte_tenant_carrera_nombre
        ON cohorte (tenant_id, carrera_id, nombre)
        WHERE deleted_at IS NULL
    """)

    # --- Seed idempotente del permiso 'estructura:gestionar' + grant a ADMIN (D8/D10) ---
    # CHECKPOINT RBAC: alta del grant toca RBAC (CRÍTICO) — revisada por el usuario.
    # El permiso ya existe en 003 para tenants creados antes de esta migración.
    # Esta migración es idempotente: ON CONFLICT DO NOTHING en cada insert.
    conn = op.get_bind()
    tenants = conn.execute(
        sa.text("SELECT id FROM tenants WHERE deleted_at IS NULL")
    ).fetchall()
    for (tid,) in tenants:
        # Seed el permiso estructura:gestionar si no existe
        conn.execute(
            sa.text("""
                INSERT INTO permiso (id, tenant_id, codigo, modulo, accion, created_at, updated_at)
                VALUES (gen_random_uuid(), :tid, 'estructura:gestionar', 'estructura', 'gestionar', now(), now())
                ON CONFLICT ON CONSTRAINT uq_permiso_tenant_codigo DO NOTHING
            """),
            {"tid": str(tid)},
        )
        # Grant a ADMIN con scope global
        conn.execute(
            sa.text("""
                INSERT INTO rol_permiso (id, tenant_id, rol_id, permiso_id, scope, created_at, updated_at)
                SELECT
                    gen_random_uuid(),
                    :tid,
                    r.id,
                    p.id,
                    CAST('global' AS permiso_scope),
                    now(),
                    now()
                FROM rol r, permiso p
                WHERE r.tenant_id = :tid
                  AND r.nombre = 'ADMIN'
                  AND p.tenant_id = :tid
                  AND p.codigo = 'estructura:gestionar'
                  AND r.deleted_at IS NULL
                  AND p.deleted_at IS NULL
                ON CONFLICT ON CONSTRAINT uq_rol_permiso DO NOTHING
            """),
            {"tid": str(tid)},
        )


def downgrade() -> None:
    # --- Revertir seed del permiso/grant (orden inverso al upgrade) ---
    op.execute("""
        DO $$ BEGIN
            IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'rol_permiso') THEN
                DELETE FROM rol_permiso
        WHERE permiso_id IN (
            SELECT id FROM permiso WHERE codigo = 'estructura:gestionar'
        );
            END IF;
        END $$;
    """)
    op.execute("""
        DO $$ BEGIN
            IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'permiso') THEN
                DELETE FROM permiso WHERE codigo = 'estructura:gestionar';
            END IF;
        END $$;
    """)

    # --- Drop índices únicos parciales ---
    op.execute("DROP INDEX IF EXISTS ux_cohorte_tenant_carrera_nombre")
    op.execute("DROP INDEX IF EXISTS ux_materia_tenant_codigo")
    op.execute("DROP INDEX IF EXISTS ux_carrera_tenant_codigo")

    # --- Drop tablas (cohorte antes que carrera por la FK) ---
    op.drop_index("ix_cohorte_tenant_carrera", table_name="cohorte")
    op.drop_index("ix_cohorte_deleted_at",      table_name="cohorte")
    op.drop_index("ix_cohorte_tenant_id",        table_name="cohorte")
    op.drop_table("cohorte")

    op.drop_index("ix_materia_deleted_at", table_name="materia")
    op.drop_index("ix_materia_tenant_id",  table_name="materia")
    op.drop_table("materia")

    op.drop_index("ix_carrera_deleted_at", table_name="carrera")
    op.drop_index("ix_carrera_tenant_id",  table_name="carrera")
    op.drop_table("carrera")

    # --- Drop enum ---
    op.execute("DROP TYPE IF EXISTS estado_estructura CASCADE")
