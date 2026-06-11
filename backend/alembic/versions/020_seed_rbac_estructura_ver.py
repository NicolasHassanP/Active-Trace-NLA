"""020 — seed RBAC permiso estructura:ver

Revision ID: 020
Revises: 019
Create Date: 2026-06-11

Problema raíz: los GET de catálogos (/carreras, /materias, /cohortes) exigían
`estructura:gestionar`, por lo que COORDINADOR —que NO tiene ese permiso— recibía
403 al intentar poblar los <select> de materia/carrera/cohorte.

Solución: un permiso de LECTURA separado `estructura:ver` (scope 'global') que
permite consultar los catálogos sin autorizar mutaciones.  Los POST/PATCH/DELETE
siguen requiriendo `estructura:gestionar`.

Grants (aprobados por el usuario):
    - estructura:ver (modulo=estructura, accion=ver), scope 'global'
        → otorgado a ADMIN y COORDINADOR para todos los tenants existentes.

Design decisions:
    D1 — revision="020", down_revision="019".
    D2 — Seed idempotente per-tenant: SELECT tenants activos, loop,
         ON CONFLICT DO NOTHING.
    D3 — Helper importable `seed_c21_rbac_estructura_ver_for_tenant`
         (mismo estilo que `seed_rbac_for_tenant` en migración 003 y
          `seed_c20_rbac_for_tenant` en migración 018) para testabilidad.
    D4 — Una sola migración para el nuevo permiso + sus grants (regla dura).

CHECKPOINT RBAC: Alta de nuevo permiso y grants (CRÍTICO) — aprobado por el usuario.
  Es idempotente: ON CONFLICT DO NOTHING en cada insert; correrla N veces no duplica.
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = "020"
down_revision = "019"
branch_labels = None
depends_on = None


# Roles que reciben estructura:ver.
_ESTRUCTURA_VER_ROLES = ("ADMIN", "COORDINADOR")


# ---------------------------------------------------------------------------
# Seed helper — idempotent, callable standalone for tests
# ---------------------------------------------------------------------------

def seed_c21_rbac_estructura_ver_for_tenant(conn, tenant_id) -> None:
    """
    Idempotent seed of the estructura:ver permiso + grants for a single tenant.

    Uses INSERT ... ON CONFLICT DO NOTHING on the unique constraints so that
    running this twice on the same tenant produces no duplicates.

    Args:
        conn: a SQLAlchemy *sync* Connection (e.g. op.get_bind() or a run_sync conn).
        tenant_id: the tenant UUID to seed.
    """
    # 1. Seed the permiso.
    conn.execute(
        sa.text("""
            INSERT INTO permiso (id, tenant_id, codigo, modulo, accion, created_at, updated_at)
            VALUES (gen_random_uuid(), :tid, :codigo, :modulo, :accion, now(), now())
            ON CONFLICT ON CONSTRAINT uq_permiso_tenant_codigo DO NOTHING
        """),
        {
            "tid": str(tenant_id),
            "codigo": "estructura:ver",
            "modulo": "estructura",
            "accion": "ver",
        },
    )

    # 2. Grant estructura:ver (scope 'global') a ADMIN y COORDINADOR.
    for rol_nombre in _ESTRUCTURA_VER_ROLES:
        _grant_estructura_ver(conn, tenant_id, rol_nombre)


def _grant_estructura_ver(conn, tenant_id, rol_nombre) -> None:
    """Idempotent grant of estructura:ver to one rol for a tenant."""
    conn.execute(
        sa.text("""
            INSERT INTO rol_permiso (id, tenant_id, rol_id, permiso_id, scope, created_at, updated_at)
            SELECT
                gen_random_uuid(),
                :tid,
                r.id,
                p.id,
                CAST(:scope AS permiso_scope),
                now(),
                now()
            FROM rol r, permiso p
            WHERE r.tenant_id = :tid
              AND r.nombre = :rol_nombre
              AND p.tenant_id = :tid
              AND p.codigo = :permiso_codigo
              AND r.deleted_at IS NULL
              AND p.deleted_at IS NULL
            ON CONFLICT ON CONSTRAINT uq_rol_permiso DO NOTHING
        """),
        {
            "tid": str(tenant_id),
            "rol_nombre": rol_nombre,
            "permiso_codigo": "estructura:ver",
            "scope": "global",
        },
    )


def upgrade() -> None:
    # CHECKPOINT RBAC: alta de estructura:ver para ADMIN y COORDINADOR (CRÍTICO)
    # — idempotente per-tenant.
    conn = op.get_bind()
    tenants = conn.execute(
        sa.text("SELECT id FROM tenants WHERE deleted_at IS NULL")
    ).fetchall()
    for (tid,) in tenants:
        seed_c21_rbac_estructura_ver_for_tenant(conn, tid)


def downgrade() -> None:
    # Revertir grants primero (FK), luego el permiso. Idempotente con guardas IF EXISTS.
    op.execute("""
        DO $$ BEGIN
            IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'rol_permiso')
               AND EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'permiso') THEN
                DELETE FROM rol_permiso
                WHERE permiso_id IN (
                    SELECT id FROM permiso WHERE codigo = 'estructura:ver'
                );
            END IF;
        END $$;
    """)
    op.execute("""
        DO $$ BEGIN
            IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'permiso') THEN
                DELETE FROM permiso WHERE codigo = 'estructura:ver';
            END IF;
        END $$;
    """)
