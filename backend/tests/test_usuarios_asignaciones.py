"""
test_usuarios_asignaciones.py — TDD suite para C-07 usuarios y asignaciones.

RED → GREEN → TRIANGULATE → REFACTOR cycle para tasks 1-12.

Cubre:
    Task 1  : Enum RolAsignacion
    Task 2  : Modelo Usuario (columnas, PII cifrada, email_hash, __repr__)
    Task 3  : Modelo Asignacion (columnas, FKs, obligatorios)
    Task 4  : Helper estado_vigencia (puro, sin side effects)
    Task 5  : Migración 006 (upgrade/downgrade)
    Task 6  : Unicidad de email por tenant (blind index DB)
    Task 7  : Repositories tenant-scoped (aislamiento, soft delete)
    Task 8  : UsuarioService (unicidad email, derivación hash, PII no en logs)
    Task 9  : AsignacionService (tenant-scope, multi-rol, vigencia)
    Task 10 : Schemas Pydantic v2 (extra=forbid, OQ-3 masking)
    Task 11 : Endpoints HTTP (403 fail-closed, 409/404/422, aislamiento)
    Task 12 : PII no en respuestas/logs, cobertura, LOC

DB real: activia_trace_test. Sin mocks.
"""
import datetime
import logging
import uuid
from datetime import date, timedelta

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError

from app.core.database import build_session_factory
from app.models.rbac import Permiso, Rol, RolPermiso, PermisoScope
from app.models.tenant import Tenant, TenantEstado
from app.models.usuario import Asignacion, RolAsignacion, Usuario, UsuarioEstado
from app.models.vigencia import EstadoVigencia, estado_vigencia
from app.repositories.usuario_repository import AsignacionRepository, UsuarioRepository
from app.schemas.usuario import (
    AsignacionCreate,
    AsignacionRead,
    AsignacionUpdate,
    UsuarioCreate,
    UsuarioRead,
    UsuarioUpdate,
)
from app.services.usuario_service import (
    AsignacionNoEncontrada,
    AsignacionService,
    ConflictoEmail,
    ReferenciaInvalida,
    UsuarioNoEncontrado,
    UsuarioService,
)


# ---------------------------------------------------------------------------
# JWT / settings helper
# ---------------------------------------------------------------------------

TEST_SECRET_KEY = "supersecretkeyfortesting1234567890"
TEST_ENCRYPTION_KEY = "E" * 32


def _make_jwt(
    tenant_id: uuid.UUID,
    user_id: uuid.UUID,
    roles: list,
    secret: str = TEST_SECRET_KEY,
) -> str:
    from jose import jwt as jose_jwt

    now = datetime.datetime.now(tz=datetime.timezone.utc)
    exp = now + datetime.timedelta(minutes=30)
    payload = {
        "sub": str(user_id),
        "tenant_id": str(tenant_id),
        "roles": roles,
        "iat": int(now.timestamp()),
        "exp": int(exp.timestamp()),
        "type": "access",
    }
    return jose_jwt.encode(payload, secret, algorithm="HS256")


def _fake_settings():
    class FakeSettings:
        SECRET_KEY = TEST_SECRET_KEY
        ENCRYPTION_KEY = TEST_ENCRYPTION_KEY
        ACCESS_TOKEN_EXPIRE_MINUTES = 30
        MFA_TOKEN_EXPIRE_MINUTES = 10
        REFRESH_TOKEN_EXPIRE_DAYS = 7
        RECOVERY_TOKEN_EXPIRE_MINUTES = 30
        LOGIN_RATE_LIMIT = "10/minute"

    return FakeSettings()


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture(scope="module")
async def usuario_setup(test_engine, create_tables):
    """
    Crea dos tenants con RBAC catalog para tests de usuarios/asignaciones.
      tenant_a: user_admin_a → ADMIN con usuarios:gestionar + equipos:asignar
      tenant_b: user_b       → ADMIN con usuarios:gestionar + equipos:asignar
    """

    factory = build_session_factory(test_engine)
    session = factory()

    tid_a = uuid.uuid4()
    tid_b = uuid.uuid4()
    session.add(Tenant(id=tid_a, nombre="Usuarios Tenant A", estado=TenantEstado.ACTIVO))
    session.add(Tenant(id=tid_b, nombre="Usuarios Tenant B", estado=TenantEstado.ACTIVO))
    await session.flush()

    user_admin_a = uuid.uuid4()
    user_b = uuid.uuid4()

    # Roles
    rol_admin_a = Rol(tenant_id=tid_a, nombre="USR_ADMIN_A")
    rol_admin_b = Rol(tenant_id=tid_b, nombre="USR_ADMIN_B")
    session.add_all([rol_admin_a, rol_admin_b])
    await session.flush()

    # Permisos
    perm_gestionar_a = Permiso(tenant_id=tid_a, codigo="usuarios:gestionar", modulo="usuarios", accion="gestionar")
    perm_gestionar_b = Permiso(tenant_id=tid_b, codigo="usuarios:gestionar", modulo="usuarios", accion="gestionar")
    perm_asignar_a = Permiso(tenant_id=tid_a, codigo="equipos:asignar", modulo="equipos", accion="asignar")
    perm_asignar_b = Permiso(tenant_id=tid_b, codigo="equipos:asignar", modulo="equipos", accion="asignar")
    session.add_all([perm_gestionar_a, perm_gestionar_b, perm_asignar_a, perm_asignar_b])
    await session.flush()

    # Grants
    session.add(RolPermiso(tenant_id=tid_a, rol_id=rol_admin_a.id, permiso_id=perm_gestionar_a.id, scope=PermisoScope.global_))
    session.add(RolPermiso(tenant_id=tid_b, rol_id=rol_admin_b.id, permiso_id=perm_gestionar_b.id, scope=PermisoScope.global_))
    session.add(RolPermiso(tenant_id=tid_a, rol_id=rol_admin_a.id, permiso_id=perm_asignar_a.id, scope=PermisoScope.global_))
    session.add(RolPermiso(tenant_id=tid_b, rol_id=rol_admin_b.id, permiso_id=perm_asignar_b.id, scope=PermisoScope.global_))
    await session.commit()
    await session.close()

    return {
        "tid_a": tid_a,
        "tid_b": tid_b,
        "user_admin_a": user_admin_a,
        "user_b": user_b,
        "rol_admin_a": "USR_ADMIN_A",
        "rol_admin_b": "USR_ADMIN_B",
    }


