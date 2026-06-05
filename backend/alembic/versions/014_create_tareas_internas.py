"""014 — tareas internas: tablas + RBAC + audit

Revision ID: 014
Revises: 013
Create Date: 2026-06-04

C-16: Tareas Internas (F8.1–F8.3, FL-05).

Design decisions:
    D9  — revision="014", down_revision="013".
    D8  — Extend audit_action: TAREA_ASIGNAR, TAREA_DELEGAR, TAREA_CAMBIAR_ESTADO (idempotente).
    D2  — Enum tarea_estado (Pendiente|EnProgreso|Resuelta|Cancelada) idempotente.
    D1  — Tablas en orden FK: tarea → comentario_tarea (tenant-scoped, soft-delete).
    D9  — Índices nombrados explícitos.
    D9  — Seed RBAC: 'tareas:gestionar' (COORDINADOR, ADMIN) por tenant con ON CONFLICT DO NOTHING.
    D9  — downgrade: borra rol_permiso/permiso tareas:gestionar, drop indexes, drop tablas,
          drop enum tarea_estado. La extensión de audit_action NO es reversible (Postgres limitation).
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers
revision = "014"
down_revision = "013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- D8: Extend audit_action enum idempotently (3 new values) ---
    for action in ("TAREA_ASIGNAR", "TAREA_DELEGAR", "TAREA_CAMBIAR_ESTADO"):
        op.execute(
            f"DO $$ BEGIN "
            f"  ALTER TYPE audit_action ADD VALUE '{action}'; "
            f"EXCEPTION WHEN duplicate_object THEN NULL; "
            f"END $$;"
        )

    # --- D2: Create enum tarea_estado idempotently (mirror aviso_alcance pattern in 013) ---
    op.execute(
        "DO $$ BEGIN "
        "  CREATE TYPE tarea_estado AS ENUM "
        "  ('Pendiente', 'EnProgreso', 'Resuelta', 'Cancelada'); "
        "EXCEPTION WHEN duplicate_object THEN NULL; "
        "END $$;"
    )

    # --- D1/D9: Create table tarea (FK order: before comentario_tarea) ---
    op.execute("""
        CREATE TABLE IF NOT EXISTS tarea (
            id            UUID          PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id     UUID          NOT NULL REFERENCES tenants(id) ON DELETE RESTRICT,
            asignado_a    UUID          NOT NULL REFERENCES usuario(id) ON DELETE RESTRICT,
            asignado_por  UUID          NOT NULL REFERENCES usuario(id) ON DELETE RESTRICT,
            descripcion   TEXT          NOT NULL,
            estado        tarea_estado  NOT NULL,
            materia_id    UUID          NULL REFERENCES materia(id) ON DELETE RESTRICT,
            contexto_id   UUID          NULL,
            contexto_tipo VARCHAR(50)   NULL,
            created_at    TIMESTAMPTZ   NOT NULL DEFAULT now(),
            updated_at    TIMESTAMPTZ   NOT NULL DEFAULT now(),
            deleted_at    TIMESTAMPTZ   NULL
        )
    """)

    # --- D1/D9: Create table comentario_tarea (FK to tarea) ---
    op.execute("""
        CREATE TABLE IF NOT EXISTS comentario_tarea (
            id         UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id  UUID        NOT NULL REFERENCES tenants(id) ON DELETE RESTRICT,
            tarea_id   UUID        NOT NULL REFERENCES tarea(id) ON DELETE RESTRICT,
            autor_id   UUID        NOT NULL REFERENCES usuario(id) ON DELETE RESTRICT,
            cuerpo     TEXT        NOT NULL,
            es_sistema BOOLEAN     NOT NULL DEFAULT FALSE,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            deleted_at TIMESTAMPTZ NULL
        )
    """)

    # --- D9: Named indexes ---
    # tarea indexes (hot paths: mis tareas, admin admin filter)
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_tarea_tenant_asignado_a_estado "
        "ON tarea (tenant_id, asignado_a, estado)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_tarea_tenant_asignado_por "
        "ON tarea (tenant_id, asignado_por)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_tarea_tenant_materia_id "
        "ON tarea (tenant_id, materia_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_tarea_tenant_estado "
        "ON tarea (tenant_id, estado)"
    )
    # comentario_tarea thread index (ordered by created_at for the thread)
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_comentario_tarea_tenant_tarea_id "
        "ON comentario_tarea (tenant_id, tarea_id, created_at)"
    )

    # --- D9/D7: Seed RBAC permission tareas:gestionar per-tenant ---
    conn = op.get_bind()
    tenants = conn.execute(
        sa.text("SELECT id FROM tenants WHERE deleted_at IS NULL")
    ).fetchall()

    for (tid,) in tenants:
        # Insert tareas:gestionar permission
        conn.execute(
            sa.text("""
                INSERT INTO permiso (id, tenant_id, codigo, modulo, accion, created_at, updated_at)
                VALUES (gen_random_uuid(), :tid, 'tareas:gestionar', 'tareas', 'gestionar', now(), now())
                ON CONFLICT ON CONSTRAINT uq_permiso_tenant_codigo DO NOTHING
            """),
            {"tid": str(tid)},
        )
        # Grant tareas:gestionar to COORDINADOR and ADMIN
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
                      AND p.codigo = 'tareas:gestionar'
                      AND r.deleted_at IS NULL
                      AND p.deleted_at IS NULL
                    ON CONFLICT ON CONSTRAINT uq_rol_permiso DO NOTHING
                """),
                {"tid": str(tid), "rol_nombre": rol_nombre},
            )


def downgrade() -> None:
    # D9: Revert RBAC seed — remove rol_permiso then permiso rows (defensive: tables may not exist)
    op.execute("""
        DO $$ BEGIN
            IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'rol_permiso') THEN
                DELETE FROM rol_permiso
                WHERE permiso_id IN (
                    SELECT id FROM permiso WHERE codigo = 'tareas:gestionar'
                );
            END IF;
        END $$;
    """)
    op.execute("""
        DO $$ BEGIN
            IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'permiso') THEN
                DELETE FROM permiso WHERE codigo = 'tareas:gestionar';
            END IF;
        END $$;
    """)

    # D9: Drop named indexes in reverse order
    op.execute("DROP INDEX IF EXISTS ix_comentario_tarea_tenant_tarea_id")
    op.execute("DROP INDEX IF EXISTS ix_tarea_tenant_estado")
    op.execute("DROP INDEX IF EXISTS ix_tarea_tenant_materia_id")
    op.execute("DROP INDEX IF EXISTS ix_tarea_tenant_asignado_por")
    op.execute("DROP INDEX IF EXISTS ix_tarea_tenant_asignado_a_estado")

    # D9: Drop tables in reverse FK order (comentario_tarea first, then tarea)
    op.execute("DROP TABLE IF EXISTS comentario_tarea CASCADE")
    op.execute("DROP TABLE IF EXISTS tarea CASCADE")

    # D2: Drop enum tarea_estado
    op.execute("DROP TYPE IF EXISTS tarea_estado CASCADE")

    # Note: TAREA_ASIGNAR, TAREA_DELEGAR, TAREA_CAMBIAR_ESTADO added to audit_action
    # are NOT reversible (Postgres does not support removing enum values).
    # These values remain in the audit_action type after downgrade.
