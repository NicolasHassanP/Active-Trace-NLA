"""017 — C-27 historial comunicaciones: índice compuesto por sender

Revision ID: 017
Revises: 016
Create Date: 2026-06-07

C-27: Historial de comunicaciones propias del remitente.

Design decisions:
    D1 — revision="017", down_revision="016".
    D2 — Agrega índice compuesto (tenant_id, enviado_por, created_at DESC) sobre
         la tabla comunicacion. Solo índice — sin cambio de schema (enviado_por
         ya existe desde migración 009).
    D3 — Índice parcial WHERE deleted_at IS NULL para excluir soft-deleted
         y mantener el índice compacto.
    D4 — CREATE INDEX IF NOT EXISTS para idempotencia en ambientes existentes.
    D5 — downgrade: DROP INDEX IF EXISTS.
"""
from alembic import op


# revision identifiers
revision = "017"
down_revision = "016"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Índice compuesto para la query GET /comunicaciones/mis-envios.
    # La query filtra por tenant_id AND enviado_por AND deleted_at IS NULL,
    # ordenando por created_at DESC. Este índice cubre exactamente ese hot path.
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_comunicacion_tenant_enviado_por_created "
        "ON comunicacion (tenant_id, enviado_por, created_at DESC) "
        "WHERE deleted_at IS NULL"
    )


def downgrade() -> None:
    op.execute(
        "DROP INDEX IF EXISTS ix_comunicacion_tenant_enviado_por_created"
    )