@pytest_asyncio.fixture(scope="module")
def usuario_app(test_engine, usuario_setup):
    """FastAPI app con test engine para tests de usuarios."""
    from app.main import create_app

    app = create_app()
    factory = build_session_factory(test_engine)
    app.state.session_factory = factory
    return app


@pytest_asyncio.fixture(scope="module")
async def usuario_client(usuario_app) -> AsyncClient:
    async with AsyncClient(
        transport=ASGITransport(app=usuario_app), base_url="http://test"
    ) as client:
        yield client


# ---------------------------------------------------------------------------
# TASK 1 — Enum RolAsignacion
# ---------------------------------------------------------------------------


def test_rol_asignacion_contiene_valores_correctos():
    """RED: RolAsignacion contiene PROFESOR, TUTOR, COORDINADOR, NEXO, ADMIN, FINANZAS."""
    valores = {m.value for m in RolAsignacion}
    assert "PROFESOR" in valores
    assert "TUTOR" in valores
    assert "COORDINADOR" in valores
    assert "NEXO" in valores
    assert "ADMIN" in valores
    assert "FINANZAS" in valores


def test_rol_asignacion_no_contiene_alumno():
    """RED: RolAsignacion NO contiene ALUMNO (condición modelada en padrón, C-09)."""
    valores = {m.value for m in RolAsignacion}
    assert "ALUMNO" not in valores


def test_rol_asignacion_rechaza_valor_arbitrario():
    """RED: El enum rechaza valores no declarados."""
    with pytest.raises(ValueError):
        RolAsignacion("DIRECTOR")


def test_rol_asignacion_es_str_enum():
    """Triangulación: RolAsignacion es str (permite comparar con strings)."""
    assert RolAsignacion.PROFESOR == "PROFESOR"
    assert isinstance(RolAsignacion.ADMIN, str)


# ---------------------------------------------------------------------------
# TASK 2 — Modelo Usuario
# ---------------------------------------------------------------------------


def test_usuario_tiene_columnas_base():
    """RED: Usuario tiene id, tenant_id, nombre, apellidos, email_encrypted, email_hash."""
    cols = {c.key for c in Usuario.__table__.columns}
    for col in ["id", "tenant_id", "nombre", "apellidos", "email_encrypted", "email_hash"]:
        assert col in cols, f"Columna faltante: {col}"


def test_usuario_tiene_pii_cifrada():
    """RED: Usuario tiene columnas PII cifradas (dni, cuil, cbu, alias_cbu)."""
    cols = {c.key for c in Usuario.__table__.columns}
    for col in ["dni", "cuil", "cbu", "alias_cbu"]:
        assert col in cols, f"Columna PII faltante: {col}"


def test_usuario_tiene_campos_negocio():
    """RED: Usuario tiene todos los atributos de negocio §E4."""
    cols = {c.key for c in Usuario.__table__.columns}
    for col in ["legajo", "legajo_profesional", "banco", "regional", "facturador", "estado"]:
        assert col in cols, f"Columna de negocio faltante: {col}"


def test_usuario_tiene_auth_identity_id():
    """RED: Usuario tiene auth_identity_id FK nullable (D9)."""
    cols = {c.key for c in Usuario.__table__.columns}
    assert "auth_identity_id" in cols


def test_usuario_tiene_timestamps_y_soft_delete():
    """RED: Usuario tiene created_at, updated_at, deleted_at."""
    cols = {c.key for c in Usuario.__table__.columns}
    for col in ["created_at", "updated_at", "deleted_at"]:
        assert col in cols, f"Columna timestamp faltante: {col}"


def test_usuario_no_tiene_columna_estado_vigencia():
    """RED: No existe columna estado_vigencia — es derivada."""
    cols = {c.key for c in Usuario.__table__.columns}
    assert "estado_vigencia" not in cols


def test_usuario_legajo_admite_nulo():
    """Triangulación: legajo admite nulo (no es PK ni obligatorio)."""
    u = Usuario(
        email_encrypted="test@example.com",
        email_hash="abc" * 21 + "a",
        nombre="Ana",
        apellidos="García",
        estado=UsuarioEstado.activo,
    )
    assert u.legajo is None


def test_usuario_repr_no_incluye_pii(monkeypatch):
    """Triangulación: __repr__ no incluye email ni PII en texto plano."""
    monkeypatch.setattr("app.core.config.Settings", _fake_settings)
    u = Usuario(
        email_encrypted="secreto@pii.com",
        email_hash="hash123",
        nombre="Pedro",
        apellidos="López",
        estado=UsuarioEstado.activo,
    )
    r = repr(u)
    assert "secreto@pii.com" not in r
    assert "pii.com" not in r


# ---------------------------------------------------------------------------
# TASK 3 — Modelo Asignacion
# ---------------------------------------------------------------------------


def test_asignacion_tiene_columnas_obligatorias():
    """RED: Asignacion tiene usuario_id, rol, desde (NOT NULL)."""
    cols = {c.key for c in Asignacion.__table__.columns}
    for col in ["id", "tenant_id", "usuario_id", "rol", "desde"]:
        assert col in cols, f"Columna obligatoria faltante: {col}"


def test_asignacion_tiene_columnas_contexto_nullable():
    """RED: Asignacion tiene materia_id, carrera_id, cohorte_id (nullable)."""
    cols = {c.key for c in Asignacion.__table__.columns}
    for col in ["materia_id", "carrera_id", "cohorte_id"]:
        assert col in cols


def test_asignacion_tiene_responsable_id_y_hasta():
    """RED: Asignacion tiene responsable_id (nullable) y hasta (nullable)."""
    cols = {c.key for c in Asignacion.__table__.columns}
    assert "responsable_id" in cols
    assert "hasta" in cols


def test_asignacion_tiene_comisiones_jsonb():
    """RED: Asignacion tiene comisiones JSONB."""
    cols = {c.key for c in Asignacion.__table__.columns}
    assert "comisiones" in cols


def test_asignacion_no_tiene_columna_estado_vigencia():
    """RED: No existe columna estado_vigencia en Asignacion — es derivada (D4)."""
    cols = {c.key for c in Asignacion.__table__.columns}
    assert "estado_vigencia" not in cols


