"""003 — create rbac tables

Revision ID: 003
Revises: 002
Create Date: 2026-06-03

C-04: Fine-grained RBAC catalog.
Three tenant-scoped tables: rol, permiso, rol_permiso.
Enum: permiso_scope ('global', 'propio').

Design decisions:
    D1 — revision 003, not 002 (002 already used by C-03 auth tables).
    D2 — all tables tenant-scoped; seed replicated per existing tenant.
    D4 — scope column in rol_permiso (not in permiso code).
    D6 — seed idempotent via INSERT ... ON CONFLICT DO NOTHING.
    D7 — UniqueConstraints: (tenant_id, nombre), (tenant_id, codigo),
          (tenant_id, rol_id, permiso_id). Explicit indexes on every FK.

Matrix §3.3 (knowledge-base/03_actores_y_roles.md):
    NEXO: exactly one permission avisos:confirmar (global) — OQ-4 resolved.
    All other roles: full matrix as per §3.3.
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None


# ---------------------------------------------------------------------------
# Permission matrix — derived literally from KB §3.3
# Format: (role_name, permission_code, scope)
# scope: "global" or "propio"
# ---------------------------------------------------------------------------

# All permissions defined in the system
_PERMISOS = [
    # (codigo, modulo, accion)
    ("academico:ver_propio",        "academico",       "ver_propio"),
    ("evaluacion:reservar",         "evaluacion",      "reservar"),
    ("avisos:confirmar",            "avisos",          "confirmar"),
    ("calificaciones:importar",     "calificaciones",  "importar"),
    ("atrasados:ver",               "atrasados",       "ver"),
    ("entregas:ver_sin_corregir",   "entregas",        "ver_sin_corregir"),
    ("comunicacion:enviar",         "comunicacion",    "enviar"),
    ("comunicacion:aprobar",        "comunicacion",    "aprobar"),
    ("encuentros:gestionar",        "encuentros",      "gestionar"),
    ("guardias:registrar",          "guardias",        "registrar"),
    ("tareas:gestionar",            "tareas",          "gestionar"),
    ("avisos:publicar",             "avisos",          "publicar"),
    ("equipos:asignar",             "equipos",         "asignar"),
    ("estructura:gestionar",        "estructura",      "gestionar"),
    ("usuarios:gestionar",          "usuarios",        "gestionar"),
    ("auditoria:ver",               "auditoria",       "ver"),
    ("liquidaciones:operar_grilla", "liquidaciones",   "operar_grilla"),
    ("liquidaciones:cerrar",        "liquidaciones",   "cerrar"),
    ("facturas:gestionar",          "facturas",        "gestionar"),
    ("tenant:configurar",           "tenant",          "configurar"),
    ("impersonacion:usar",          "impersonacion",   "usar"),
]

# Role → permission grants: (role_name, permission_code, scope)
# Derived literally from §3.3. NEXO: single permission per OQ-4.
_MATRIZ = [
    # ALUMNO
    ("ALUMNO", "academico:ver_propio",      "global"),
    ("ALUMNO", "evaluacion:reservar",       "global"),
    ("ALUMNO", "avisos:confirmar",          "global"),

    # TUTOR
    ("TUTOR", "avisos:confirmar",           "global"),
    ("TUTOR", "atrasados:ver",              "global"),
    ("TUTOR", "entregas:ver_sin_corregir",  "global"),
    ("TUTOR", "encuentros:gestionar",       "global"),
    ("TUTOR", "guardias:registrar",         "propio"),

    # PROFESOR
    ("PROFESOR", "avisos:confirmar",        "global"),
    ("PROFESOR", "calificaciones:importar", "propio"),
    ("PROFESOR", "atrasados:ver",           "propio"),
    ("PROFESOR", "entregas:ver_sin_corregir", "propio"),
    ("PROFESOR", "comunicacion:enviar",     "propio"),
    ("PROFESOR", "encuentros:gestionar",    "propio"),
    ("PROFESOR", "guardias:registrar",      "propio"),
    ("PROFESOR", "tareas:gestionar",        "propio"),

    # COORDINADOR
    ("COORDINADOR", "avisos:confirmar",         "global"),
    ("COORDINADOR", "calificaciones:importar",  "global"),
    ("COORDINADOR", "atrasados:ver",            "global"),
    ("COORDINADOR", "entregas:ver_sin_corregir","global"),
    ("COORDINADOR", "comunicacion:enviar",      "global"),
    ("COORDINADOR", "comunicacion:aprobar",     "global"),
    ("COORDINADOR", "encuentros:gestionar",     "global"),
    ("COORDINADOR", "guardias:registrar",       "global"),
    ("COORDINADOR", "tareas:gestionar",         "global"),
    ("COORDINADOR", "avisos:publicar",          "global"),
    ("COORDINADOR", "equipos:asignar",          "global"),
    ("COORDINADOR", "auditoria:ver",            "propio"),

    # NEXO — OQ-4 resolved: single permission, everything else fail-closed
    ("NEXO", "avisos:confirmar", "global"),

    # ADMIN
    ("ADMIN", "avisos:confirmar",           "global"),
    ("ADMIN", "calificaciones:importar",    "global"),
    ("ADMIN", "atrasados:ver",              "global"),
    ("ADMIN", "entregas:ver_sin_corregir",  "global"),
    ("ADMIN", "comunicacion:enviar",        "global"),
    ("ADMIN", "comunicacion:aprobar",       "global"),
    ("ADMIN", "encuentros:gestionar",       "global"),
    ("ADMIN", "guardias:registrar",         "global"),
    ("ADMIN", "tareas:gestionar",           "global"),
    ("ADMIN", "avisos:publicar",            "global"),
    ("ADMIN", "equipos:asignar",            "global"),
    ("ADMIN", "estructura:gestionar",       "global"),
    ("ADMIN", "usuarios:gestionar",         "global"),
    ("ADMIN", "auditoria:ver",              "global"),
    ("ADMIN", "tenant:configurar",          "global"),
    ("ADMIN", "impersonacion:usar",         "global"),

    # FINANZAS
    ("FINANZAS", "avisos:confirmar",            "global"),
    ("FINANZAS", "auditoria:ver",               "global"),
    ("FINANZAS", "liquidaciones:operar_grilla", "global"),
    ("FINANZAS", "liquidaciones:cerrar",        "global"),
    ("FINANZAS", "facturas:gestionar",          "global"),
]

_ROLES = ["ALUMNO", "TUTOR", "PROFESOR", "COORDINADOR", "NEXO", "ADMIN", "FINANZAS"]


# ---------------------------------------------------------------------------
# Seed helper — idempotent, callable standalone for tests
# ---------------------------------------------------------------------------

def seed_rbac_for_tenant(conn, tenant_id) -> None:
    """
    Idempotent seed: insert roles, permisos and rol_permiso for a single tenant.

    Uses INSERT ... ON CONFLICT DO NOTHING on the unique constraints so that
    running this twice on the same tenant produces no duplicates.
    """
    import uuid as _uuid

    # 1. Seed roles
    for rol_nombre in _ROLES:
        conn.execute(
            sa.text("""
                INSERT INTO rol (id, tenant_id, nombre, created_at, updated_at)
                VALUES (gen_random_uuid(), :tid, :nombre, now(), now())
                ON CONFLICT ON CONSTRAINT uq_rol_tenant_nombre DO NOTHING
            """),
            {"tid": str(tenant_id), "nombre": rol_nombre},
        )

    # 2. Seed permisos
    for codigo, modulo, accion in _PERMISOS:
        conn.execute(
            sa.text("""
                INSERT INTO permiso (id, tenant_id, codigo, modulo, accion, created_at, updated_at)
                VALUES (gen_random_uuid(), :tid, :codigo, :modulo, :accion, now(), now())
                ON CONFLICT ON CONSTRAINT uq_permiso_tenant_codigo DO NOTHING
            """),
            {"tid": str(tenant_id), "codigo": codigo, "modulo": modulo, "accion": accion},
        )

    # 3. Seed rol_permiso
    for rol_nombre, permiso_codigo, scope in _MATRIZ:
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
    # --- Create permiso_scope enum (idempotent) ---
    op.execute(
        "DO $$ BEGIN "
        "  CREATE TYPE permiso_scope AS ENUM ('global', 'propio'); "
        "EXCEPTION WHEN duplicate_object THEN NULL; "
        "END $$;"
    )

    # --- rol table ---
    op.execute("""
        CREATE TABLE rol (
            id          UUID        NOT NULL DEFAULT gen_random_uuid(),
            tenant_id   UUID        NOT NULL REFERENCES tenants(id) ON DELETE RESTRICT,
            nombre      VARCHAR(50) NOT NULL,
            descripcion VARCHAR(255),
            created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
            deleted_at  TIMESTAMPTZ,
            PRIMARY KEY (id)
        )
    """)
    op.create_unique_constraint("uq_rol_tenant_nombre", "rol", ["tenant_id", "nombre"])
    op.create_index("ix_rol_tenant_id",  "rol", ["tenant_id"])
    op.create_index("ix_rol_deleted_at", "rol", ["deleted_at"])

    # --- permiso table ---
    op.execute("""
        CREATE TABLE permiso (
            id          UUID         NOT NULL DEFAULT gen_random_uuid(),
            tenant_id   UUID         NOT NULL REFERENCES tenants(id) ON DELETE RESTRICT,
            codigo      VARCHAR(100) NOT NULL,
            modulo      VARCHAR(50)  NOT NULL,
            accion      VARCHAR(50)  NOT NULL,
            descripcion VARCHAR(255),
            created_at  TIMESTAMPTZ  NOT NULL DEFAULT now(),
            updated_at  TIMESTAMPTZ  NOT NULL DEFAULT now(),
            deleted_at  TIMESTAMPTZ,
            PRIMARY KEY (id)
        )
    """)
    op.create_unique_constraint("uq_permiso_tenant_codigo", "permiso", ["tenant_id", "codigo"])
    op.create_index("ix_permiso_tenant_id",  "permiso", ["tenant_id"])
    op.create_index("ix_permiso_deleted_at", "permiso", ["deleted_at"])

    # --- rol_permiso table ---
    op.execute("""
        CREATE TABLE rol_permiso (
            id          UUID           NOT NULL DEFAULT gen_random_uuid(),
            tenant_id   UUID           NOT NULL REFERENCES tenants(id) ON DELETE RESTRICT,
            rol_id      UUID           NOT NULL REFERENCES rol(id) ON DELETE CASCADE,
            permiso_id  UUID           NOT NULL REFERENCES permiso(id) ON DELETE CASCADE,
            scope       permiso_scope  NOT NULL DEFAULT 'global',
            created_at  TIMESTAMPTZ    NOT NULL DEFAULT now(),
            updated_at  TIMESTAMPTZ    NOT NULL DEFAULT now(),
            deleted_at  TIMESTAMPTZ,
            PRIMARY KEY (id)
        )
    """)
    op.create_unique_constraint(
        "uq_rol_permiso", "rol_permiso", ["tenant_id", "rol_id", "permiso_id"]
    )
    op.create_index("ix_rol_permiso_tenant_id",  "rol_permiso", ["tenant_id"])
    op.create_index("ix_rol_permiso_rol_id",     "rol_permiso", ["rol_id"])
    op.create_index("ix_rol_permiso_permiso_id", "rol_permiso", ["permiso_id"])
    op.create_index("ix_rol_permiso_deleted_at", "rol_permiso", ["deleted_at"])

    # --- Seed: por cada tenant existente ---
    conn = op.get_bind()
    tenants = conn.execute(sa.text("SELECT id FROM tenants WHERE deleted_at IS NULL")).fetchall()
    for (tid,) in tenants:
        seed_rbac_for_tenant(conn, tid)


def downgrade() -> None:
    # Drop in reverse FK dependency order (idempotent — tables may be gone via CASCADE)
    op.execute("DROP INDEX IF EXISTS ix_rol_permiso_deleted_at")
    op.execute("DROP INDEX IF EXISTS ix_rol_permiso_permiso_id")
    op.execute("DROP INDEX IF EXISTS ix_rol_permiso_rol_id")
    op.execute("DROP INDEX IF EXISTS ix_rol_permiso_tenant_id")
    op.execute("DROP TABLE IF EXISTS rol_permiso CASCADE")

    op.execute("DROP INDEX IF EXISTS ix_permiso_deleted_at")
    op.execute("DROP INDEX IF EXISTS ix_permiso_tenant_id")
    op.execute("DROP TABLE IF EXISTS permiso CASCADE")

    op.execute("DROP INDEX IF EXISTS ix_rol_deleted_at")
    op.execute("DROP INDEX IF EXISTS ix_rol_tenant_id")
    op.execute("DROP TABLE IF EXISTS rol CASCADE")

    op.execute("DROP TYPE IF EXISTS permiso_scope CASCADE")

    op.execute("DROP TYPE IF EXISTS permiso_scope CASCADE")
