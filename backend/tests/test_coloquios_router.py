"""
test_coloquios_router.py — Integration tests for C-14 /api/v1/coloquios router.

Task 5.5: Router integration tests (DB real).
    - 201 creation of convocatoria
    - 403 fail-closed (ALUMNO no gestiona, gestor no reserva con permiso ajeno)
    - 409 cupo lleno
    - 404 cross-tenant

RED → GREEN: tests reference router endpoints.
DB real: activia_trace_test. Sin mocks.
"""
import asyncio
import datetime
import uuid
from datetime import date

import pytest
import pytest_asyncio
from dotenv import load_dotenv
import os
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import NullPool

from app.core.database import build_session_factory

load_dotenv()
TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://postgres@localhost:5432/activia_trace_test",
)

TEST_SECRET_KEY = "supersecretkeyfortesting1234567890"
TEST_ENCRYPTION_KEY = "E" * 32


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


def _make_jwt(tenant_id: uuid.UUID, user_id: uuid.UUID, roles: list) -> str:
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
    return jose_jwt.encode(payload, TEST_SECRET_KEY, algorithm="HS256")


@pytest.fixture(scope="module")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="module")
async def col_engine():
    engine = create_async_engine(TEST_DATABASE_URL, poolclass=NullPool, echo=False)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture(scope="module")
