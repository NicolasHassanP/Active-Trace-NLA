"""007 — create version_padron + entrada_padron tables

Revision ID: 007
Revises: 006
Create Date: 2026-06-03

C-09: Padrón versionado de alumnos por materia×cohorte + integración Moodle.

Design decisions:
    D1 — revision="007", down_revision="006".
    D2 — activa como cursor de versión activa (UPDATE prior + INSERT new, misma tx).
    D3 — EntradaPadron.email_encrypted con EncryptedString (AES-256-GCM), sin blind index.
    D4 — usuario_id nullable en entrada_padron (FK→usuario, ON DELETE SET NULL).
    D8 — Permisos nuevos: padron:cargar (PROFESOR, COORDINADOR, ADMIN),
         padron:gestionar (COORDINADOR, ADMIN). Seed idempotente.
    Indexes — ix_vp_tenant_materia_cohorte_activa (partial WHERE activa=TRUE),
              ix_ep_version_id, ix_ep_tenant_usuario (partial WHERE deleted_at IS NULL).
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = "007"
down_revision = "006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- Extend audit_action enum with PADRON_CARGAR ---
    # Idempotent: IF NOT EXISTS is not available before PG 12;
    # use DO/EXCEPTION same pattern as 004/005.
    op.execute(
        "DO $$ BEGIN "
        "  ALTER TYPE audit_action ADD VALUE 'PADRON_CARGAR'; "
        "EXCEPTION WHEN duplicate_object THEN NULL; "
        "END $$;"
    )

    # --- CREATE TABLE version_padron ---
    op.execute("""
        CREATE TABLE version_padron (
            id              UUID            NOT NULL DEFAULT gen_random_uuid(),
            tenant_id       UUID            NOT NULL REFERENCES tenants(id) ON DELETE RESTRICT,
            materia_id      UUID            NOT NULL REFERENCES materia(id) ON DELETE RESTRICT,
            cohorte_id      UUID            NOT NULL REFERENCES cohorte(id) ON DELETE RESTRICT,
            cargado_por     UUID            REFERENCES usuario(id) ON DELETE SET NULL,
            cargado_at      TIMESTAMPTZ     NOT NULL DEFAULT now(),
            activa          BOOLEAN         NOT NULL DEFAULT FALSE,
            -- Base TenantScopedBase
            created_at      TIMESTAMPTZ     NOT NULL DEFAULT now(),
            updated_at      TIMESTAMPTZ     NOT NULL DEFAULT now(),
            deleted_at      TIMESTAMPTZ,
            PRIMARY KEY (id)
        )
    """)
    op.create_index("ix_vp_tenant_id",     "version_padron", ["tenant_id"])
    op.create_index("ix_vp_deleted_at",    "version_padron", ["deleted_at"])
    op.create_index("ix_vp_materia_id",    "version_padron", ["materia_id"])
    op.create_index("ix_vp_cohorte_id",    "version_padron", ["cohorte_id"])
    op.create_index("ix_vp_cargado_por",   "version_padron", ["cargado_por"])

    # Partial index: at most one active version per (tenant, materia, cohorte)
    op.execute("""
        CREATE INDEX ix_vp_tenant_materia_cohorte_activa
        ON version_padron (tenant_id, materia_id, cohorte_id)
        WHERE activa = TRUE AND deleted_at IS NULL
    """)

    # --- CREATE TABLE entrada_padron ---
    op.execute("""
        CREATE TABLE entrada_padron (
            id              UUID            NOT NULL DEFAULT gen_random_uuid(),
            version_id      UUID            NOT NULL REFERENCES version_padron(id) ON DELETE RESTRICT,
            tenant_id       UUID            NOT NULL REFERENCES tenants(id) ON DELETE RESTRICT,
            usuario_id      UUID            REFERENCES usuario(id) ON DELETE SET NULL,
            nombre          TEXT            NOT NULL,
            apellidos       TEXT            NOT NULL,
            email_encrypted TEXT            NOT NULL,
            comision        TEXT,
            regional        TEXT,
            -- Base TenantScopedBase
            created_at      TIMESTAMPTZ     NOT NULL DEFAULT now(),
            updated_at      TIMESTAMPTZ     NOT NULL DEFAULT now(),
            deleted_at      TIMESTAMPTZ,
            PRIMARY KEY (id)
        )
    """)
    op.create_index("ix_ep_tenant_id",   "entrada_padron", ["tenant_id"])
    op.create_index("ix_ep_deleted_at",  "entrada_padron", ["deleted_at"])
    op.create_index("ix_ep_version_id",  "entrada_padron", ["version_id"])
    op.create_index("ix_ep_usuario_id",  "entrada_padron", ["usuario_id"])

    # Partial index for active tenant-user lookups
    op.execute("""
        CREATE INDEX ix_ep_tenant_usuario
        ON entrada_padron (tenant_id, usuario_id)
        WHERE deleted_at IS NULL
    """)

    # --- Seed idempotente de permisos (D8) ---
    # CHECKPOINT RBAC (CRÍTICO): revisado y aprobado.
    # padron:cargar  → PROFESOR, COORDINADOR, ADMIN
    # padron:gestionar → COORDINADOR, ADMIN
    conn = op.get_bind()
    tenants = conn.execute(
        sa.text("SELECT id FROM tenants WHERE deleted_at IS NULL")
    ).fetchall()
    for (tid,) in tenants:
        # Seed padron:cargar
        conn.execute(
            sa.text("""
                INSERT INTO permiso (id, tenant_id, codigo, modulo, accion, created_at, updated_at)
                VALUES (gen_random_uuid(), :tid, 'padron:cargar', 'padron', 'cargar', now(), now())
                ON CONFLICT ON CONSTRAINT uq_permiso_tenant_codigo DO NOTHING
            """),
            {"tid": str(tid)},
        )
        # Grant padron:cargar → PROFESOR
        for rol_nombre in ("PROFESOR", "COORDINADOR", "ADMIN"):
            conn.execute(
                sa.text("""
                    INSERT INTO rol_permiso (id, tenant_id, rol_id, permiso_id, scope, created_at, updated_at)
                    SELECT
                        gen_random_uuid(), :tid, r.id, p.id,
                        CAST('global' AS permiso_scope), now(), now()
                    FROM rol r, permiso p
                    WHERE r.tenant_id = :tid
                      AND r.nombre = :rol_nombre
                      AND p.tenant_id = :tid
                      AND p.codigo = 'padron:cargar'
                      AND r.deleted_at IS NULL
                      AND p.deleted_at IS NULL
                    ON CONFLICT ON CONSTRAINT uq_rol_permiso DO NOTHING
                """),
                {"tid": str(tid), "rol_nombre": rol_nombre},
            )

        # Seed padron:gestionar
        conn.execute(
            sa.text("""
                INSERT INTO permiso (id, tenant_id, codigo, modulo, accion, created_at, updated_at)
                VALUES (gen_random_uuid(), :tid, 'padron:gestionar', 'padron', 'gestionar', now(), now())
                ON CONFLICT ON CONSTRAINT uq_permiso_tenant_codigo DO NOTHING
            """),
            {"tid": str(tid)},
        )
        # Grant padron:gestionar → COORDINADOR, ADMIN
        for rol_nombre in ("COORDINADOR", "ADMIN"):
            conn.execute(
                sa.text("""
                    INSERT INTO rol_permiso (id, tenant_id, rol_id, permiso_id, scope, created_at, updated_at)
                    SELECT
                        gen_random_uuid(), :tid, r.id, p.id,
                        CAST('global' AS permiso_scope), now(), now()
                    FROM rol r, permiso p
                    WHERE r.tenant_id = :tid
                      AND r.nombre = :rol_nombre
                      AND p.tenant_id = :tid
                      AND p.codigo = 'padron:gestionar'
                      AND r.deleted_at IS NULL
                      AND p.deleted_at IS NULL
                    ON CONFLICT ON CONSTRAINT uq_rol_permiso DO NOTHING
                """),
                {"tid": str(tid), "rol_nombre": rol_nombre},
            )


def downgrade() -> None:
    # --- Revertir seed de permisos/grants (D8) ---
    op.execute("""
        DELETE FROM rol_permiso
        WHERE permiso_id IN (
            SELECT id FROM permiso
            WHERE codigo IN ('padron:cargar', 'padron:gestionar')
        )
    """)
    op.execute(
        "DELETE FROM permiso WHERE codigo IN ('padron:cargar', 'padron:gestionar')"
    )

    # --- Drop partial indexes ---
    op.execute("DROP INDEX IF EXISTS ix_ep_tenant_usuario")
    op.execute("DROP INDEX IF EXISTS ix_vp_tenant_materia_cohorte_activa")

    # --- Drop entrada_padron (referencia version_padron, va primero) ---
    op.drop_index("ix_ep_usuario_id",  table_name="entrada_padron")
    op.drop_index("ix_ep_version_id",  table_name="entrada_padron")
    op.drop_index("ix_ep_deleted_at",  table_name="entrada_padron")
    op.drop_index("ix_ep_tenant_id",   table_name="entrada_padron")
    op.drop_table("entrada_padron")

    # --- Drop version_padron ---
    op.drop_index("ix_vp_cargado_por",   table_name="version_padron")
    op.drop_index("ix_vp_cohorte_id",    table_name="version_padron")
    op.drop_index("ix_vp_materia_id",    table_name="version_padron")
    op.drop_index("ix_vp_deleted_at",    table_name="version_padron")
    op.drop_index("ix_vp_tenant_id",     table_name="version_padron")
    op.drop_table("version_padron")