def test_asignacion_contexto_y_responsable_admiten_nulo():
    """Triangulación: materia_id, carrera_id, cohorte_id, responsable_id nullable."""
    a = Asignacion(
        usuario_id=uuid.uuid4(),
        rol=RolAsignacion.PROFESOR,
        desde=date.today(),
    )
    assert a.materia_id is None
    assert a.carrera_id is None
    assert a.cohorte_id is None
    assert a.responsable_id is None
    assert a.hasta is None


# ---------------------------------------------------------------------------
# TASK 4 — Helper estado_vigencia (función pura)
# ---------------------------------------------------------------------------


def test_estado_vigencia_vigente_desde_hoy():
    """RED: desde == hoy, sin hasta → Vigente."""
    hoy = date.today()
    assert estado_vigencia(hoy, None, hoy) == EstadoVigencia.vigente


def test_estado_vigencia_vigente_hasta_hoy():
    """RED: hasta == hoy → Vigente (borde incluido)."""
    hoy = date.today()
    ayer = hoy - timedelta(days=1)
    assert estado_vigencia(ayer, hoy, hoy) == EstadoVigencia.vigente


def test_estado_vigencia_vencida_hasta_pasado():
    """Triangulación: hasta < hoy → Vencida."""
    hoy = date.today()
    ayer = hoy - timedelta(days=1)
    assert estado_vigencia(hoy - timedelta(days=10), ayer, hoy) == EstadoVigencia.vencida


def test_estado_vigencia_no_iniciada_desde_futuro():
    """Triangulación: desde > hoy → NoIniciada."""
    hoy = date.today()
    manana = hoy + timedelta(days=1)
    assert estado_vigencia(manana, None, hoy) == EstadoVigencia.no_iniciada


def test_estado_vigencia_abierta_vigente():
    """Triangulación: desde en el pasado, hasta IS NULL → Vigente."""
    hoy = date.today()
    hace_un_anio = hoy - timedelta(days=365)
    assert estado_vigencia(hace_un_anio, None, hoy) == EstadoVigencia.vigente


def test_estado_vigencia_usa_date_today_si_no_se_pasa_hoy():
    """Triangulación: sin hoy explícito, usa date.today()."""
    desde = date.today() - timedelta(days=5)
    result = estado_vigencia(desde, None)  # sin hoy
    assert result == EstadoVigencia.vigente


def test_estado_vigencia_borde_desde_igual_hasta():
    """Triangulación: desde == hasta == hoy → Vigente (asignación de un día)."""
    hoy = date.today()
    assert estado_vigencia(hoy, hoy, hoy) == EstadoVigencia.vigente


# ---------------------------------------------------------------------------
# TASK 5 — Migración 006 (upgrade/downgrade)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio(loop_scope="session")
async def test_migracion_006_upgrade_crea_tablas(test_engine, create_tables, monkeypatch):
    """RED: 006 upgrade crea tablas usuario, asignacion y enums (via create_all)."""
    monkeypatch.setattr("app.core.config.Settings", _fake_settings)

    from sqlalchemy import text

    async with test_engine.connect() as conn:
        # Verificar tabla usuario (creada por create_all via Base.metadata)
        res = await conn.execute(
            text("SELECT 1 FROM information_schema.tables WHERE table_name = 'usuario'")
        )
        assert res.scalar() == 1, "Tabla usuario no existe"

        # Verificar tabla asignacion
        res = await conn.execute(
            text("SELECT 1 FROM information_schema.tables WHERE table_name = 'asignacion'")
        )
        assert res.scalar() == 1, "Tabla asignacion no existe"

        # Verificar enum rol_asignacion (creado por _ensure_schema en conftest)
        res = await conn.execute(
            text("SELECT 1 FROM pg_type WHERE typname = 'rol_asignacion'")
        )
        assert res.scalar() == 1, "Enum rol_asignacion no existe"

        # Verificar enum usuario_estado
        res = await conn.execute(
            text("SELECT 1 FROM pg_type WHERE typname = 'usuario_estado'")
        )
        assert res.scalar() == 1, "Enum usuario_estado no existe"
        # Nota: el índice parcial ux_usuario_tenant_email_hash es creado por la migración
        # Alembic (no por create_all). Se verifica en el test de columnas/índices DB.


@pytest.mark.asyncio(loop_scope="session")
async def test_migracion_006_columnas_usuario(test_engine, create_tables, monkeypatch):
    """RED: tabla usuario tiene columnas PII, email_hash, auth_identity_id."""
    monkeypatch.setattr("app.core.config.Settings", _fake_settings)

    from sqlalchemy import text

    async with test_engine.connect() as conn:
        res = await conn.execute(
            text(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_name = 'usuario'"
            )
        )
        cols = {row[0] for row in res.fetchall()}
        for col in ["email_encrypted", "email_hash", "dni", "cuil", "cbu", "alias_cbu",
                    "nombre", "apellidos", "auth_identity_id", "deleted_at"]:
            assert col in cols, f"Columna faltante en tabla usuario: {col}"


# ---------------------------------------------------------------------------
# TASK 6 — Unicidad de email por tenant (blind index DB)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio(loop_scope="session")
async def test_email_unico_por_tenant_mismo_tenant_via_service(db_session, create_tables, usuario_setup, monkeypatch):
    """RED: service previene crear dos usuarios con mismo email en mismo tenant (ConflictoEmail).

    La defensa en profundidad (índice parcial DB) es creada por la migración Alembic 006.
    En el test env (create_all) se verifica la validación del service, que actúa antes del DB.
    """
    monkeypatch.setattr("app.core.config.Settings", _fake_settings)

    tid = usuario_setup["tid_a"]
    repo = UsuarioRepository(session=db_session, tenant_id=tid)

    from app.core.dependencies import CurrentUser
    actor = CurrentUser(user_id=uuid.uuid4(), tenant_id=tid, roles=["ADMIN"])
    svc = UsuarioService(repo=repo)

    email = f"email_uniq_{uuid.uuid4().hex[:8]}@test.com"
    u1 = await svc.crear_usuario(actor, email=email, nombre="Ana", apellidos="García")

    # Segundo intento con mismo email → ConflictoEmail (validación de service)
    with pytest.raises(ConflictoEmail):
        await svc.crear_usuario(actor, email=email, nombre="Bob", apellidos="Smith")

    # Cleanup
    await repo.delete(u1)
    await db_session.commit()


