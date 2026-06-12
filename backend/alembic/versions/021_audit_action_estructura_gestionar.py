"""021 — add ESTRUCTURA_GESTIONAR to audit_action enum

Revision ID: 021
Revises: 020
Create Date: 2026-06-12

Problema raíz: el ABM de estructura académica (Carrera, Materia, Cohorte)
no emitía AuditEvent, dejando un gap de trazabilidad en C-06.

Solución: agregar el valor ESTRUCTURA_GESTIONAR al enum audit_action
para que EstructuraService pueda emitir eventos de auditoría en
crear/editar/dar-baja de las tres entidades.

Design decisions:
    D1 — revision="021", down_revision="020".
    D2 — ALTER TYPE ... ADD VALUE IF NOT EXISTS dentro de la transacción
         (Postgres 16 lo soporta; el valor no se usa en la misma tx → OK).
    D3 — downgrade() es no-op: Postgres no soporta DROP VALUE en un enum.
         Mismo criterio que migraciones 007, 008, 009, 010, 011, 012, 014, 016, 017, 019.
"""
from alembic import op

# revision identifiers
revision = "021"
down_revision = "020"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "ALTER TYPE audit_action ADD VALUE IF NOT EXISTS 'ESTRUCTURA_GESTIONAR'"
    )


def downgrade() -> None:
    # Postgres does not support DROP VALUE from an enum type.
    # No-op intentional — same convention as all previous audit_action migrations.
    pass
