"""013 — avisos y acknowledgment: tablas + RBAC + audit

Revision ID: 013
Revises: 012
Create Date: 2026-06-04

C-15: Avisos y Acknowledgment.

Design decisions:
    D1  — revision="013", down_revision="012".
    D2  — Extend audit_action: AVISO_PUBLICAR (idempotente DO $$).
    D3  — Nuevos enums: aviso_alcance, aviso_severidad (idempotentes).
    D4  — Tablas en orden FK: aviso → acknowledgment_aviso (tenant-scoped, soft-delete).
    D5  — Índices con nombres explícitos.
    D6  — Índice parcial único uq_ack_aviso_usuario en acknowledgment_aviso.
    D7  — Seed RBAC: 'avisos:publicar' (COORDINADOR, ADMIN) por tenant con ON CONFLICT DO NOTHING.
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers
revision = "013"
down_revision = "012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- D2: Extend audit_action enum idempotently ---
    op.execute(
        "DO $$ BEGIN "
        "  ALTER TYPE audit_action ADD VALUE 'AVISO_PUBLICAR'; "
        "EXCEPTION WHEN duplicate_object THEN NULL; "
        "END $$;"
    )

    # --- D3: Create enums idempotently ---
    op.execute(
        "DO $$ BEGIN "
        "  CREATE TYPE aviso_alcance AS ENUM "
        "  ('Global', 'PorMateria', 'PorCohorte', 'PorRol'); "
        "EXCEPTION WHEN duplicate_object THEN NULL; "
        "END $$;"
    )
    op.execute(
        "DO $$ BEGIN "
        "  CREATE TYPE aviso_severidad AS ENUM "
        "  ('Info', 'Advertencia', 'Critico'); "
        "EXCEPTION WHEN duplicate_object THEN NULL; "
        "END $$;"
    )

    # --- D4: Create table aviso (FK order first) ---
    op.execute("""
        CREATE TABLE IF NOT EXISTS aviso (
            id           UUID             PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id    UUID             NOT NULL REFERENCES tenants(id) ON DELETE RESTRICT,
            alcance      aviso_alcance    NOT NULL,
            materia_id   UUID             NULL REFERENCES materia(id) ON DELETE RESTRICT,
            cohorte_id   UUID             NULL REFERENCES cohorte(id) ON DELETE RESTRICT,
            rol_destino  VARCHAR(50)      NULL,
            severidad    aviso_severidad  NOT NULL DEFAULT 'Info',
            titulo       VARCHAR(200)     NOT NULL,
            cuerpo       VARCHAR(4000)    NOT NULL,
            inicio_en    TIMESTAMPTZ      NOT NULL,
            fin_en       TIMESTAMPTZ      NOT NULL,
            orden        INTEGER          NOT NULL DEFAULT 100,
            activo       BOOLEAN          NOT NULL DEFAULT TRUE,
            requiere_ack BOOLEAN          NOT NULL DEFAULT FALSE,
            created_at   TIMESTAMPTZ      NOT NULL DEFAULT now(),
            updated_at   TIMESTAMPTZ      NOT NULL DEFAULT now(),
            deleted_at   TIMESTAMPTZ      NULL
        )
    """)

    # --- D4: Create table acknowledgment_aviso (FK to aviso) ---
    op.execute("""
        CREATE TABLE IF NOT EXISTS acknowledgment_aviso (
            id            UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id     UUID        NOT NULL REFERENCES tenants(id) ON DELETE RESTRICT,
            aviso_id      UUID        NOT NULL REFERENCES aviso(id) ON DELETE RESTRICT,
            usuario_id    UUID        NOT NULL REFERENCES usuario(id) ON DELETE RESTRICT,
            confirmado_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
            deleted_at    TIMESTAMPTZ NULL
        )
    """)

    # --- D5: Named indexes ---
    op.execute("CREATE INDEX IF NOT EXISTS ix_aviso_tenant_activo_ventana     ON aviso (tenant_id, activo, inicio_en, fin_en)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_aviso_tenant_cohorte_id         ON aviso (tenant_id, cohorte_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_aviso_tenant_materia_id         ON aviso (tenant_id, materia_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_ack_aviso_tenant_aviso_id       ON acknowledgment_aviso (tenant_id, aviso_id)")

    # --- D6: Partial unique index — prevent double-ack ---
    op.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS uq_ack_aviso_usuario
        ON acknowledgment_aviso (tenant_id, aviso_id, usuario_id)
        WHERE deleted_at IS NULL
    """)

    # --- D7: Seed RBAC permissions per-tenant ---
    conn = op.get_bind()
    tenants = conn.execute(
        sa.text("SELECT id FROM tenants WHERE deleted_at IS NULL")
    ).fetchall()

    for (tid,) in tenants:
        # Insert avisos:publicar permission
        conn.execute(
            sa.text("""
                INSERT INTO permiso (id, tenant_id, codigo, modulo, accion, created_at, updated_at)
                VALUES (gen_random_uuid(), :tid, 'avisos:publicar', 'avisos', 'publicar', now(), now())
                ON CONFLICT ON CONSTRAINT uq_permiso_tenant_codigo DO NOTHING
            """),
            {"tid": str(tid)},
        )
        # Grant avisos:publicar to COORDINADOR and ADMIN
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
                      AND p.codigo = 'avisos:publicar'
                      AND r.deleted_at IS NULL
                      AND p.deleted_at IS NULL
                    ON CONFLICT ON CONSTRAINT uq_rol_permiso DO NOTHING
                """),
                {"tid": str(tid), "rol_nombre": rol_nombre},
            )


def downgrade() -> None:
    # Revert RBAC seed
    op.execute("""
        DELETE FROM rol_permiso
        WHERE permiso_id IN (
            SELECT id FROM permiso WHERE codigo = 'avisos:publicar'
        )
    """)
    op.execute("DELETE FROM permiso WHERE codigo = 'avisos:publicar'")

    # Drop partial unique index
    op.execute("DROP INDEX IF EXISTS uq_ack_aviso_usuario")

    # Drop named indexes
    op.execute("DROP INDEX IF EXISTS ix_ack_aviso_tenant_aviso_id")
    op.execute("DROP INDEX IF EXISTS ix_aviso_tenant_materia_id")
    op.execute("DROP INDEX IF EXISTS ix_aviso_tenant_cohorte_id")
    op.execute("DROP INDEX IF EXISTS ix_aviso_tenant_activo_ventana")

    # Drop tables in reverse FK order
    op.execute("DROP TABLE IF EXISTS acknowledgment_aviso CASCADE")
    op.execute("DROP TABLE IF EXISTS aviso CASCADE")

    # Drop enums
    op.execute("DROP TYPE IF EXISTS aviso_severidad CASCADE")
    op.execute("DROP TYPE IF EXISTS aviso_alcance CASCADE")

    # Note: AVISO_PUBLICAR added to audit_action is not reversible (Postgres limitation).
