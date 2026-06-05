"""009 — create comunicacion + tenant_config tables

Revision ID: 009
Revises: 008
Create Date: 2026-06-04

C-12: Canal de comunicación saliente — cola, aprobación, despacho async.

Design decisions:
    D1 — revision="009", down_revision="008".
    D2 — Tabla 'comunicacion': TenantScopedBase, destinatario cifrado (TEXT),
         estado enum, lote_id para agrupación, índices por (tenant_id, estado)
         y lote_id.
    D3 — Email sender Protocol + TestSender (sin SMTP real en esta migración).
    D4 — OQ-4: plantilla falla fuerte ante variable sin resolver.
    D5 — OQ-5: Error es TERMINAL (no reintento automático).
    D6 — Tabla 'tenant_config': clave/valor por tenant, UNIQUE (tenant_id, clave)
         WHERE deleted_at IS NULL.
    D7 — audit_action ADD VALUE 'COMUNICACION_ENVIAR' idempotente (DO/EXCEPTION).
    D8 — Permisos: comunicacion:enviar (PROFESOR propio, COORDINADOR global, ADMIN global);
         comunicacion:aprobar (COORDINADOR global, ADMIN global). Seed idempotente.
    D9 — downgrade elimina ambas tablas y el enum comunicacion_estado.
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = "009"
down_revision = "008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- CREATE ENUM comunicacion_estado ---
    op.execute(
        "DO $$ BEGIN "
        "  CREATE TYPE comunicacion_estado AS ENUM "
        "  ('Pendiente', 'Enviando', 'Enviado', 'Error', 'Cancelado'); "
        "EXCEPTION WHEN duplicate_object THEN NULL; "
        "END $$;"
    )

    # --- Extend audit_action enum with COMUNICACION_ENVIAR ---
    op.execute(
        "DO $$ BEGIN "
        "  ALTER TYPE audit_action ADD VALUE 'COMUNICACION_ENVIAR'; "
        "EXCEPTION WHEN duplicate_object THEN NULL; "
        "END $$;"
    )

    # --- CREATE TABLE comunicacion ---
    op.execute("""
        CREATE TABLE comunicacion (
            id              UUID            NOT NULL DEFAULT gen_random_uuid(),
            tenant_id       UUID            NOT NULL REFERENCES tenants(id) ON DELETE RESTRICT,
            -- destinatario cifrado en reposo (AES-256-GCM vía EncryptedString a nivel ORM)
            destinatario    TEXT            NOT NULL,
            asunto          TEXT            NOT NULL,
            cuerpo          TEXT            NOT NULL,
            estado          comunicacion_estado NOT NULL DEFAULT 'Pendiente',
            lote_id         UUID            NOT NULL,
            enviado_por     UUID            REFERENCES usuario(id) ON DELETE SET NULL,
            aprobado_por    UUID            REFERENCES usuario(id) ON DELETE SET NULL,
            enviado_at      TIMESTAMPTZ,
            error_detalle   TEXT,
            -- Base TenantScopedBase
            created_at      TIMESTAMPTZ     NOT NULL DEFAULT now(),
            updated_at      TIMESTAMPTZ     NOT NULL DEFAULT now(),
            deleted_at      TIMESTAMPTZ,
            PRIMARY KEY (id)
        )
    """)
    op.create_index("ix_com_tenant_id",   "comunicacion", ["tenant_id"])
    op.create_index("ix_com_lote_id",     "comunicacion", ["lote_id"])
    # Compound index for worker polling: tenant + estado
    op.execute("""
        CREATE INDEX ix_com_tenant_estado
        ON comunicacion(tenant_id, estado)
        WHERE deleted_at IS NULL
    """)

    # --- CREATE TABLE tenant_config ---
    op.execute("""
        CREATE TABLE tenant_config (
            id          UUID        NOT NULL DEFAULT gen_random_uuid(),
            tenant_id   UUID        NOT NULL REFERENCES tenants(id) ON DELETE RESTRICT,
            clave       TEXT        NOT NULL,
            valor       TEXT        NOT NULL,
            -- Base TenantScopedBase
            created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
            deleted_at  TIMESTAMPTZ,
            PRIMARY KEY (id)
        )
    """)
    op.create_index("ix_tc_tenant_id", "tenant_config", ["tenant_id"])

    # Partial unique: one config per (tenant, clave) among non-deleted
    op.execute("""
        CREATE UNIQUE INDEX uq_tenant_config_tenant_clave
        ON tenant_config(tenant_id, clave)
        WHERE deleted_at IS NULL
    """)

    # --- Seed idempotente de permisos (D8) ---
    # comunicacion:enviar  → PROFESOR(propio), COORDINADOR(global), ADMIN(global)
    # comunicacion:aprobar → COORDINADOR(global), ADMIN(global)
    conn = op.get_bind()
    tenants = conn.execute(
        sa.text("SELECT id FROM tenants WHERE deleted_at IS NULL")
    ).fetchall()

    for (tid,) in tenants:
        # comunicacion:enviar
        conn.execute(
            sa.text("""
                INSERT INTO permiso (id, tenant_id, codigo, modulo, accion, created_at, updated_at)
                VALUES (gen_random_uuid(), :tid, 'comunicacion:enviar', 'comunicacion', 'enviar', now(), now())
                ON CONFLICT ON CONSTRAINT uq_permiso_tenant_codigo DO NOTHING
            """),
            {"tid": str(tid)},
        )
        for rol_nombre, scope in [
            ("PROFESOR", "propio"),
            ("COORDINADOR", "global"),
            ("ADMIN", "global"),
        ]:
            conn.execute(
                sa.text("""
                    INSERT INTO rol_permiso (id, tenant_id, rol_id, permiso_id, scope, created_at, updated_at)
                    SELECT
                        gen_random_uuid(), :tid, r.id, p.id,
                        CAST(:scope AS permiso_scope), now(), now()
                    FROM rol r, permiso p
                    WHERE r.tenant_id = :tid
                      AND r.nombre = :rol_nombre
                      AND p.tenant_id = :tid
                      AND p.codigo = 'comunicacion:enviar'
                      AND r.deleted_at IS NULL
                      AND p.deleted_at IS NULL
                    ON CONFLICT ON CONSTRAINT uq_rol_permiso DO NOTHING
                """),
                {"tid": str(tid), "rol_nombre": rol_nombre, "scope": scope},
            )

        # comunicacion:aprobar
        conn.execute(
            sa.text("""
                INSERT INTO permiso (id, tenant_id, codigo, modulo, accion, created_at, updated_at)
                VALUES (gen_random_uuid(), :tid, 'comunicacion:aprobar', 'comunicacion', 'aprobar', now(), now())
                ON CONFLICT ON CONSTRAINT uq_permiso_tenant_codigo DO NOTHING
            """),
            {"tid": str(tid)},
        )
        for rol_nombre, scope in [
            ("COORDINADOR", "global"),
            ("ADMIN", "global"),
        ]:
            conn.execute(
                sa.text("""
                    INSERT INTO rol_permiso (id, tenant_id, rol_id, permiso_id, scope, created_at, updated_at)
                    SELECT
                        gen_random_uuid(), :tid, r.id, p.id,
                        CAST(:scope AS permiso_scope), now(), now()
                    FROM rol r, permiso p
                    WHERE r.tenant_id = :tid
                      AND r.nombre = :rol_nombre
                      AND p.tenant_id = :tid
                      AND p.codigo = 'comunicacion:aprobar'
                      AND r.deleted_at IS NULL
                      AND p.deleted_at IS NULL
                    ON CONFLICT ON CONSTRAINT uq_rol_permiso DO NOTHING
                """),
                {"tid": str(tid), "rol_nombre": rol_nombre, "scope": scope},
            )


def downgrade() -> None:
    # --- Revertir seed de permisos/grants (D8) ---
    op.execute("""
        DO $$ BEGIN
            IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'rol_permiso') THEN
                DELETE FROM rol_permiso
                WHERE permiso_id IN (
                    SELECT id FROM permiso
                    WHERE codigo IN ('comunicacion:enviar', 'comunicacion:aprobar')
                );
            END IF;
        END $$;
    """)
    op.execute("""
        DO $$ BEGIN
            IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'permiso') THEN
                DELETE FROM permiso WHERE codigo IN ('comunicacion:enviar', 'comunicacion:aprobar');
            END IF;
        END $$;
    """)

    # --- Drop partial indexes ---
    op.execute("DROP INDEX IF EXISTS ix_com_tenant_estado")
    op.execute("DROP INDEX IF EXISTS uq_tenant_config_tenant_clave")

    # --- Drop comunicacion ---
    op.drop_index("ix_com_lote_id",   table_name="comunicacion")
    op.drop_index("ix_com_tenant_id", table_name="comunicacion")
    op.drop_table("comunicacion")

    # --- Drop tenant_config ---
    op.drop_index("ix_tc_tenant_id", table_name="tenant_config")
    op.drop_table("tenant_config")

    # --- Drop comunicacion_estado enum ---
    # Note: ALTER TYPE audit_action ADD VALUE is NOT reversible in Postgres.
    # COMUNICACION_ENVIAR remains in the enum after downgrade (same trade-off as 007/008).
    op.execute("DROP TYPE IF EXISTS comunicacion_estado")
