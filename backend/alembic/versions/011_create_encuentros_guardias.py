"""011 — encuentros y guardias: slot_encuentro, instancia_encuentro, guardia + RBAC

Revision ID: 011
Revises: 010
Create Date: 2026-06-04

C-13: Encuentros y Guardias.

Design decisions:
    D1  — revision="011", down_revision="010".
    D2  — Extend audit_action: ENCUENTRO_GESTIONAR (idempotente DO $$).
    D3  — Enums nuevos: dia_semana, instancia_encuentro_estado, guardia_estado.
    D4  — Tablas: slot_encuentro, instancia_encuentro, guardia (todas tenant-scoped,
          soft-delete, explicit SQL style).
    D5  — Índices con nombres explícitos para FK-heavy tables.
    D6  — Permiso 'encuentros:gestionar' otorgado a PROFESOR, TUTOR,
          COORDINADOR, ADMIN (D9 del design.md) — un solo permiso para todo
          el módulo; diferenciación por rol en el service layer.
    D7  — Seed idempotente ON CONFLICT DO NOTHING por tenant (mismo patrón 010).
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers
revision = "011"
down_revision = "010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- 2.2 Extend audit_action enum idempotently ---
    op.execute(
        "DO $$ BEGIN "
        "  ALTER TYPE audit_action ADD VALUE 'ENCUENTRO_GESTIONAR'; "
        "EXCEPTION WHEN duplicate_object THEN NULL; "
        "END $$;"
    )

    # --- 2.3 Create enums idempotently ---
    op.execute(
        "DO $$ BEGIN "
        "  CREATE TYPE dia_semana AS ENUM "
        "  ('Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo'); "
        "EXCEPTION WHEN duplicate_object THEN NULL; "
        "END $$;"
    )
    op.execute(
        "DO $$ BEGIN "
        "  CREATE TYPE instancia_encuentro_estado AS ENUM "
        "  ('Programado', 'Realizado', 'Cancelado'); "
        "EXCEPTION WHEN duplicate_object THEN NULL; "
        "END $$;"
    )
    op.execute(
        "DO $$ BEGIN "
        "  CREATE TYPE guardia_estado AS ENUM "
        "  ('Pendiente', 'Realizada', 'Cancelada'); "
        "EXCEPTION WHEN duplicate_object THEN NULL; "
        "END $$;"
    )

    # --- 2.4 Create table slot_encuentro ---
    op.execute("""
        CREATE TABLE IF NOT EXISTS slot_encuentro (
            id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id       UUID        NOT NULL REFERENCES tenants(id) ON DELETE RESTRICT,
            asignacion_id   UUID        NOT NULL REFERENCES asignacion(id) ON DELETE RESTRICT,
            materia_id      UUID        NOT NULL REFERENCES materia(id) ON DELETE RESTRICT,
            titulo          TEXT        NOT NULL,
            hora            TIME        NOT NULL,
            dia_semana      dia_semana  NULL,
            fecha_inicio    DATE        NULL,
            cant_semanas    INTEGER     NOT NULL DEFAULT 0,
            fecha_unica     DATE        NULL,
            meet_url        TEXT        NULL,
            vig_desde       DATE        NULL,
            vig_hasta       DATE        NULL,
            created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
            deleted_at      TIMESTAMPTZ NULL
        )
    """)

    # --- 2.5 Create table instancia_encuentro ---
    op.execute("""
        CREATE TABLE IF NOT EXISTS instancia_encuentro (
            id              UUID                        PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id       UUID                        NOT NULL REFERENCES tenants(id) ON DELETE RESTRICT,
            slot_id         UUID                        NULL REFERENCES slot_encuentro(id) ON DELETE SET NULL,
            materia_id      UUID                        NOT NULL REFERENCES materia(id) ON DELETE RESTRICT,
            fecha           DATE                        NOT NULL,
            hora            TIME                        NOT NULL,
            titulo          TEXT                        NOT NULL,
            estado          instancia_encuentro_estado  NOT NULL DEFAULT 'Programado',
            meet_url        TEXT                        NULL,
            video_url       TEXT                        NULL,
            comentario      TEXT                        NOT NULL DEFAULT '',
            created_at      TIMESTAMPTZ                 NOT NULL DEFAULT now(),
            updated_at      TIMESTAMPTZ                 NOT NULL DEFAULT now(),
            deleted_at      TIMESTAMPTZ                 NULL
        )
    """)

    # --- 2.6 Create table guardia ---
    op.execute("""
        CREATE TABLE IF NOT EXISTS guardia (
            id              UUID            PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id       UUID            NOT NULL REFERENCES tenants(id) ON DELETE RESTRICT,
            asignacion_id   UUID            NOT NULL REFERENCES asignacion(id) ON DELETE RESTRICT,
            materia_id      UUID            NOT NULL REFERENCES materia(id) ON DELETE RESTRICT,
            carrera_id      UUID            NOT NULL REFERENCES carrera(id) ON DELETE RESTRICT,
            cohorte_id      UUID            NOT NULL REFERENCES cohorte(id) ON DELETE RESTRICT,
            dia             dia_semana      NOT NULL,
            horario         TEXT            NOT NULL,
            estado          guardia_estado  NOT NULL DEFAULT 'Pendiente',
            comentarios     TEXT            NOT NULL DEFAULT '',
            creada_at       TIMESTAMPTZ     NOT NULL DEFAULT now(),
            created_at      TIMESTAMPTZ     NOT NULL DEFAULT now(),
            updated_at      TIMESTAMPTZ     NOT NULL DEFAULT now(),
            deleted_at      TIMESTAMPTZ     NULL
        )
    """)

    # --- 2.7 Add named indexes ---
    op.execute("CREATE INDEX IF NOT EXISTS ix_slot_tenant_id    ON slot_encuentro(tenant_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_slot_asignacion   ON slot_encuentro(asignacion_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_slot_materia      ON slot_encuentro(materia_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_inst_tenant_id    ON instancia_encuentro(tenant_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_inst_slot         ON instancia_encuentro(slot_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_inst_materia      ON instancia_encuentro(materia_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_inst_fecha        ON instancia_encuentro(fecha)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_guardia_tenant_id ON guardia(tenant_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_guardia_asignacion ON guardia(asignacion_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_guardia_materia   ON guardia(materia_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_guardia_cohorte   ON guardia(cohorte_id)")

    # --- 2.8 Seed permission encuentros:gestionar per-tenant (D6, D9) ---
    conn = op.get_bind()
    tenants = conn.execute(
        sa.text("SELECT id FROM tenants WHERE deleted_at IS NULL")
    ).fetchall()

    for (tid,) in tenants:
        # Insert the permission
        conn.execute(
            sa.text("""
                INSERT INTO permiso (id, tenant_id, codigo, modulo, accion, created_at, updated_at)
                VALUES (gen_random_uuid(), :tid, 'encuentros:gestionar', 'encuentros', 'gestionar', now(), now())
                ON CONFLICT ON CONSTRAINT uq_permiso_tenant_codigo DO NOTHING
            """),
            {"tid": str(tid)},
        )
        # Grant to PROFESOR, TUTOR, COORDINADOR, ADMIN
        for rol_nombre, scope in [
            ("PROFESOR", "global"),
            ("TUTOR", "global"),
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
                      AND p.codigo = 'encuentros:gestionar'
                      AND r.deleted_at IS NULL
                      AND p.deleted_at IS NULL
                    ON CONFLICT ON CONSTRAINT uq_rol_permiso DO NOTHING
                """),
                {"tid": str(tid), "rol_nombre": rol_nombre, "scope": scope},
            )


def downgrade() -> None:
    # Revert seed
    op.execute("""
        DELETE FROM rol_permiso
        WHERE permiso_id IN (
            SELECT id FROM permiso WHERE codigo = 'encuentros:gestionar'
        )
    """)
    op.execute("DELETE FROM permiso WHERE codigo = 'encuentros:gestionar'")

    # Drop tables in FK order
    op.execute("DROP TABLE IF EXISTS instancia_encuentro CASCADE")
    op.execute("DROP TABLE IF EXISTS slot_encuentro CASCADE")
    op.execute("DROP TABLE IF EXISTS guardia CASCADE")

    # Note: enum DROP is not fully reversible when other objects depend on them.
    # They are left in place; ADD VALUE to audit_action is also irreversible.
