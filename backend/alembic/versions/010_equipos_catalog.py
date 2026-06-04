"""010 — equipos catalog: permiso equipos:ver, equipos:asignar + audit actions

Revision ID: 010
Revises: 009
Create Date: 2026-06-04

C-08: Equipos docentes — catálogo RBAC y acciones de auditoría.

Design decisions:
    D1 — revision="010", down_revision="009".
    D4 — OQ-4: equipos:ver → ADMIN(global), COORDINADOR(global), FINANZAS(global)
              para consulta general; PROFESOR(propio), TUTOR(propio), NEXO(propio)
              para mis-equipos.
         equipos:asignar → ADMIN(global), COORDINADOR(global).
    D9 — Acciones de auditoría: EQUIPOS_ASIGNACION_MASIVA, EQUIPOS_CLONAR,
         EQUIPOS_VIGENCIA_GENERAL añadidas con ADD VALUE idempotente.
    D10 — Migración ÚNICA del change — solo catálogo (sin schema de dominio).
          El equipo es una proyección derivada de Asignacion existente (C-07).
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers
revision = "010"
down_revision = "009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- Extend audit_action enum with C-08 actions (D9) ---
    op.execute(
        "DO $$ BEGIN "
        "  ALTER TYPE audit_action ADD VALUE 'EQUIPOS_ASIGNACION_MASIVA'; "
        "EXCEPTION WHEN duplicate_object THEN NULL; "
        "END $$;"
    )
    op.execute(
        "DO $$ BEGIN "
        "  ALTER TYPE audit_action ADD VALUE 'EQUIPOS_CLONAR'; "
        "EXCEPTION WHEN duplicate_object THEN NULL; "
        "END $$;"
    )
    op.execute(
        "DO $$ BEGIN "
        "  ALTER TYPE audit_action ADD VALUE 'EQUIPOS_VIGENCIA_GENERAL'; "
        "EXCEPTION WHEN duplicate_object THEN NULL; "
        "END $$;"
    )

    # --- Seed idempotente de permisos (D4, OQ-4) ---
    conn = op.get_bind()
    tenants = conn.execute(
        sa.text("SELECT id FROM tenants WHERE deleted_at IS NULL")
    ).fetchall()

    for (tid,) in tenants:
        # equipos:ver
        conn.execute(
            sa.text("""
                INSERT INTO permiso (id, tenant_id, codigo, modulo, accion, created_at, updated_at)
                VALUES (gen_random_uuid(), :tid, 'equipos:ver', 'equipos', 'ver', now(), now())
                ON CONFLICT ON CONSTRAINT uq_permiso_tenant_codigo DO NOTHING
            """),
            {"tid": str(tid)},
        )
        # Grant equipos:ver to management roles (global)
        for rol_nombre, scope in [
            ("ADMIN", "global"),
            ("COORDINADOR", "global"),
            ("FINANZAS", "global"),
            ("PROFESOR", "propio"),
            ("TUTOR", "propio"),
            ("NEXO", "propio"),
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
                      AND p.codigo = 'equipos:ver'
                      AND r.deleted_at IS NULL
                      AND p.deleted_at IS NULL
                    ON CONFLICT ON CONSTRAINT uq_rol_permiso DO NOTHING
                """),
                {"tid": str(tid), "rol_nombre": rol_nombre, "scope": scope},
            )

        # equipos:asignar
        conn.execute(
            sa.text("""
                INSERT INTO permiso (id, tenant_id, codigo, modulo, accion, created_at, updated_at)
                VALUES (gen_random_uuid(), :tid, 'equipos:asignar', 'equipos', 'asignar', now(), now())
                ON CONFLICT ON CONSTRAINT uq_permiso_tenant_codigo DO NOTHING
            """),
            {"tid": str(tid)},
        )
        for rol_nombre, scope in [
            ("ADMIN", "global"),
            ("COORDINADOR", "global"),
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
                      AND p.codigo = 'equipos:asignar'
                      AND r.deleted_at IS NULL
                      AND p.deleted_at IS NULL
                    ON CONFLICT ON CONSTRAINT uq_rol_permiso DO NOTHING
                """),
                {"tid": str(tid), "rol_nombre": rol_nombre, "scope": scope},
            )


def downgrade() -> None:
    # --- Revertir seed de permisos/grants (D4) ---
    op.execute("""
        DELETE FROM rol_permiso
        WHERE permiso_id IN (
            SELECT id FROM permiso
            WHERE codigo IN ('equipos:ver', 'equipos:asignar')
        )
    """)
    op.execute(
        "DELETE FROM permiso WHERE codigo IN ('equipos:ver', 'equipos:asignar')"
    )
    # Note: ALTER TYPE audit_action ADD VALUE is NOT reversible in Postgres.
    # EQUIPOS_* values remain in the enum after downgrade.