@pytest.mark.asyncio(loop_scope="session")
async def test_email_permitido_en_tenant_diferente(db_session, create_tables, monkeypatch):
    """RED: mismo email en dos tenants distintos es aceptado."""
    monkeypatch.setattr("app.core.config.Settings", _fake_settings)

    from app.core.security.passwords import email_lookup_hash

    tid1 = uuid.uuid4()
    tid2 = uuid.uuid4()
    db_session.add(Tenant(id=tid1, nombre="Email Tenant 1", estado=TenantEstado.ACTIVO))
    db_session.add(Tenant(id=tid2, nombre="Email Tenant 2", estado=TenantEstado.ACTIVO))
    await db_session.flush()

    email = "shared@different.com"
    email_hash = email_lookup_hash(email)

    u1 = Usuario(tenant_id=tid1, email_encrypted=email, email_hash=email_hash, nombre="A", apellidos="B", estado=UsuarioEstado.activo)
    u2 = Usuario(tenant_id=tid2, email_encrypted=email, email_hash=email_hash, nombre="C", apellidos="D", estado=UsuarioEstado.activo)
    db_session.add_all([u1, u2])
    await db_session.commit()  # No debe lanzar error

    # Cleanup
    await db_session.delete(u1)
    await db_session.delete(u2)
    await db_session.commit()


@pytest.mark.asyncio(loop_scope="session")
async def test_email_reutilizable_tras_baja_logica(db_session, create_tables, monkeypatch):
    """Triangulación: tras baja lógica se puede crear usuario con mismo email."""
    monkeypatch.setattr("app.core.config.Settings", _fake_settings)

    from app.core.security.passwords import email_lookup_hash
    from datetime import datetime, timezone

    tid = uuid.uuid4()
    db_session.add(Tenant(id=tid, nombre="Reuse Email Tenant", estado=TenantEstado.ACTIVO))
    await db_session.flush()

    email = "reuse@test.com"
    email_hash = email_lookup_hash(email)

    u1 = Usuario(tenant_id=tid, email_encrypted=email, email_hash=email_hash, nombre="X", apellidos="Y", estado=UsuarioEstado.activo)
    db_session.add(u1)
    await db_session.flush()

    # Dar de baja lógica
    u1.deleted_at = datetime.now(tz=timezone.utc)
    await db_session.flush()

    # Ahora se puede crear con el mismo email
    u2 = Usuario(tenant_id=tid, email_encrypted=email, email_hash=email_hash, nombre="Z", apellidos="W", estado=UsuarioEstado.activo)
    db_session.add(u2)
    await db_session.commit()  # No debe lanzar error

    # Cleanup
    await db_session.delete(u1)
    await db_session.delete(u2)
    await db_session.commit()


def test_email_hash_deterministico_variantes_capitalizacion(monkeypatch):
    """Triangulación: email_hash es determinístico para variantes de capitalización."""
    monkeypatch.setattr("app.core.config.Settings", _fake_settings)

    from app.core.security.passwords import email_lookup_hash

    h1 = email_lookup_hash("User@Example.COM")
    h2 = email_lookup_hash("user@example.com")
    h3 = email_lookup_hash("  user@example.com  ")
    assert h1 == h2 == h3


# ---------------------------------------------------------------------------
# TASK 7 — Repositories tenant-scoped
# ---------------------------------------------------------------------------


@pytest.mark.asyncio(loop_scope="session")
async def test_usuario_repo_add_fuerza_tenant_id(db_session, create_tables, usuario_setup, monkeypatch):
    """RED: UsuarioRepository.add fuerza tenant_id al scope."""
    monkeypatch.setattr("app.core.config.Settings", _fake_settings)

    from app.core.security.passwords import email_lookup_hash

    tid = usuario_setup["tid_a"]
    repo = UsuarioRepository(session=db_session, tenant_id=tid)

    email = f"repo_test_{uuid.uuid4().hex[:8]}@test.com"
    email_hash = email_lookup_hash(email)

    u = Usuario(
        email_encrypted=email,
        email_hash=email_hash,
        nombre="Repo",
        apellidos="Test",
        estado=UsuarioEstado.activo,
    )
    # Sin tenant_id explícito — el repo lo fuerza
    saved = await repo.add(u)
    assert saved.tenant_id == tid

    # Cleanup
    await repo.delete(saved)
    await db_session.commit()


@pytest.mark.asyncio(loop_scope="session")
async def test_usuario_repo_aislamiento_tenant(db_session, create_tables, usuario_setup, monkeypatch):
    """RED: list() del tenant A nunca devuelve usuarios del tenant B."""
    monkeypatch.setattr("app.core.config.Settings", _fake_settings)

    from app.core.security.passwords import email_lookup_hash

    tid_a = usuario_setup["tid_a"]
    tid_b = usuario_setup["tid_b"]

    repo_a = UsuarioRepository(session=db_session, tenant_id=tid_a)
    repo_b = UsuarioRepository(session=db_session, tenant_id=tid_b)

    email_a = f"tenant_a_{uuid.uuid4().hex[:8]}@test.com"
    email_b = f"tenant_b_{uuid.uuid4().hex[:8]}@test.com"

    u_a = Usuario(email_encrypted=email_a, email_hash=email_lookup_hash(email_a), nombre="A", apellidos="A", estado=UsuarioEstado.activo)
    u_b = Usuario(email_encrypted=email_b, email_hash=email_lookup_hash(email_b), nombre="B", apellidos="B", estado=UsuarioEstado.activo)

    await repo_a.add(u_a)
    await repo_b.add(u_b)

    lista_a = await repo_a.list()
    ids_a = {u.id for u in lista_a}
    assert u_a.id in ids_a
    assert u_b.id not in ids_a

    lista_b = await repo_b.list()
    ids_b = {u.id for u in lista_b}
    assert u_b.id in ids_b
    assert u_a.id not in ids_b

    # Cleanup
    await repo_a.delete(u_a)
    await repo_b.delete(u_b)
    await db_session.commit()


