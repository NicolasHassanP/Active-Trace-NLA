"""012 — evaluaciones y coloquios: tablas + RBAC

Revision ID: 012
Revises: 011
Create Date: 2026-06-04

C-14: Evaluaciones y Coloquios.

Design decisions:
    D1  — revision="012", down_revision="011".
    D2  — Extend audit_action: COLOQUIO_GESTIONAR (idempotente DO $$).
    D3  — Nuevos enums: evaluacion_tipo, reserva_estado (idempotentes).
    D4  — Tablas en orden FK: evaluacion → turno_evaluacion → candidato_evaluacion
          → reserva_evaluacion → resultado_evaluacion (todas tenant-scoped, soft-delete).
    D5  — Índices con nombres explícitos.
    D6  — Índice parcial único en reserva_evaluacion para una reserva Activa
          por (tenant_id, evaluacion_id, alumno_id) — defensa en profundidad (D4 design).
    D7  — Seed RBAC: 'coloquios:gestionar' (COORDINADOR, ADMIN, PROFESOR) y
          'coloquios:reservar' (ALUMNO) por tenant con ON CONFLICT DO NOTHING.
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers
revision = "012"
down_revision = "011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- D2: Extend audit_action enum idempotently ---
    op.execute(
        "DO $$ BEGIN "
        "  ALTER TYPE audit_action ADD VALUE 'COLOQUIO_GESTIONAR'; "
        "EXCEPTION WHEN duplicate_object THEN NULL; "
        "END $$;"
    )

    # --- D3: Create enums idempotently ---
    op.execute(
        "DO $$ BEGIN "
        "  CREATE TYPE evaluacion_tipo AS ENUM "
        "  ('Parcial', 'TP', 'Coloquio', 'Recuperatorio'); "
        "EXCEPTION WHEN duplicate_object THEN NULL; "
        "END $$;"
    )
    op.execute(
        "DO $$ BEGIN "
        "  CREATE TYPE reserva_estado AS ENUM "
        "  ('Activa', 'Cancelada'); "
        "EXCEPTION WHEN duplicate_object THEN NULL; "
        "END $$;"
    )

    # --- D4: Create table evaluacion ---
    op.execute("""
        CREATE TABLE IF NOT EXISTS evaluacion (
            id               UUID             PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id        UUID             NOT NULL REFERENCES tenants(id) ON DELETE RESTRICT,
            materia_id       UUID             NOT NULL REFERENCES materia(id) ON DELETE RESTRICT,
            cohorte_id       UUID             NOT NULL REFERENCES cohorte(id) ON DELETE RESTRICT,
            tipo             evaluacion_tipo  NOT NULL,
            instancia        TEXT             NOT NULL,
            dias_disponibles INTEGER          NOT NULL DEFAULT 0,
            cerrada          BOOLEAN          NOT NULL DEFAULT FALSE,
            created_at       TIMESTAMPTZ      NOT NULL DEFAULT now(),
            updated_at       TIMESTAMPTZ      NOT NULL DEFAULT now(),
            deleted_at       TIMESTAMPTZ      NULL
        )
    """)

    # --- D4: Create table turno_evaluacion ---
    op.execute("""
        CREATE TABLE IF NOT EXISTS turno_evaluacion (
            id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id       UUID        NOT NULL REFERENCES tenants(id) ON DELETE RESTRICT,
            evaluacion_id   UUID        NOT NULL REFERENCES evaluacion(id) ON DELETE RESTRICT,
            fecha           DATE        NOT NULL,
            cupo_total      INTEGER     NOT NULL,
            franja          TEXT        NULL,
            created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
            deleted_at      TIMESTAMPTZ NULL
        )
    """)

    # --- D4: Create table candidato_evaluacion ---
    op.execute("""
        CREATE TABLE IF NOT EXISTS candidato_evaluacion (
            id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id       UUID        NOT NULL REFERENCES tenants(id) ON DELETE RESTRICT,
            evaluacion_id   UUID        NOT NULL REFERENCES evaluacion(id) ON DELETE RESTRICT,
            alumno_id       UUID        NOT NULL REFERENCES usuario(id) ON DELETE RESTRICT,
            created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
            deleted_at      TIMESTAMPTZ NULL
        )
    """)

    # --- D4: Create table reserva_evaluacion ---
    op.execute("""
        CREATE TABLE IF NOT EXISTS reserva_evaluacion (
            id              UUID            PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id       UUID            NOT NULL REFERENCES tenants(id) ON DELETE RESTRICT,
            turno_id        UUID            NOT NULL REFERENCES turno_evaluacion(id) ON DELETE RESTRICT,
            evaluacion_id   UUID            NOT NULL REFERENCES evaluacion(id) ON DELETE RESTRICT,
            alumno_id       UUID            NOT NULL REFERENCES usuario(id) ON DELETE RESTRICT,
            estado          reserva_estado  NOT NULL DEFAULT 'Activa',
            created_at      TIMESTAMPTZ     NOT NULL DEFAULT now(),
            updated_at      TIMESTAMPTZ     NOT NULL DEFAULT now(),
            deleted_at      TIMESTAMPTZ     NULL
        )
    """)

    # --- D4: Create table resultado_evaluacion ---
    op.execute("""
        CREATE TABLE IF NOT EXISTS resultado_evaluacion (
            id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id       UUID        NOT NULL REFERENCES tenants(id) ON DELETE RESTRICT,
            evaluacion_id   UUID        NOT NULL REFERENCES evaluacion(id) ON DELETE RESTRICT,
            alumno_id       UUID        NOT NULL REFERENCES usuario(id) ON DELETE RESTRICT,
            nota_final      TEXT        NULL,
            created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
            deleted_at      TIMESTAMPTZ NULL
        )
    """)

    # --- D5: Named indexes ---
    op.execute("CREATE INDEX IF NOT EXISTS ix_evaluacion_tenant_id    ON evaluacion(tenant_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_evaluacion_materia_id   ON evaluacion(materia_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_evaluacion_cohorte_id   ON evaluacion(cohorte_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_turno_tenant_id         ON turno_evaluacion(tenant_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_turno_evaluacion_id     ON turno_evaluacion(evaluacion_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_turno_fecha             ON turno_evaluacion(fecha)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_candidato_tenant_id     ON candidato_evaluacion(tenant_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_candidato_evaluacion_id ON candidato_evaluacion(evaluacion_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_candidato_alumno_id     ON candidato_evaluacion(alumno_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_reserva_tenant_id       ON reserva_evaluacion(tenant_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_reserva_turno_id        ON reserva_evaluacion(turno_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_reserva_evaluacion_id   ON reserva_evaluacion(evaluacion_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_reserva_alumno_id       ON reserva_evaluacion(alumno_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_resultado_tenant_id     ON resultado_evaluacion(tenant_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_resultado_evaluacion_id ON resultado_evaluacion(evaluacion_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_resultado_alumno_id     ON resultado_evaluacion(alumno_id)")

    # --- D6: Partial unique index for one active reservation per (alumno, convocatoria) ---
    op.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS uq_reserva_activa_por_convocatoria
        ON reserva_evaluacion (tenant_id, evaluacion_id, alumno_id)
        WHERE estado = 'Activa' AND deleted_at IS NULL
    """)

    # --- D7: Seed RBAC permissions per-tenant ---
    conn = op.get_bind()
    tenants = conn.execute(
        sa.text("SELECT id FROM tenants WHERE deleted_at IS NULL")
    ).fetchall()

    for (tid,) in tenants:
        # Insert coloquios:gestionar permission
        conn.execute(
            sa.text("""
                INSERT INTO permiso (id, tenant_id, codigo, modulo, accion, created_at, updated_at)
                VALUES (gen_random_uuid(), :tid, 'coloquios:gestionar', 'coloquios', 'gestionar', now(), now())
                ON CONFLICT ON CONSTRAINT uq_permiso_tenant_codigo DO NOTHING
            """),
            {"tid": str(tid)},
        )
        # Insert coloquios:reservar permission
        conn.execute(
            sa.text("""
                INSERT INTO permiso (id, tenant_id, codigo, modulo, accion, created_at, updated_at)
                VALUES (gen_random_uuid(), :tid, 'coloquios:reservar', 'coloquios', 'reservar', now(), now())
                ON CONFLICT ON CONSTRAINT uq_permiso_tenant_codigo DO NOTHING
            """),
            {"tid": str(tid)},
        )
        # Grant coloquios:gestionar to COORDINADOR, ADMIN, PROFESOR
        for rol_nombre in ("COORDINADOR", "ADMIN", "PROFESOR"):
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
                      AND p.codigo = 'coloquios:gestionar'
                      AND r.deleted_at IS NULL
                      AND p.deleted_at IS NULL
                    ON CONFLICT ON CONSTRAINT uq_rol_permiso DO NOTHING
                """),
                {"tid": str(tid), "rol_nombre": rol_nombre},
            )
        # Grant coloquios:reservar to ALUMNO
        conn.execute(
            sa.text("""
                INSERT INTO rol_permiso (id, tenant_id, rol_id, permiso_id, scope, created_at, updated_at)
                SELECT
                    gen_random_uuid(), :tid, r.id, p.id,
                    CAST('global' AS permiso_scope), now(), now()
                FROM rol r, permiso p
                WHERE r.tenant_id = :tid
                  AND r.nombre = 'ALUMNO'
                  AND p.tenant_id = :tid
                  AND p.codigo = 'coloquios:reservar'
                  AND r.deleted_at IS NULL
                  AND p.deleted_at IS NULL
                ON CONFLICT ON CONSTRAINT uq_rol_permiso DO NOTHING
            """),
            {"tid": str(tid)},
        )


def downgrade() -> None:
    # Revert seed
    op.execute("""
        DO $$ BEGIN
            IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'rol_permiso') THEN
                DELETE FROM rol_permiso
                WHERE permiso_id IN (
                    SELECT id FROM permiso WHERE codigo IN ('coloquios:gestionar', 'coloquios:reservar')
                );
            END IF;
        END $$;
    """)
    op.execute("""
        DO $$ BEGIN
            IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'permiso') THEN
                DELETE FROM permiso WHERE codigo IN ('coloquios:gestionar', 'coloquios:reservar');
            END IF;
        END $$;
    """)

    # Drop partial unique index
    op.execute("DROP INDEX IF EXISTS uq_reserva_activa_por_convocatoria")

    # Drop tables in FK order (most dependent first)
    op.execute("DROP TABLE IF EXISTS reserva_evaluacion CASCADE")
    op.execute("DROP TABLE IF EXISTS resultado_evaluacion CASCADE")
    op.execute("DROP TABLE IF EXISTS candidato_evaluacion CASCADE")
    op.execute("DROP TABLE IF EXISTS turno_evaluacion CASCADE")
    op.execute("DROP TABLE IF EXISTS evaluacion CASCADE")

    # Drop enums
    op.execute("DROP TYPE IF EXISTS reserva_estado CASCADE")
    op.execute("DROP TYPE IF EXISTS evaluacion_tipo CASCADE")

    # Note: COLOQUIO_GESTIONAR added to audit_action is not reversible (same as 011).
