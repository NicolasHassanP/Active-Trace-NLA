"""008 — create umbral_materia + calificacion tables

Revision ID: 008
Revises: 007
Create Date: 2026-06-04

C-10: Calificaciones por alumno×materia×actividad + umbral de aprobación configurable.

Design decisions:
    D1 — revision="008", down_revision="007".
    D2 — Calificacion cuelga de EntradaPadron (FK RESTRICT), materia_id desnormalizado.
    D3 — aprobado persistido, calculado al importar (no columna generada).
    D4 — derive_aprobado: función pura en calificacion_aprobado.py.
    D5 — UmbralMateria: unicidad por (tenant_id, asignacion_id, materia_id) WHERE deleted_at IS NULL.
    D8 — Upsert scope-isolated por (tenant, entrada_padron, materia, actividad, importado_por).
    D9 — Permisos: calificaciones:importar y calificaciones:configurar-umbral.
         PROFESOR → scope='propio'; COORDINADOR/ADMIN → scope='global'. Seed idempotente.
    D10 — audit_action ADD VALUE 'CALIFICACIONES_IMPORTAR' (idempotente).
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = "008"
down_revision = "007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- Extend audit_action enum with CALIFICACIONES_IMPORTAR ---
    op.execute(
        "DO $$ BEGIN "
        "  ALTER TYPE audit_action ADD VALUE 'CALIFICACIONES_IMPORTAR'; "
        "EXCEPTION WHEN duplicate_object THEN NULL; "
        "END $$;"
    )

    # --- CREATE ENUM calificacion_origen ---
    op.execute(
        "DO $$ BEGIN "
        "  CREATE TYPE calificacion_origen AS ENUM ('Importado', 'Manual'); "
        "EXCEPTION WHEN duplicate_object THEN NULL; "
        "END $$;"
    )

    # --- CREATE TABLE umbral_materia ---
    op.execute("""
        CREATE TABLE umbral_materia (
            id              UUID            NOT NULL DEFAULT gen_random_uuid(),
            tenant_id       UUID            NOT NULL REFERENCES tenants(id) ON DELETE RESTRICT,
            asignacion_id   UUID            NOT NULL REFERENCES asignacion(id) ON DELETE RESTRICT,
            materia_id      UUID            NOT NULL REFERENCES materia(id) ON DELETE RESTRICT,
            umbral_pct      INTEGER         NOT NULL DEFAULT 60,
            valores_aprobatorios JSONB      NOT NULL DEFAULT '[]',
            -- Base TenantScopedBase
            created_at      TIMESTAMPTZ     NOT NULL DEFAULT now(),
            updated_at      TIMESTAMPTZ     NOT NULL DEFAULT now(),
            deleted_at      TIMESTAMPTZ,
            PRIMARY KEY (id)
        )
    """)
    op.create_index("ix_um_tenant_id",  "umbral_materia", ["tenant_id"])
    op.create_index("ix_um_materia_id", "umbral_materia", ["materia_id"])

    # Partial unique: one umbral per (tenant, asignacion, materia) among non-deleted
    op.execute("""
        CREATE UNIQUE INDEX uq_um_asignacion_materia
        ON umbral_materia(tenant_id, asignacion_id, materia_id)
        WHERE deleted_at IS NULL
    """)

    # --- CREATE TABLE calificacion ---
    op.execute("""
        CREATE TABLE calificacion (
            id                  UUID            NOT NULL DEFAULT gen_random_uuid(),
            tenant_id           UUID            NOT NULL REFERENCES tenants(id) ON DELETE RESTRICT,
            entrada_padron_id   UUID            NOT NULL REFERENCES entrada_padron(id) ON DELETE RESTRICT,
            materia_id          UUID            NOT NULL REFERENCES materia(id) ON DELETE RESTRICT,
            importado_por       UUID            REFERENCES usuario(id) ON DELETE SET NULL,
            actividad           TEXT            NOT NULL,
            nota_numerica       NUMERIC,
            nota_textual        TEXT,
            aprobado            BOOLEAN         NOT NULL DEFAULT FALSE,
            origen              calificacion_origen NOT NULL DEFAULT 'Importado',
            importado_at        TIMESTAMPTZ,
            -- Base TenantScopedBase
            created_at          TIMESTAMPTZ     NOT NULL DEFAULT now(),
            updated_at          TIMESTAMPTZ     NOT NULL DEFAULT now(),
            deleted_at          TIMESTAMPTZ,
            PRIMARY KEY (id)
        )
    """)
    op.create_index("ix_cal_tenant_id",       "calificacion", ["tenant_id"])
    op.create_index("ix_cal_entrada_padron",  "calificacion", ["entrada_padron_id"])
    op.create_index("ix_cal_materia_id",      "calificacion", ["materia_id"])

    # Partial unique: one calificacion per (tenant, entrada_padron, materia, actividad, importado_por)
    op.execute("""
        CREATE UNIQUE INDEX uq_cal_entrada_materia_actividad_importador
        ON calificacion(tenant_id, entrada_padron_id, materia_id, actividad, importado_por)
        WHERE deleted_at IS NULL
    """)

    # --- Seed idempotente de permisos (D9) ---
    # CHECKPOINT RBAC (CRÍTICO): revisado y confirmado por el usuario.
    # calificaciones:importar  → PROFESOR(propio), COORDINADOR(global), ADMIN(global)
    # calificaciones:configurar-umbral → PROFESOR(propio), COORDINADOR(global), ADMIN(global)
    conn = op.get_bind()
    tenants = conn.execute(
        sa.text("SELECT id FROM tenants WHERE deleted_at IS NULL")
    ).fetchall()
    for (tid,) in tenants:
        # Seed calificaciones:importar
        conn.execute(
            sa.text("""
                INSERT INTO permiso (id, tenant_id, codigo, modulo, accion, created_at, updated_at)
                VALUES (gen_random_uuid(), :tid, 'calificaciones:importar', 'calificaciones', 'importar', now(), now())
                ON CONFLICT ON CONSTRAINT uq_permiso_tenant_codigo DO NOTHING
            """),
            {"tid": str(tid)},
        )
        for rol_nombre, scope in [("PROFESOR", "propio"), ("COORDINADOR", "global"), ("ADMIN", "global")]:
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
                      AND p.codigo = 'calificaciones:importar'
                      AND r.deleted_at IS NULL
                      AND p.deleted_at IS NULL
                    ON CONFLICT ON CONSTRAINT uq_rol_permiso DO NOTHING
                """),
                {"tid": str(tid), "rol_nombre": rol_nombre, "scope": scope},
            )

        # Seed calificaciones:configurar-umbral
        conn.execute(
            sa.text("""
                INSERT INTO permiso (id, tenant_id, codigo, modulo, accion, created_at, updated_at)
                VALUES (gen_random_uuid(), :tid, 'calificaciones:configurar-umbral', 'calificaciones', 'configurar-umbral', now(), now())
                ON CONFLICT ON CONSTRAINT uq_permiso_tenant_codigo DO NOTHING
            """),
            {"tid": str(tid)},
        )
        for rol_nombre, scope in [("PROFESOR", "propio"), ("COORDINADOR", "global"), ("ADMIN", "global")]:
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
                      AND p.codigo = 'calificaciones:configurar-umbral'
                      AND r.deleted_at IS NULL
                      AND p.deleted_at IS NULL
                    ON CONFLICT ON CONSTRAINT uq_rol_permiso DO NOTHING
                """),
                {"tid": str(tid), "rol_nombre": rol_nombre, "scope": scope},
            )


def downgrade() -> None:
    # --- Revertir seed de permisos/grants (D9) ---
    op.execute("""
        DO $$ BEGIN
            IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'rol_permiso') THEN
                DELETE FROM rol_permiso
                WHERE permiso_id IN (
                    SELECT id FROM permiso
                    WHERE codigo IN ('calificaciones:importar', 'calificaciones:configurar-umbral')
                );
            END IF;
        END $$;
    """)
    op.execute("""
        DO $$ BEGIN
            IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'permiso') THEN
                DELETE FROM permiso WHERE codigo IN ('calificaciones:importar', 'calificaciones:configurar-umbral');
            END IF;
        END $$;
    """)

    # --- Drop partial indexes ---
    op.execute("DROP INDEX IF EXISTS uq_cal_entrada_materia_actividad_importador")
    op.execute("DROP INDEX IF EXISTS uq_um_asignacion_materia")

    # --- Drop calificacion (references entrada_padron and materia — goes first) ---
    op.drop_index("ix_cal_materia_id",      table_name="calificacion")
    op.drop_index("ix_cal_entrada_padron",  table_name="calificacion")
    op.drop_index("ix_cal_tenant_id",       table_name="calificacion")
    op.drop_table("calificacion")

    # --- Drop umbral_materia ---
    op.drop_index("ix_um_materia_id", table_name="umbral_materia")
    op.drop_index("ix_um_tenant_id",  table_name="umbral_materia")
    op.drop_table("umbral_materia")

    # --- Drop calificacion_origen enum ---
    # Note: ALTER TYPE ... ADD VALUE for audit_action is not reversible in Postgres
    # (same trade-off as 007/004). The CALIFICACIONES_IMPORTAR value remains.
    op.execute("DROP TYPE IF EXISTS calificacion_origen")