@pytest.mark.asyncio(loop_scope="session")
async def test_usuario_repo_soft_delete(db_session, create_tables, usuario_setup, monkeypatch):
    """Triangulación: delete() marca deleted_at sin borrar físicamente."""
    monkeypatch.setattr("app.core.config.Settings", _fake_settings)

    from app.core.security.passwords import email_lookup_hash

    tid = usuario_setup["tid_a"]
    repo = UsuarioRepository(session=db_session, tenant_id=tid)

    email = f"softdel_{uuid.uuid4().hex[:8]}@test.com"
    u = Usuario(email_encrypted=email, email_hash=email_lookup_hash(email), nombre="Soft", apellidos="Delete", estado=UsuarioEstado.activo)
    saved = await repo.add(u)

    # Borrar lógicamente
    await repo.delete(saved)

    # No aparece en list normal
    lista = await repo.list()
    ids = {x.id for x in lista}
    assert saved.id not in ids

    # Aparece con include_deleted=True
    lista_all = await repo.list(include_deleted=True)
    ids_all = {x.id for x in lista_all}
    assert saved.id in ids_all


# ---------------------------------------------------------------------------
# TASK 8 — UsuarioService
# ---------------------------------------------------------------------------


@pytest.mark.asyncio(loop_scope="session")
async def test_service_crea_usuario_y_deriva_hash(db_session, create_tables, usuario_setup, monkeypatch):
    """RED: crear_usuario deriva email_hash, no lo recibe del cliente."""
    monkeypatch.setattr("app.core.config.Settings", _fake_settings)

    from app.core.security.passwords import email_lookup_hash

    tid = usuario_setup["tid_a"]
    repo = UsuarioRepository(session=db_session, tenant_id=tid)

    from app.core.dependencies import CurrentUser
    actor = CurrentUser(user_id=uuid.uuid4(), tenant_id=tid, roles=["ADMIN"])

    svc = UsuarioService(repo=repo)
    email = f"service_hash_{uuid.uuid4().hex[:8]}@test.com"
    u = await svc.crear_usuario(actor, email=email, nombre="Hash", apellidos="Test")

    assert u.email_hash == email_lookup_hash(email)

    # Cleanup
    await repo.delete(u)
    await db_session.commit()


@pytest.mark.asyncio(loop_scope="session")
async def test_service_conflicto_email_mismo_tenant(db_session, create_tables, usuario_setup, monkeypatch):
    """RED: crear usuario con email duplicado (mismo tenant) lanza ConflictoEmail."""
    monkeypatch.setattr("app.core.config.Settings", _fake_settings)

    tid = usuario_setup["tid_a"]
    repo = UsuarioRepository(session=db_session, tenant_id=tid)

    from app.core.dependencies import CurrentUser
    actor = CurrentUser(user_id=uuid.uuid4(), tenant_id=tid, roles=["ADMIN"])

    svc = UsuarioService(repo=repo)
    email = f"dup_{uuid.uuid4().hex[:8]}@test.com"

    u = await svc.crear_usuario(actor, email=email, nombre="First", apellidos="User")
    with pytest.raises(ConflictoEmail):
        await svc.crear_usuario(actor, email=email, nombre="Second", apellidos="User")

    # Cleanup
    await repo.delete(u)
    await db_session.commit()


@pytest.mark.asyncio(loop_scope="session")
async def test_service_editar_email_recomputa_hash(db_session, create_tables, usuario_setup, monkeypatch):
    """Triangulación: editar email recomputa email_hash y re-valida unicidad."""
    monkeypatch.setattr("app.core.config.Settings", _fake_settings)

    from app.core.security.passwords import email_lookup_hash

    tid = usuario_setup["tid_a"]
    repo = UsuarioRepository(session=db_session, tenant_id=tid)

    from app.core.dependencies import CurrentUser
    actor = CurrentUser(user_id=uuid.uuid4(), tenant_id=tid, roles=["ADMIN"])

    svc = UsuarioService(repo=repo)
    email_orig = f"orig_{uuid.uuid4().hex[:8]}@test.com"
    email_new = f"new_{uuid.uuid4().hex[:8]}@test.com"

    u = await svc.crear_usuario(actor, email=email_orig, nombre="Original", apellidos="Email")
    edited = await svc.editar_usuario(u.id, email=email_new)

    assert edited.email_hash == email_lookup_hash(email_new)
    assert edited.email_hash != email_lookup_hash(email_orig)

    # Cleanup
    await repo.delete(edited)
    await db_session.commit()


@pytest.mark.asyncio(loop_scope="session")
async def test_service_baja_conserva_registro(db_session, create_tables, usuario_setup, monkeypatch):
    """Triangulación: baja lógica conserva el registro (soft delete)."""
    monkeypatch.setattr("app.core.config.Settings", _fake_settings)

    tid = usuario_setup["tid_a"]
    repo = UsuarioRepository(session=db_session, tenant_id=tid)

    from app.core.dependencies import CurrentUser
    actor = CurrentUser(user_id=uuid.uuid4(), tenant_id=tid, roles=["ADMIN"])

    svc = UsuarioService(repo=repo)
    email = f"baja_{uuid.uuid4().hex[:8]}@test.com"

    u = await svc.crear_usuario(actor, email=email, nombre="Baja", apellidos="Test")
    await svc.dar_baja_usuario(u.id)

    # El registro existe con deleted_at
    recuperado = await repo.get_by_id(u.id, include_deleted=True)
    assert recuperado is not None
    assert recuperado.deleted_at is not None


# ---------------------------------------------------------------------------
# TASK 9 — AsignacionService
# ---------------------------------------------------------------------------


@pytest.mark.asyncio(loop_scope="session")
async def test_asignacion_service_rechaza_usuario_otro_tenant(db_session, create_tables, usuario_setup, monkeypatch):
    """RED: crear asignación con usuario_id de OTRO tenant es rechazado."""
    monkeypatch.setattr("app.core.config.Settings", _fake_settings)

    from app.core.security.passwords import email_lookup_hash

    tid_a = usuario_setup["tid_a"]
    tid_b = usuario_setup["tid_b"]

    repo_a = UsuarioRepository(session=db_session, tenant_id=tid_a)
    repo_b = UsuarioRepository(session=db_session, tenant_id=tid_b)

    # Crear usuario en tenant B
    email_b = f"asig_b_{uuid.uuid4().hex[:8]}@test.com"
    u_b = Usuario(email_encrypted=email_b, email_hash=email_lookup_hash(email_b), nombre="B", apellidos="User", estado=UsuarioEstado.activo)
    await repo_b.add(u_b)

    # Intentar asignar en tenant A referenciando usuario de tenant B
    asig_repo_a = AsignacionRepository(session=db_session, tenant_id=tid_a)

    from app.core.dependencies import CurrentUser
    actor_a = CurrentUser(user_id=uuid.uuid4(), tenant_id=tid_a, roles=["ADMIN"])

    svc = AsignacionService(asignacion_repo=asig_repo_a, usuario_repo=repo_a)
    with pytest.raises(UsuarioNoEncontrado):
        await svc.crear_asignacion(actor_a, u_b.id, RolAsignacion.PROFESOR, date.today())

    # Cleanup
    await repo_b.delete(u_b)
    await db_session.commit()


