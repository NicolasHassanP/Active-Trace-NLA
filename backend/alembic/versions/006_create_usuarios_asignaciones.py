"""006 — create usuarios y asignaciones tables

Revision ID: 006
Revises: 005
Create Date: 2026-06-03

C-07: Identidad de negocio (Usuario) y eje de autorización contextual (Asignacion).

Design decisions:
    D1 — revision="006", down_revision="005".
    D2 — PII cifrada como TEXT (ciphertext AES-256-GCM base64url). EncryptedString en ORM.
    D3 — email_hash blind index + índice único parcial (tenant_id, email_hash) WHERE deleted_at IS NULL.
    D4 — estado_vigencia NO es columna (derivado en runtime).
    D5 — responsable_id self-FK → usuario.id RESTRICT nullable.
    D7 — Enum rol_asignacion idempotente (patrón DO/EXCEPTION de 003/005).
    D8 — Seed idempotente de usuarios:gestionar (→ ADMIN) y equipos:asignar (→ COORDINADOR, ADMIN).
    D9 — auth_identity_id FK nullable → auth_identities.id ON DELETE SET NULL. Sin backfill.

CHECKPOINT RBAC (CRÍTICO): el seed idempotente de permisos toca RBAC.
  Permisos ya sembrados en 003 para tenants existentes.
  Esta migración es no-op para ellos (ON CONFLICT DO NOTHING).
  Patrón EXACTO de 005: loop tenants no borrados, INSERT … ON CONFLICT DO NOTHING.
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = "006"
down_revision = "005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- Create enums idempotentes ---
    # rol_asignacion
    op.execute(
        "DO $$ BEGIN "
        "  CREATE TYPE rol_asignacion AS ENUM "
        "    ('PROFESOR', 'TUTOR', 'COORDINADOR', 'NEXO', 'ADMIN', 'FINANZAS'); "
        "EXCEPTION WHEN duplicate_object THEN NULL; "
        "END $$;"
    )
    # usuario_estado
    op.execute(
        "DO $$ BEGIN "
        "  CREATE TYPE usuario_estado AS ENUM ('activo', 'inactivo'); "
        "EXCEPTION WHEN duplicate_object THEN NULL; "
        "END $$;"
    )

    # --- CREATE TABLE usuario ---
    op.execute("""
        CREATE TABLE usuario (
            id                  UUID            NOT NULL DEFAULT gen_random_uuid(),
            tenant_id           UUID            NOT NULL REFERENCES tenants(id) ON DELETE RESTRICT,
            -- PII cifrada (ciphertext AES-256-GCM base64url)
            email_encrypted     TEXT            NOT NULL,
            email_hash          VARCHAR(64)     NOT NULL,
            dni                 TEXT,
            cuil                TEXT,
            cbu                 TEXT,
            alias_cbu           TEXT,
            -- Identidad / negocio (§E4 completo)
            nombre              VARCHAR(200)    NOT NULL,
            apellidos           VARCHAR(200)    NOT NULL,
            legajo              VARCHAR(50),
            legajo_profesional  VARCHAR(50),
            banco               VARCHAR(100),
            regional            VARCHAR(100),
            facturador          BOOLEAN         NOT NULL DEFAULT FALSE,
            estado              usuario_estado  NOT NULL DEFAULT 'activo',
            -- Reconciliación auth (D9) — FK nullable, ON DELETE SET NULL
            auth_identity_id    UUID            REFERENCES auth_identities(id) ON DELETE SET NULL,
            -- Base TenantScopedBase
            created_at          TIMESTAMPTZ     NOT NULL DEFAULT now(),
            updated_at          TIMESTAMPTZ     NOT NULL DEFAULT now(),
            deleted_at          TIMESTAMPTZ,
            PRIMARY KEY (id)
        )
    """)
    op.create_index("ix_usuario_tenant_id",  "usuario", ["tenant_id"])
    op.create_index("ix_usuario_deleted_at", "usuario", ["deleted_at"])
    op.create_index("ix_usuario_email_hash", "usuario", ["email_hash"])
    op.create_index("ix_usuario_auth_identity_id", "usuario", ["auth_identity_id"])

    # --- Índice único parcial email (D3) ---
    op.execute("""
        CREATE UNIQUE INDEX ux_usuario_tenant_email_hash
        ON usuario (tenant_id, email_hash)
        WHERE deleted_at IS NULL
    """)

    # --- Índice único parcial auth_identity_id por tenant (D9/OQ-2) ---
    op.execute("""
        CREATE UNIQUE INDEX ux_usuario_tenant_auth_identity
        ON usuario (tenant_id, auth_identity_id)
        WHERE deleted_at IS NULL AND auth_identity_id IS NOT NULL
    """)

    # --- CREATE TABLE asignacion ---
    op.execute("""
        CREATE TABLE asignacion (
            id              UUID            NOT NULL DEFAULT gen_random_uuid(),
            tenant_id       UUID            NOT NULL REFERENCES tenants(id) ON DELETE RESTRICT,
            -- FK obligatoria al usuario
            usuario_id      UUID            NOT NULL REFERENCES usuario(id) ON DELETE RESTRICT,
            -- Rol
            rol             rol_asignacion  NOT NULL,
            -- Contexto (nullable, FKs RESTRICT)
            materia_id      UUID            REFERENCES materia(id) ON DELETE RESTRICT,
            carrera_id      UUID            REFERENCES carrera(id) ON DELETE RESTRICT,
            cohorte_id      UUID            REFERENCES cohorte(id) ON DELETE RESTRICT,
            -- Comisiones
            comisiones      JSONB           NOT NULL DEFAULT '[]'::jsonb,
            -- Responsable (self-FK RESTRICT nullable, D5)
            responsable_id  UUID            REFERENCES usuario(id) ON DELETE RESTRICT,
            -- Ventana temporal (D4)
            desde           DATE            NOT NULL,
            hasta           DATE,
            -- Base TenantScopedBase
            created_at      TIMESTAMPTZ     NOT NULL DEFAULT now(),
            updated_at      TIMESTAMPTZ     NOT NULL DEFAULT now(),
            deleted_at      TIMESTAMPTZ,
            PRIMARY KEY (id)
        )
    """)
    op.create_index("ix_asignacion_tenant_id",     "asignacion", ["tenant_id"])
    op.create_index("ix_asignacion_deleted_at",    "asignacion", ["deleted_at"])
    op.create_index("ix_asignacion_usuario_id",    "asignacion", ["usuario_id"])
    op.create_index("ix_asignacion_materia_id",    "asignacion", ["materia_id"])
    op.create_index("ix_asignacion_carrera_id",    "asignacion", ["carrera_id"])
    op.create_index("ix_asignacion_cohorte_id",    "asignacion", ["cohorte_id"])
    op.create_index("ix_asignacion_responsable_id","asignacion", ["responsable_id"])

    # --- Seed idempotente per-tenant (D8) ---
    # CHECKPOINT RBAC (CRÍTICO): revisado y aprobado por el usuario.
    # Permisos ya sembrados en 003 para tenants existentes.
    # ON CONFLICT DO NOTHING → no-op para tenants que ya los tienen.
    conn = op.get_bind()
    tenants = conn.execute(
        sa.text("SELECT id FROM tenants WHERE deleted_at IS NULL")
    ).fetchall()
    for (tid,) in tenants:
        # Seed usuarios:gestionar
        conn.execute(
            sa.text("""
                INSERT INTO permiso (id, tenant_id, codigo, modulo, accion, created_at, updated_at)
                VALUES (gen_random_uuid(), :tid, 'usuarios:gestionar', 'usuarios', 'gestionar', now(), now())
                ON CONFLICT ON CONSTRAINT uq_permiso_tenant_codigo DO NOTHING
            """),
            {"tid": str(tid)},
        )
        # Grant usuarios:gestionar → ADMIN (global)
        conn.execute(
            sa.text("""
                INSERT INTO rol_permiso (id, tenant_id, rol_id, permiso_id, scope, created_at, updated_at)
                SELECT
                    gen_random_uuid(), :tid, r.id, p.id,
                    CAST('global' AS permiso_scope), now(), now()
                FROM rol r, permiso p
                WHERE r.tenant_id = :tid
                  AND r.nombre = 'ADMIN'
                  AND p.tenant_id = :tid
                  AND p.codigo = 'usuarios:gestionar'
                  AND r.deleted_at IS NULL
                  AND p.deleted_at IS NULL
                ON CONFLICT ON CONSTRAINT uq_rol_permiso DO NOTHING
            """),
            {"tid": str(tid)},
        )

        # Seed equipos:asignar
        conn.execute(
            sa.text("""
                INSERT INTO permiso (id, tenant_id, codigo, modulo, accion, created_at, updated_at)
                VALUES (gen_random_uuid(), :tid, 'equipos:asignar', 'equipos', 'asignar', now(), now())
                ON CONFLICT ON CONSTRAINT uq_permiso_tenant_codigo DO NOTHING
            """),
            {"tid": str(tid)},
        )
        # Grant equipos:asignar → COORDINADOR (global)
        conn.execute(
            sa.text("""
                INSERT INTO rol_permiso (id, tenant_id, rol_id, permiso_id, scope, created_at, updated_at)
                SELECT
                    gen_random_uuid(), :tid, r.id, p.id,
                    CAST('global' AS permiso_scope), now(), now()
                FROM rol r, permiso p
                WHERE r.tenant_id = :tid
                  AND r.nombre = 'COORDINADOR'
                  AND p.tenant_id = :tid
                  AND p.codigo = 'equipos:asignar'
                  AND r.deleted_at IS NULL
                  AND p.deleted_at IS NULL
                ON CONFLICT ON CONSTRAINT uq_rol_permiso DO NOTHING
            """),
            {"tid": str(tid)},
        )
        # Grant equipos:asignar → ADMIN (global)
        conn.execute(
            sa.text("""
                INSERT INTO rol_permiso (id, tenant_id, rol_id, permiso_id, scope, created_at, updated_at)
                SELECT
                    gen_random_uuid(), :tid, r.id, p.id,
                    CAST('global' AS permiso_scope), now(), now()
                FROM rol r, permiso p
                WHERE r.tenant_id = :tid
                  AND r.nombre = 'ADMIN'
                  AND p.tenant_id = :tid
                  AND p.codigo = 'equipos:asignar'
                  AND r.deleted_at IS NULL
                  AND p.deleted_at IS NULL
                ON CONFLICT ON CONSTRAINT uq_rol_permiso DO NOTHING
            """),
            {"tid": str(tid)},
        )


def downgrade() -> None:
    # --- Revertir seed de permisos/grants (D8) ---
    op.execute("""
        DO $$ BEGIN
            IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'rol_permiso') THEN
                DELETE FROM rol_permiso
                WHERE permiso_id IN (
                    SELECT id FROM permiso
                    WHERE codigo IN ('usuarios:gestionar', 'equipos:asignar')
                );
            END IF;
        END $$;
    """)
    op.execute("""
        DO $$ BEGIN
            IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'permiso') THEN
                DELETE FROM permiso WHERE codigo IN ('usuarios:gestionar', 'equipos:asignar');
            END IF;
        END $$;
    """)

    # --- Drop índices únicos parciales ---
    op.execute("DROP INDEX IF EXISTS ux_usuario_tenant_auth_identity")
    op.execute("DROP INDEX IF EXISTS ux_usuario_tenant_email_hash")

    # --- Drop tablas (asignacion antes que usuario por FKs) ---
    op.drop_index("ix_asignacion_responsable_id", table_name="asignacion")
    op.drop_index("ix_asignacion_cohorte_id",     table_name="asignacion")
    op.drop_index("ix_asignacion_carrera_id",     table_name="asignacion")
    op.drop_index("ix_asignacion_materia_id",     table_name="asignacion")
    op.drop_index("ix_asignacion_usuario_id",     table_name="asignacion")
    op.drop_index("ix_asignacion_deleted_at",     table_name="asignacion")
    op.drop_index("ix_asignacion_tenant_id",      table_name="asignacion")
    op.drop_table("asignacion")

    op.drop_index("ix_usuario_auth_identity_id", table_name="usuario")
    op.drop_index("ix_usuario_email_hash",       table_name="usuario")
    op.drop_index("ix_usuario_deleted_at",       table_name="usuario")
    op.drop_index("ix_usuario_tenant_id",        table_name="usuario")
    op.drop_table("usuario")

    # --- Drop enums ---
    op.execute("DROP TYPE IF EXISTS usuario_estado CASCADE")
    op.execute("DROP TYPE IF EXISTS rol_asignacion CASCADE")
