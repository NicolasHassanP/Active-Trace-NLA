"""004 — create audit_event table

Revision ID: 004
Revises: 003
Create Date: 2026-06-03

C-05: Append-only audit log with immutability enforced at both the model
and database layers.

Design decisions implemented:
    D1 — revision="004", down_revision="003".
    D2 — NO updated_at, NO deleted_at; created_at only.
    D3 — Trigger BEFORE UPDATE OR DELETE raises exception (defense in depth).
    D4 — audit_action enum (idempotent creation via DO/EXCEPTION pattern).
    OQ-1 resolved — audit_resultado enum with ok/fail/partial values.
    OQ-3 resolved — entidad_id is VARCHAR nullable.
    OQ-5 resolved — catalog: IMPERSONACION_INICIO, IMPERSONACION_FIN, AUDITORIA_CONSULTA.
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = "004"
down_revision = "003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- Create audit_action enum (idempotent, DO/EXCEPTION pattern from 003) ---
    op.execute(
        "DO $$ BEGIN "
        "  CREATE TYPE audit_action AS ENUM ("
        "    'IMPERSONACION_INICIO', 'IMPERSONACION_FIN', 'AUDITORIA_CONSULTA'"
        "  ); "
        "EXCEPTION WHEN duplicate_object THEN NULL; "
        "END $$;"
    )

    # --- Create audit_resultado enum (idempotent) ---
    op.execute(
        "DO $$ BEGIN "
        "  CREATE TYPE audit_resultado AS ENUM ('ok', 'fail', 'partial'); "
        "EXCEPTION WHEN duplicate_object THEN NULL; "
        "END $$;"
    )

    # --- Create audit_event table ---
    # NO updated_at, NO deleted_at — append-only (D2).
    # tenant_id FK with RESTRICT (event is not orphaned by tenant deletion).
    op.execute("""
        CREATE TABLE IF NOT EXISTS audit_event (
            id                    UUID         NOT NULL DEFAULT gen_random_uuid(),
            tenant_id             UUID         NOT NULL REFERENCES tenants(id) ON DELETE RESTRICT,
            actor_user_id         UUID         NOT NULL,
            impersonated_user_id  UUID,
            accion                audit_action NOT NULL,
            modulo                VARCHAR(100) NOT NULL,
            entidad_tipo          VARCHAR(100) NOT NULL,
            entidad_id            VARCHAR(255),
            resultado             audit_resultado NOT NULL,
            registros_afectados   INTEGER,
            ip                    VARCHAR(45),
            user_agent            VARCHAR(500),
            before                JSONB,
            after                 JSONB,
            created_at            TIMESTAMPTZ  NOT NULL DEFAULT now(),
            PRIMARY KEY (id)
        )
    """)

    # --- Indexes (task 3.4, idempotent) ---
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_audit_event_tenant_created "
        "ON audit_event (tenant_id, created_at)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_audit_event_tenant_actor "
        "ON audit_event (tenant_id, actor_user_id)"
    )

    # --- Immutability trigger (D3, task 3.5, idempotent) ---
    op.execute("""
        CREATE OR REPLACE FUNCTION audit_event_immutable()
        RETURNS TRIGGER AS $$
        BEGIN
            RAISE EXCEPTION
                'audit_event rows are immutable: UPDATE and DELETE are not allowed'
                USING ERRCODE = 'restrict_violation';
        END;
        $$ LANGUAGE plpgsql;
    """)

    op.execute("""
        DO $$ BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_trigger
                WHERE tgname = 'trg_audit_event_immutable'
            ) THEN
                CREATE TRIGGER trg_audit_event_immutable
                BEFORE UPDATE OR DELETE ON audit_event
                FOR EACH ROW EXECUTE FUNCTION audit_event_immutable();
            END IF;
        END $$;
    """)


def downgrade() -> None:
    # Drop in reverse order: trigger → function → indexes → table → enums

    # --- Drop trigger and function ---
    op.execute("DROP TRIGGER IF EXISTS trg_audit_event_immutable ON audit_event")
    op.execute("DROP FUNCTION IF EXISTS audit_event_immutable()")

    # --- Drop indexes (idempotent) ---
    op.execute("DROP INDEX IF EXISTS ix_audit_event_tenant_actor")
    op.execute("DROP INDEX IF EXISTS ix_audit_event_tenant_created")

    # --- Drop table ---
    op.drop_table("audit_event")

    # --- Drop enums ---
    op.execute("DROP TYPE IF EXISTS audit_action CASCADE")
    op.execute("DROP TYPE IF EXISTS audit_resultado CASCADE")