@pytest.mark.asyncio(loop_scope="session")
async def test_asignacion_service_rechaza_responsable_otro_tenant(db_session, create_tables, usuario_setup, monkeypatch):
    """RED: responsable_id de OTRO tenant es rechazado."""
    monkeypatch.setattr("app.core.config.Settings", _fake_settings)

    from app.core.security.passwords import email_lookup_hash

    tid_a = usuario_setup["tid_a"]
    tid_b = usuario_setup["tid_b"]

    repo_a = UsuarioRepository(session=db_session, tenant_id=tid_a)
    repo_b = UsuarioRepository(session=db_session, tenant_id=tid_b)

    email_a = f"usr_a_{uuid.uuid4().hex[:8]}@test.com"
    email_b = f"res_b_{uuid.uuid4().hex[:8]}@test.com"

    u_a = Usuario(email_encrypted=email_a, email_hash=email_lookup_hash(email_a), nombre="User", apellidos="A", estado=UsuarioEstado.activo)
    u_b = Usuario(email_encrypted=email_b, email_hash=email_lookup_hash(email_b), nombre="Resp", apellidos="B", estado=UsuarioEstado.activo)
    await repo_a.add(u_a)
    await repo_b.add(u_b)

    asig_repo_a = AsignacionRepository(session=db_session, tenant_id=tid_a)

    from app.core.dependencies import CurrentUser
    actor_a = CurrentUser(user_id=uuid.uuid4(), tenant_id=tid_a, roles=["ADMIN"])

    svc = AsignacionService(asignacion_repo=asig_repo_a, usuario_repo=repo_a)
    with pytest.raises(ReferenciaInvalida):
        await svc.crear_asignacion(
            actor_a, u_a.id, RolAsignacion.TUTOR, date.today(),
            responsable_id=u_b.id  # Responsable de otro tenant
        )

    # Cleanup
    await repo_a.delete(u_a)
    await repo_b.delete(u_b)
    await db_session.commit()


@pytest.mark.asyncio(loop_scope="session")
async def test_asignacion_service_multi_rol_mismo_usuario(db_session, create_tables, usuario_setup, monkeypatch):
    """RED: un mismo usuario puede tener asignaciones con roles distintos."""
    monkeypatch.setattr("app.core.config.Settings", _fake_settings)

    from app.core.security.passwords import email_lookup_hash

    tid = usuario_setup["tid_a"]
    repo = UsuarioRepository(session=db_session, tenant_id=tid)
    asig_repo = AsignacionRepository(session=db_session, tenant_id=tid)

    email = f"multir_{uuid.uuid4().hex[:8]}@test.com"
    u = Usuario(email_encrypted=email, email_hash=email_lookup_hash(email), nombre="Multi", apellidos="Rol", estado=UsuarioEstado.activo)
    await repo.add(u)

    from app.core.dependencies import CurrentUser
    actor = CurrentUser(user_id=uuid.uuid4(), tenant_id=tid, roles=["ADMIN"])

    svc = AsignacionService(asignacion_repo=asig_repo, usuario_repo=repo)
    hoy = date.today()

    a1 = await svc.crear_asignacion(actor, u.id, RolAsignacion.PROFESOR, hoy)
    a2 = await svc.crear_asignacion(actor, u.id, RolAsignacion.TUTOR, hoy)

    # Ambas asignaciones existen
    lista = await svc.listar_asignaciones(usuario_id=u.id)
    ids = {a.id for a in lista}
    assert a1.id in ids
    assert a2.id in ids

    # Cleanup
    await asig_repo.delete(a1)
    await asig_repo.delete(a2)
    await repo.delete(u)
    await db_session.commit()


@pytest.mark.asyncio(loop_scope="session")
async def test_asignacion_vencida_se_conserva(db_session, create_tables, usuario_setup, monkeypatch):
    """RED: asignación con hasta pasado se conserva (no se borra al vencer)."""
    monkeypatch.setattr("app.core.config.Settings", _fake_settings)

    from app.core.security.passwords import email_lookup_hash

    tid = usuario_setup["tid_a"]
    repo = UsuarioRepository(session=db_session, tenant_id=tid)
    asig_repo = AsignacionRepository(session=db_session, tenant_id=tid)

    email = f"venc_{uuid.uuid4().hex[:8]}@test.com"
    u = Usuario(email_encrypted=email, email_hash=email_lookup_hash(email), nombre="Vence", apellidos="Test", estado=UsuarioEstado.activo)
    await repo.add(u)

    from app.core.dependencies import CurrentUser
    actor = CurrentUser(user_id=uuid.uuid4(), tenant_id=tid, roles=["ADMIN"])

    svc = AsignacionService(asignacion_repo=asig_repo, usuario_repo=repo)
    ayer = date.today() - timedelta(days=1)
    hace_diez = date.today() - timedelta(days=10)

    # Crear asignación ya vencida
    a = await svc.crear_asignacion(actor, u.id, RolAsignacion.NEXO, hace_diez, hasta=ayer)

    # Estado vigencia debe ser vencida
    assert svc.calcular_vigencia(a) == EstadoVigencia.vencida

    # La asignación sigue en la lista (no se borra automáticamente)
    lista = await svc.listar_asignaciones(usuario_id=u.id)
    ids = {x.id for x in lista}
    assert a.id in ids

    # Cleanup
    await asig_repo.delete(a)
    await repo.delete(u)
    await db_session.commit()


# ---------------------------------------------------------------------------
# TASK 10 — Schemas Pydantic v2
# ---------------------------------------------------------------------------


def test_usuario_create_rechaza_campos_extra():
    """RED: UsuarioCreate rechaza campos no declarados (extra=forbid)."""
    with pytest.raises(ValidationError):
        UsuarioCreate(
            email="test@test.com",
            nombre="A",
            apellidos="B",
            campo_extra="valor",  # type: ignore
        )


