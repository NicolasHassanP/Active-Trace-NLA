"""019 — umbral_materia: scope global ADMIN (asignacion_id nullable + cohorte_id)

Revision ID: 019
Revises: 018
Create Date: 2026-06-10

C-19/feature: ADMIN tiene scope global pero los endpoints de umbral exigían
asignación propia → error 500 crudo. Solución:
    - asignacion_id pasa a nullable (NULL = default por materia/cohorte, scope ADMIN global).
    - Nueva columna cohorte_id (nullable) para diferenciar defaults por cohorte.
    - DROP el índice único viejo uq_um_asignacion_materia.
    - CREATE dos índices únicos parciales:
        uq_um_default_materia_cohorte: (tenant_id, materia_id, cohorte_id) WHERE asignacion_id IS NULL
        uq_um_asignacion_override:     (tenant_id, asignacion_id, materia_id) WHERE asignacion_id IS NOT NULL
    - Data migration: filas existentes mantienen su asignacion_id (se vuelven overrides).
    - Downgrade: reversa completa.

Design decisions:
    D1 — revision="019", down_revision="018".
    D2 — asignacion_id nullable via ALTER COLUMN (no recrear tabla).
    D3 — cohorte_id added as nullable FK RESTRICT → cohorte(id).
    D4 — Dos índices parciales reemplazan el único viejo: semántica default vs override.
    D5 — Data migration: filas viejas (asignacion_id NOT NULL) → overrides sin tocar.
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers
revision = "019"
down_revision = "018"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Add cohorte_id column (nullable FK → cohorte)
    op.execute("""
        ALTER TABLE umbral_materia
        ADD COLUMN IF NOT EXISTS cohorte_id UUID
            REFERENCES cohorte(id) ON DELETE RESTRICT
    """)
    op.create_index("ix_um_cohorte_id", "umbral_materia", ["cohorte_id"])

    # 2. Make asignacion_id nullable (existing rows keep their value = overrides)
    op.execute("""
        ALTER TABLE umbral_materia
        ALTER COLUMN asignacion_id DROP NOT NULL
    """)

    # 3. Drop old unique index (enforced NOT NULL + (tenant, asignacion, materia))
    op.execute("DROP INDEX IF EXISTS uq_um_asignacion_materia")

    # 4. Create two partial unique indexes replacing the old one:
    #    a) Default per (tenant, materia, cohorte) where no asignacion (scope global)
    op.execute("""
        CREATE UNIQUE INDEX uq_um_default_materia_cohorte
        ON umbral_materia(tenant_id, materia_id, cohorte_id)
        WHERE asignacion_id IS NULL AND deleted_at IS NULL
    """)
    #    b) Override per (tenant, asignacion, materia) where asignacion exists (scope propio)
    op.execute("""
        CREATE UNIQUE INDEX uq_um_asignacion_override
        ON umbral_materia(tenant_id, asignacion_id, materia_id)
        WHERE asignacion_id IS NOT NULL AND deleted_at IS NULL
    """)
    # Note: existing rows (asignacion_id IS NOT NULL) are automatically covered by
    # uq_um_asignacion_override. No data migration needed — they become overrides.


def downgrade() -> None:
    # 1. Restore the old partial unique index (only works if no NULL asignacion_id rows exist)
    #    Rows with NULL asignacion_id must be deleted first to restore NOT NULL constraint.
    op.execute("DELETE FROM umbral_materia WHERE asignacion_id IS NULL")

    # 2. Drop new partial indexes
    op.execute("DROP INDEX IF EXISTS uq_um_default_materia_cohorte")
    op.execute("DROP INDEX IF EXISTS uq_um_asignacion_override")

    # 3. Restore NOT NULL on asignacion_id
    op.execute("""
        ALTER TABLE umbral_materia
        ALTER COLUMN asignacion_id SET NOT NULL
    """)

    # 4. Restore original unique index
    op.execute("""
        CREATE UNIQUE INDEX uq_um_asignacion_materia
        ON umbral_materia(tenant_id, asignacion_id, materia_id)
        WHERE deleted_at IS NULL
    """)

    # 5. Drop cohorte_id column
    op.drop_index("ix_um_cohorte_id", table_name="umbral_materia")
    op.execute("ALTER TABLE umbral_materia DROP COLUMN IF EXISTS cohorte_id")