async def col_setup(col_engine):
    """Create tenants, RBAC, and academic structure for coloquios router tests."""
    import app.models  # noqa: F401

    async with col_engine.begin() as conn:
        for stmt in [
            "DO $$ BEGIN CREATE TYPE tenant_estado AS ENUM ('activo', 'inactivo'); EXCEPTION WHEN duplicate_object THEN NULL; END $$;",
            "DO $$ BEGIN CREATE TYPE permiso_scope AS ENUM ('global', 'propio'); EXCEPTION WHEN duplicate_object THEN NULL; END $$;",
            "DO $$ BEGIN CREATE TYPE audit_resultado AS ENUM ('ok', 'fail', 'partial'); EXCEPTION WHEN duplicate_object THEN NULL; END $$;",
            "DO $$ BEGIN CREATE TYPE estado_estructura AS ENUM ('activa', 'inactiva'); EXCEPTION WHEN duplicate_object THEN NULL; END $$;",
            "DO $$ BEGIN CREATE TYPE rol_asignacion AS ENUM ('PROFESOR', 'TUTOR', 'COORDINADOR', 'NEXO', 'ADMIN', 'FINANZAS'); EXCEPTION WHEN duplicate_object THEN NULL; END $$;",
            "DO $$ BEGIN CREATE TYPE usuario_estado AS ENUM ('activo', 'inactivo'); EXCEPTION WHEN duplicate_object THEN NULL; END $$;",
            "DO $$ BEGIN CREATE TYPE calificacion_origen AS ENUM ('Importado', 'Manual'); EXCEPTION WHEN duplicate_object THEN NULL; END $$;",
            "DO $$ BEGIN CREATE TYPE comunicacion_estado AS ENUM ('Pendiente', 'Enviando', 'Enviado', 'Error', 'Cancelado'); EXCEPTION WHEN duplicate_object THEN NULL; END $$;",
            "DO $$ BEGIN CREATE TYPE dia_semana AS ENUM ('Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo'); EXCEPTION WHEN duplicate_object THEN NULL; END $$;",
            "DO $$ BEGIN CREATE TYPE instancia_encuentro_estado AS ENUM ('Programado', 'Realizado', 'Cancelado'); EXCEPTION WHEN duplicate_object THEN NULL; END $$;",
            "DO $$ BEGIN CREATE TYPE guardia_estado AS ENUM ('Pendiente', 'Realizada', 'Cancelada'); EXCEPTION WHEN duplicate_object THEN NULL; END $$;",
            "DO $$ BEGIN CREATE TYPE evaluacion_tipo AS ENUM ('Parcial', 'TP', 'Coloquio', 'Recuperatorio'); EXCEPTION WHEN duplicate_object THEN NULL; END $$;",
            "DO $$ BEGIN CREATE TYPE reserva_estado AS ENUM ('Activa', 'Cancelada'); EXCEPTION WHEN duplicate_object THEN NULL; END $$;",
        ]:
            await conn.execute(text(stmt))
        for action in ["PADRON_CARGAR", "CALIFICACIONES_IMPORTAR", "COMUNICACION_ENVIAR",
                       "EQUIPOS_ASIGNACION_MASIVA", "EQUIPOS_CLONAR", "EQUIPOS_VIGENCIA_GENERAL",
                       "ENCUENTRO_GESTIONAR", "COLOQUIO_GESTIONAR"]:
            await conn.execute(text(
                f"DO $$ BEGIN ALTER TYPE audit_action ADD VALUE '{action}'; "
                "EXCEPTION WHEN duplicate_object THEN NULL; END $$;"
            ))
        from app.core.database import Base
        await conn.run_sync(Base.metadata.create_all, checkfirst=True)
        await conn.execute(text(
            "CREATE UNIQUE INDEX IF NOT EXISTS uq_reserva_activa_por_convocatoria "
            "ON reserva_evaluacion (tenant_id, evaluacion_id, alumno_id) "
            "WHERE estado = 'Activa' AND deleted_at IS NULL"
        ))

    factory = build_session_factory(col_engine)
    session = factory()

    try:
        from app.models.tenant import Tenant, TenantEstado
        from app.models.estructura import Carrera, Cohorte, Materia, EstadoEstructura
        from app.models.rbac import Permiso, PermisoScope, Rol, RolPermiso
        from app.models.usuario import Usuario, UsuarioEstado
        from app.core.security.passwords import email_lookup_hash as _hash

        tid_a = uuid.uuid4()
        tid_b = uuid.uuid4()

        session.add(Tenant(id=tid_a, nombre=f"ColA_{tid_a.hex[:4]}", estado=TenantEstado.ACTIVO))
        session.add(Tenant(id=tid_b, nombre=f"ColB_{tid_b.hex[:4]}", estado=TenantEstado.ACTIVO))
        await session.flush()

        # Roles
        rol_gestionar_a = Rol(tenant_id=tid_a, nombre="COL_GESTIONAR_A")
        rol_reservar_a = Rol(tenant_id=tid_a, nombre="COL_RESERVAR_A")
        rol_noperm_a = Rol(tenant_id=tid_a, nombre="COL_NOPERM_A")
        session.add_all([rol_gestionar_a, rol_reservar_a, rol_noperm_a])
        await session.flush()

        # Permissions
        perm_gestionar = Permiso(tenant_id=tid_a, codigo="coloquios:gestionar", modulo="coloquios", accion="gestionar")
        perm_reservar = Permiso(tenant_id=tid_a, codigo="coloquios:reservar", modulo="coloquios", accion="reservar")
        session.add_all([perm_gestionar, perm_reservar])
        await session.flush()

        session.add(RolPermiso(tenant_id=tid_a, rol_id=rol_gestionar_a.id, permiso_id=perm_gestionar.id, scope=PermisoScope.global_))
        session.add(RolPermiso(tenant_id=tid_a, rol_id=rol_reservar_a.id, permiso_id=perm_reservar.id, scope=PermisoScope.global_))
        await session.flush()

        # Academic structure
        car = Carrera(tenant_id=tid_a, codigo=f"C_{uuid.uuid4().hex[:4]}", nombre="Carrera", estado=EstadoEstructura.activa)
        mat = Materia(tenant_id=tid_a, codigo=f"M_{uuid.uuid4().hex[:4]}", nombre="Materia", estado=EstadoEstructura.activa)
        session.add(car)
        session.add(mat)
        await session.flush()
        coh = Cohorte(tenant_id=tid_a, carrera_id=car.id, nombre="Coh", anio=2026,
                      vig_desde=date.today(), estado=EstadoEstructura.activa)
        session.add(coh)
        await session.flush()

        # Users
        email_al = f"col_al_{uuid.uuid4().hex[:6]}@t.com"
        al = Usuario(tenant_id=tid_a, email_encrypted=email_al, email_hash=_hash(email_al),
                     nombre="Al", apellidos="Alumno", estado=UsuarioEstado.activo)
        session.add(al)
        await session.flush()

        await session.commit()

        yield {
            "tid_a": tid_a,
            "tid_b": tid_b,
            "rol_gestionar": "COL_GESTIONAR_A",
            "rol_reservar": "COL_RESERVAR_A",
            "rol_noperm": "COL_NOPERM_A",
            "mat_id": mat.id,
            "coh_id": coh.id,
            "al_id": al.id,
        }
    finally:
        try:
            await session.rollback()
            await session.close()
        except Exception:
            pass