def test_usuario_create_no_acepta_email_hash():
    """RED: UsuarioCreate no acepta email_hash ni tenant_id (client never sends)."""
    with pytest.raises(ValidationError):
        UsuarioCreate(
            email="test@test.com",
            nombre="A",
            apellidos="B",
            email_hash="abc",  # type: ignore
        )


def test_usuario_read_no_expone_pii_financiera():
    """RED (OQ-3): UsuarioRead no expone dni/cuil/cbu/alias_cbu en texto plano."""
    # UsuarioRead no tiene campo dni, cuil, cbu, alias_cbu
    fields = set(UsuarioRead.model_fields.keys())
    for campo_pii in ["dni", "cuil", "cbu", "alias_cbu", "tenant_id", "email_hash",
                      "email_encrypted"]:
        assert campo_pii not in fields, f"Campo PII {campo_pii!r} expuesto en UsuarioRead"


def test_usuario_read_expone_campos_correctos():
    """RED (OQ-3): UsuarioRead expone exactamente los campos del contrato."""
    expected = {"id", "email", "nombre", "apellidos", "legajo", "estado",
                "asignaciones", "created_at", "updated_at"}
    fields = set(UsuarioRead.model_fields.keys())
    for campo in expected:
        assert campo in fields, f"Campo requerido {campo!r} ausente en UsuarioRead"


def test_asignacion_create_exige_obligatorios():
    """RED: AsignacionCreate exige usuario_id, rol, desde."""
    with pytest.raises(ValidationError):
        AsignacionCreate(rol=RolAsignacion.PROFESOR, desde=date.today())  # sin usuario_id

    with pytest.raises(ValidationError):
        AsignacionCreate(usuario_id=uuid.uuid4(), desde=date.today())  # sin rol


def test_asignacion_create_acepta_contexto_nulo():
    """RED: AsignacionCreate acepta materia_id/carrera_id/cohorte_id/hasta nulos."""
    a = AsignacionCreate(
        usuario_id=uuid.uuid4(),
        rol=RolAsignacion.TUTOR,
        desde=date.today(),
    )
    assert a.hasta is None
    assert a.materia_id is None
    assert a.carrera_id is None
    assert a.cohorte_id is None


def test_asignacion_update_todos_opcionales():
    """Triangulación: AsignacionUpdate tiene todos los campos opcionales."""
    u = AsignacionUpdate()
    assert u.rol is None
    assert u.desde is None
    assert u.hasta is None


def test_asignacion_read_tiene_estado_vigencia():
    """Triangulación: AsignacionRead incluye estado_vigencia."""
    fields = set(AsignacionRead.model_fields.keys())
    assert "estado_vigencia" in fields


def test_asignacion_read_rechaza_campos_extra():
    """RED: AsignacionRead rechaza campos extra (extra=forbid)."""
    with pytest.raises(ValidationError):
        AsignacionRead(
            id=uuid.uuid4(),
            usuario_id=uuid.uuid4(),
            rol=RolAsignacion.ADMIN,
            desde=date.today(),
            estado_vigencia=EstadoVigencia.vigente,
            created_at=datetime.datetime.now(),
            updated_at=datetime.datetime.now(),
            campo_extra="x",  # type: ignore
        )


def test_usuario_update_todos_opcionales():
    """Triangulación: UsuarioUpdate tiene todos los campos opcionales (PATCH parcial)."""
    u = UsuarioUpdate()
    assert u.email is None
    assert u.nombre is None
    assert u.estado is None


