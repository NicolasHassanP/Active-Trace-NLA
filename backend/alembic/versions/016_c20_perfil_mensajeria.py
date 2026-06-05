"""016 — C-20 perfil y mensajería interna

Revision ID: 016
Revises: 015
Create Date: 2026-06-05

C-20: Perfil propio + Mensajería interna (F11.1, F11.2, F3.4).

Design decisions:
    D1  — revision="016", down_revision="015".
    D2  — ADD COLUMN genero VARCHAR(50) nullable en usuario (OQ-2 cerrada).
    D4  — CREATE TABLE hilos_mensaje, mensajes, hilo_participantes.
    D8  — Extend audit_action: PERFIL_EDITAR (idempotente).
    D5  — Índices: (tenant_id, usuario_id) en participantes,
                   (tenant_id, hilo_id, created_at) en mensajes.
    D6  — downgrade: DROP COLUMN genero, DROP TABLE mensajes/participantes/hilos.
          Los valores de audit_action NO son reversibles en PostgreSQL.
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers
revision = "016"
down_revision = "015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- D2: ADD COLUMN genero a tabla usuario (OQ-2 — columna no existía) ---
    op.execute(
        "ALTER TABLE usuario ADD COLUMN IF NOT EXISTS genero VARCHAR(50)"
    )

    # --- D8: Extend audit_action enum idempotently ---
    op.execute(
        "DO $$ BEGIN "
        "  ALTER TYPE audit_action ADD VALUE 'PERFIL_EDITAR'; "
        "EXCEPTION WHEN duplicate_object THEN NULL; "
        "END $$;"
    )

    # --- D4: Create table hilos_mensaje ---
    op.execute("""
        CREATE TABLE IF NOT EXISTS hilos_mensaje (
            id         UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id  UUID         NOT NULL REFERENCES tenants(id) ON DELETE RESTRICT,
            asunto     VARCHAR(255) NULL,
            created_at TIMESTAMPTZ  NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ  NOT NULL DEFAULT now(),
            deleted_at TIMESTAMPTZ  NULL
        )
    """)

    # --- D4: Create table mensajes ---
    op.execute("""
        CREATE TABLE IF NOT EXISTS mensajes (
            id           UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id    UUID         NOT NULL REFERENCES tenants(id) ON DELETE RESTRICT,
            hilo_id      UUID         NOT NULL REFERENCES hilos_mensaje(id) ON DELETE RESTRICT,
            remitente_id UUID         NOT NULL REFERENCES usuario(id) ON DELETE RESTRICT,
            asunto       VARCHAR(255) NOT NULL,
            cuerpo       TEXT         NOT NULL,
            created_at   TIMESTAMPTZ  NOT NULL DEFAULT now(),
            updated_at   TIMESTAMPTZ  NOT NULL DEFAULT now(),
            deleted_at   TIMESTAMPTZ  NULL
        )
    """)

    # --- D4: Create table hilo_participantes (PK compuesta: hilo_id + usuario_id) ---
    op.execute("""
        CREATE TABLE IF NOT EXISTS hilo_participantes (
            hilo_id      UUID        NOT NULL REFERENCES hilos_mensaje(id) ON DELETE CASCADE,
            usuario_id   UUID        NOT NULL REFERENCES usuario(id) ON DELETE RESTRICT,
            tenant_id    UUID        NOT NULL REFERENCES tenants(id) ON DELETE RESTRICT,
            last_read_at TIMESTAMPTZ NULL,
            PRIMARY KEY (hilo_id, usuario_id)
        )
    """)

    # --- D5: Índices de aislamiento y hot paths ---
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_hilos_mensaje_tenant_id "
        "ON hilos_mensaje (tenant_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_mensajes_tenant_hilo_at "
        "ON mensajes (tenant_id, hilo_id, created_at)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_mensajes_hilo_id "
        "ON mensajes (hilo_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_hilo_participantes_tenant_usuario "
        "ON hilo_participantes (tenant_id, usuario_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_hilo_participantes_hilo_id "
        "ON hilo_participantes (hilo_id)"
    )


def _seed_rbac_permissions(conn) -> None:
    """
    Seed idempotente de los permisos C-20 en el catálogo RBAC.

    - perfil:editar → otorgado a TODOS los roles (incluyendo ALUMNO). OQ-1.
    - inbox:usar   → TUTOR/PROFESOR/COORDINADOR/NEXO/ADMIN/FINANZAS. ALUMNO excluido.

    Esta función debe ser llamada después de upgrade() para cada tenant existente,
    o bien desde un script de seed separado. No se llama automáticamente desde
    Alembic para no acoplar la migración de schema a datos variables por tenant.
    """
    pass  # Implementar en script de seed multi-tenant por tenant_id


def downgrade() -> None:
    # Drop indexes
    op.execute("DROP INDEX IF EXISTS ix_hilo_participantes_hilo_id")
    op.execute("DROP INDEX IF EXISTS ix_hilo_participantes_tenant_usuario")
    op.execute("DROP INDEX IF EXISTS ix_mensajes_hilo_id")
    op.execute("DROP INDEX IF EXISTS ix_mensajes_tenant_hilo_at")
    op.execute("DROP INDEX IF EXISTS ix_hilos_mensaje_tenant_id")

    # Drop tables in FK order
    op.execute("DROP TABLE IF EXISTS hilo_participantes CASCADE")
    op.execute("DROP TABLE IF EXISTS mensajes CASCADE")
    op.execute("DROP TABLE IF EXISTS hilos_mensaje CASCADE")

    # Drop genero column from usuario
    op.execute("ALTER TABLE usuario DROP COLUMN IF EXISTS genero")

    # Note: PERFIL_EDITAR added to audit_action is NOT reversible.
    # The value remains in the audit_action type after downgrade — inocuous.