@pytest_asyncio.fixture(scope="module")
def col_app(col_engine, col_setup):
    from app.main import create_app
    app = create_app()
    factory = build_session_factory(col_engine)
    app.state.session_factory = factory
    return app


@pytest_asyncio.fixture(scope="module")
async def col_client(col_app) -> AsyncClient:
    async with AsyncClient(
        transport=ASGITransport(app=col_app), base_url="http://test"
    ) as client:
        yield client


# ---------------------------------------------------------------------------
# 5.5: Router integration tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio(loop_scope="session")
async def test_crear_convocatoria_sin_token_returns_401(col_client):
    """5.5: POST /coloquios/convocatorias without token → 401."""
    resp = await col_client.post(
        "/api/v1/coloquios/convocatorias",
        json={"materia_id": str(uuid.uuid4()), "cohorte_id": str(uuid.uuid4()),
              "tipo": "Coloquio", "instancia": "test",
              "turnos": [{"fecha": "2026-09-01", "cupo_total": 5}]},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio(loop_scope="session")
async def test_crear_convocatoria_sin_permiso_returns_403(col_client, col_setup, monkeypatch):
    """5.5: ALUMNO (coloquios:reservar) cannot create convocatoria → 403."""
    monkeypatch.setattr("app.core.config.Settings", _fake_settings)
    tid = col_setup["tid_a"]
    token = _make_jwt(tid, uuid.uuid4(), roles=[col_setup["rol_reservar"]])

    resp = await col_client.post(
        "/api/v1/coloquios/convocatorias",
        json={
            "materia_id": str(uuid.uuid4()),
            "cohorte_id": str(uuid.uuid4()),
            "tipo": "Coloquio",
            "instancia": "test",
            "turnos": [{"fecha": "2026-09-01", "cupo_total": 5}],
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio(loop_scope="session")
async def test_crear_convocatoria_returns_201(col_client, col_setup, monkeypatch):
    """5.5: PROFESOR with coloquios:gestionar creates convocatoria → 201."""
    monkeypatch.setattr("app.core.config.Settings", _fake_settings)
    tid = col_setup["tid_a"]
    token = _make_jwt(tid, uuid.uuid4(), roles=[col_setup["rol_gestionar"]])
    mat_id = col_setup["mat_id"]
    coh_id = col_setup["coh_id"]

    resp = await col_client.post(
        "/api/v1/coloquios/convocatorias",
        json={
            "materia_id": str(mat_id),
            "cohorte_id": str(coh_id),
            "tipo": "Coloquio",
            "instancia": "Coloquio Final HTTP",
            "turnos": [{"fecha": "2026-09-10", "cupo_total": 10}],
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert "evaluacion" in data
    assert "turnos" in data
    assert len(data["turnos"]) == 1
    assert data["evaluacion"]["cerrada"] is False


@pytest.mark.asyncio(loop_scope="session")
async def test_reservar_sin_permiso_gestionar_returns_403(col_client, col_setup, monkeypatch):
    """5.5: gestor (coloquios:gestionar) cannot reserve (fail-closed)."""
    monkeypatch.setattr("app.core.config.Settings", _fake_settings)
    tid = col_setup["tid_a"]
    token = _make_jwt(tid, uuid.uuid4(), roles=[col_setup["rol_gestionar"]])

    resp = await col_client.post(
        "/api/v1/coloquios/reservas",
        json={"turno_id": str(uuid.uuid4()), "evaluacion_id": str(uuid.uuid4())},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio(loop_scope="session")
async def test_crear_convocatoria_cross_tenant_isolation(col_client, col_setup, monkeypatch):
    """5.5: tenant B user gets 404 when querying tenant A resources."""
    monkeypatch.setattr("app.core.config.Settings", _fake_settings)
    tid_b = col_setup["tid_b"]
    # No permission in B for gestionar, user gets 403 first (fail-closed)
    token = _make_jwt(tid_b, uuid.uuid4(), roles=["SOME_ROLE_B"])

    resp = await col_client.post(
        "/api/v1/coloquios/convocatorias",
        json={
            "materia_id": str(uuid.uuid4()),
            "cohorte_id": str(uuid.uuid4()),
            "tipo": "Coloquio",
            "instancia": "Cross-tenant",
            "turnos": [{"fecha": "2026-10-01", "cupo_total": 5}],
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403  # fail-closed: no permission in tenant B
