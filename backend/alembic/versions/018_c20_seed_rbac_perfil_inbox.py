"""018 — seed C-20 RBAC permisos perfil:editar + inbox:usar

Revision ID: 018
Revises: 017
Create Date: 2026-06-09

C-20: Siembra idempotente per-tenant de los dos permisos del módulo Perfil y
Mensajería interna, que la migración 016 (schema) dejó sin sembrar.

Grants (design.md C-20, OQ-1):
    - perfil:editar (modulo=perfil, accion=editar), scope 'propio'
        → otorgado a TODOS los 7 roles (incluyendo ALUMNO — autoservicio universal).
    - inbox:usar (modulo=inbox, accion=usar), scope 'global'
        → otorgado a todos los roles EXCEPTO ALUMNO
          (TUTOR, PROFESOR, COORDINADOR, NEXO, ADMIN, FINANZAS).

Sin estos grants, los endpoints de inbox.py (require_permission("inbox:usar")) y
el PATCH de perfil.py (require_permission("perfil:editar")) devuelven 403 en
producción para todos los usuarios (fail-closed).

Design decisions:
    D1 — revision="018", down_revision="017".
    D2 — Seed idempotente per-tenant: SELECT tenants activos, loop, ON CONFLICT DO NOTHING.
    D3 — Lógica de seed expuesta como helper importable `seed_c20_rbac_for_tenant`
         (mismo estilo que `seed_rbac_for_tenant` en migración 003) para testabilidad.

CHECKPOINT RBAC: El alta de estos grants toca RBAC (CRÍTICO) — aprobado por el usuario.
  Es idempotente: ON CONFLICT DO NOTHING en cada insert; correrla N veces no duplica.
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = "018"
down_revision = "017"
branch_labels = None
depends_on = None


# Roles que reciben inbox:usar (todos menos ALUMNO).
_INBOX_ROLES = ("TUTOR", "PROFESOR", "COORDINADOR", "NEXO", "ADMIN", "FINANZAS")

# Roles que reciben perfil:editar (los 7, incluyendo ALUMNO).
_PERFIL_ROLES = ("ALUMNO", "TUTOR", "PROFESOR", "COORDINADOR", "NEXO", "ADMIN", "FINANZAS")


# ---------------------------------------------------------------------------
# Seed helper — idempotent, callable standalone for tests
# ---------------------------------------------------------------------------

def seed_c20_rbac_for_tenant(conn, tenant_id) -> None:
    """
    Idempotent seed of the C-20 permisos + grants for a single tenant.

    Uses INSERT ... ON CONFLICT DO NOTHING on the unique constraints so that
    running this twice on the same tenant produces no duplicates.

    Args:
        conn: a SQLAlchemy *sync* Connection (e.g. op.get_bind() or a run_sync conn).
        tenant_id: the tenant UUID to seed.
    """
    # 1. Seed the two permisos.
    for codigo, modulo, accion in (
        ("perfil:editar", "perfil", "editar"),
        ("inbox:usar", "inbox", "usar"),
    ):
        conn.execute(
            sa.text("""
                INSERT INTO permiso (id, tenant_id, codigo, modulo, accion, created_at, updated_at)
                VALUES (gen_random_uuid(), :tid, :codigo, :modulo, :accion, now(), now())
                ON CONFLICT ON CONSTRAINT uq_permiso_tenant_codigo DO NOTHING
            """),
            {"tid": str(tenant_id), "codigo": codigo, "modulo": modulo, "accion": accion},
        )

    # 2. Grant perfil:editar (scope 'propio') a los 7 roles.
    for rol_nombre in _PERFIL_ROLES:
        _grant(conn, tenant_id, rol_nombre, "perfil:editar", "propio")

    # 3. Grant inbox:usar (scope 'global') a todos menos ALUMNO.
    for rol_nombre in _INBOX_ROLES:
        _grant(conn, tenant_id, rol_nombre, "inbox:usar", "global")


def _grant(conn, tenant_id, rol_nombre, permiso_codigo, scope) -> None:
    """Idempotent grant of one permiso to one rol for a tenant."""
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
            "permiso_codigo": permiso_codigo,
            "scope": scope,
        },
    )


def upgrade() -> None:
    # CHECKPOINT RBAC: alta de grants C-20 (CRÍTICO) — idempotente per-tenant.
    conn = op.get_bind()
    tenants = conn.execute(
        sa.text("SELECT id FROM tenants WHERE deleted_at IS NULL")
    ).fetchall()
    for (tid,) in tenants:
        seed_c20_rbac_for_tenant(conn, tid)


def downgrade() -> None:
    # Revertir grants primero (FK), luego los permisos. Idempotente con guardas IF EXISTS.
    op.execute("""
        DO $$ BEGIN
            IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'rol_permiso')
               AND EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'permiso') THEN
                DELETE FROM rol_permiso
                WHERE permiso_id IN (
                    SELECT id FROM permiso WHERE codigo IN ('perfil:editar', 'inbox:usar')
                );
            END IF;
        END $$;
    """)
    op.execute("""
        DO $$ BEGIN
            IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'permiso') THEN
                DELETE FROM permiso WHERE codigo IN ('perfil:editar', 'inbox:usar');
            END IF;
        END $$;
    """)