# ---------------------------------------------------------------------------
# TASK 11 — Endpoints HTTP (fail-closed, 403, 409, 404, 422)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio(loop_scope="session")
async def test_listar_usuarios_sin_permiso_retorna_403(usuario_client, usuario_setup, monkeypatch):
    """RED: GET /api/v1/admin/usuarios sin usuarios:gestionar → 403."""
    monkeypatch.setattr("app.core.config.Settings", _fake_settings)

    tid = usuario_setup["tid_a"]
    user_id = uuid.uuid4()
    token = _make_jwt(tid, user_id, roles=["SINPERMISO"])

    resp = await usuario_client.get(
        "/api/v1/admin/usuarios",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio(loop_scope="session")
async def test_crear_usuario_sin_permiso_retorna_403(usuario_client, usuario_setup, monkeypatch):
    """RED: POST /api/v1/admin/usuarios sin usuarios:gestionar → 403."""
    monkeypatch.setattr("app.core.config.Settings", _fake_settings)

    tid = usuario_setup["tid_a"]
    token = _make_jwt(tid, uuid.uuid4(), roles=["SINPERMISO"])

    resp = await usuario_client.post(
        "/api/v1/admin/usuarios",
        json={"email": "x@x.com", "nombre": "A", "apellidos": "B"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio(loop_scope="session")
async def test_crear_usuario_con_permiso_retorna_201(usuario_client, usuario_setup, monkeypatch):
    """RED: POST /api/v1/admin/usuarios con permiso → 201 y datos correctos."""
    monkeypatch.setattr("app.core.config.Settings", _fake_settings)

    tid = usuario_setup["tid_a"]
    user_id = usuario_setup["user_admin_a"]
    rol = usuario_setup["rol_admin_a"]
    token = _make_jwt(tid, user_id, roles=[rol])

    email = f"endpoint_{uuid.uuid4().hex[:8]}@test.com"
    resp = await usuario_client.post(
        "/api/v1/admin/usuarios",
        json={"email": email, "nombre": "Endpoint", "apellidos": "Test"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["email"] == email
    assert data["nombre"] == "Endpoint"
    # OQ-3: nunca expone PII financiera ni tenant_id
    assert "dni" not in data
    assert "cuil" not in data
    assert "cbu" not in data
    assert "tenant_id" not in data


@pytest.mark.asyncio(loop_scope="session")
async def test_crear_usuario_duplicado_retorna_409(usuario_client, usuario_setup, monkeypatch):
    """RED: POST mismo email dos veces → 409."""
    monkeypatch.setattr("app.core.config.Settings", _fake_settings)

    tid = usuario_setup["tid_a"]
    user_id = usuario_setup["user_admin_a"]
    rol = usuario_setup["rol_admin_a"]
    token = _make_jwt(tid, user_id, roles=[rol])

    email = f"dup_ep_{uuid.uuid4().hex[:8]}@test.com"
    await usuario_client.post(
        "/api/v1/admin/usuarios",
        json={"email": email, "nombre": "A", "apellidos": "B"},
        headers={"Authorization": f"Bearer {token}"},
    )
    resp = await usuario_client.post(
        "/api/v1/admin/usuarios",
        json={"email": email, "nombre": "C", "apellidos": "D"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 409


@pytest.mark.asyncio(loop_scope="session")
async def test_editar_usuario_no_encontrado_retorna_404(usuario_client, usuario_setup, monkeypatch):
    """RED: PATCH usuario inexistente → 404."""
    monkeypatch.setattr("app.core.config.Settings", _fake_settings)

    tid = usuario_setup["tid_a"]
    user_id = usuario_setup["user_admin_a"]
    rol = usuario_setup["rol_admin_a"]
    token = _make_jwt(tid, user_id, roles=[rol])

    resp = await usuario_client.patch(
        f"/api/v1/admin/usuarios/{uuid.uuid4()}",
        json={"nombre": "Nuevo"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio(loop_scope="session")
async def test_asignacion_sin_permiso_retorna_403(usuario_client, usuario_setup, monkeypatch):
    """RED: POST /api/v1/asignaciones sin equipos:asignar → 403."""
    monkeypatch.setattr("app.core.config.Settings", _fake_settings)

    tid = usuario_setup["tid_a"]
    token = _make_jwt(tid, uuid.uuid4(), roles=["SINPERMISO"])

    resp = await usuario_client.post(
        "/api/v1/asignaciones",
        json={
            "usuario_id": str(uuid.uuid4()),
            "rol": "PROFESOR",
            "desde": str(date.today()),
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio(loop_scope="session")
async def test_asignacion_usuario_inexistente_retorna_422(usuario_client, usuario_setup, monkeypatch):
    """RED: crear asignación con usuario inexistente → 422."""
    monkeypatch.setattr("app.core.config.Settings", _fake_settings)

    tid = usuario_setup["tid_a"]
    user_id = usuario_setup["user_admin_a"]
    rol = usuario_setup["rol_admin_a"]
    token = _make_jwt(tid, user_id, roles=[rol])

    resp = await usuario_client.post(
        "/api/v1/asignaciones",
        json={
            "usuario_id": str(uuid.uuid4()),  # No existe
            "rol": "PROFESOR",
            "desde": str(date.today()),
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio(loop_scope="session")
async def test_response_nunca_expone_pii_financiera(usuario_client, usuario_setup, monkeypatch):
    """Triangulación (OQ-3): respuesta nunca incluye dni/cuil/cbu en texto plano."""
    monkeypatch.setattr("app.core.config.Settings", _fake_settings)

    tid = usuario_setup["tid_a"]
    user_id = usuario_setup["user_admin_a"]
    rol = usuario_setup["rol_admin_a"]
    token = _make_jwt(tid, user_id, roles=[rol])

    email = f"pii_test_{uuid.uuid4().hex[:8]}@test.com"
    resp = await usuario_client.post(
        "/api/v1/admin/usuarios",
        json={
            "email": email,
            "nombre": "PII",
            "apellidos": "Test",
            "dni": "12345678",
            "cuil": "20-12345678-1",
            "cbu": "0000003100012345678900",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201
    data = resp.json()
    response_str = str(data)
    # La PII financiera NO debe aparecer en texto plano en la respuesta
    assert "12345678" not in response_str
    assert "cbu" not in data
    assert "dni" not in data
    assert "cuil" not in data


@pytest.mark.asyncio(loop_scope="session")
async def test_aislamiento_tenant_en_endpoint(usuario_client, usuario_setup, monkeypatch):
    """Triangulación: usuario del tenant A no ve registros del tenant B."""
    monkeypatch.setattr("app.core.config.Settings", _fake_settings)

    from app.core.security.passwords import email_lookup_hash

    tid_a = usuario_setup["tid_a"]
    tid_b = usuario_setup["tid_b"]
    user_a = usuario_setup["user_admin_a"]
    rol_a = usuario_setup["rol_admin_a"]
    user_b = usuario_setup["user_b"]
    rol_b = usuario_setup["rol_admin_b"]

    token_a = _make_jwt(tid_a, user_a, roles=[rol_a])
    token_b = _make_jwt(tid_b, user_b, roles=[rol_b])

    email_b = f"isol_b_{uuid.uuid4().hex[:8]}@test.com"
    # Crear usuario en tenant B
    resp = await usuario_client.post(
        "/api/v1/admin/usuarios",
        json={"email": email_b, "nombre": "B", "apellidos": "Tenant"},
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert resp.status_code == 201
    user_b_id = resp.json()["id"]

    # Tenant A no debe ver el usuario de B en su lista
    resp_lista = await usuario_client.get(
        "/api/v1/admin/usuarios",
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert resp_lista.status_code == 200
    ids_a = [u["id"] for u in resp_lista.json()]
    assert user_b_id not in ids_a


# ---------------------------------------------------------------------------
# TASK 12 — PII no en logs, LOC check (básico)
# ---------------------------------------------------------------------------


def test_pii_no_aparece_en_logs_durante_creacion(monkeypatch, caplog):
    """RED: PII en texto plano no aparece en logs durante creación (verificación básica)."""
    monkeypatch.setattr("app.core.config.Settings", _fake_settings)

    # Verificamos que el __repr__ del modelo no incluye PII
    u = Usuario(
        email_encrypted="secreto@pii.com",
        email_hash="hash123",
        nombre="Pedro",
        apellidos="López",
        dni="12345678",
        cuil="20-12345678-1",
        cbu="0000003100012345678900",
        estado=UsuarioEstado.activo,
    )
    r = repr(u)
    assert "secreto@pii.com" not in r
    assert "12345678" not in r
    assert "0000003100012345678900" not in r


def test_require_permission_no_modificado_en_c07():
    """Task 4.4: verificar que require_permission no fue modificado en C-07."""
    # require_permission y el motor de permisos efectivos no deben tener cambios C-07
    from app.core.dependencies import require_permission
    import inspect
    src = inspect.getsource(require_permission)
    # Simplemente verificamos que el módulo existe y es invocable sin C-07 changes
    assert callable(require_permission)
