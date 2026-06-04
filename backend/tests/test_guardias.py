"""
test_guardias.py — TDD suite para C-13 guardias.

RED → GREEN → TRIANGULATE → REFACTOR cycle para tasks 8.1–8.7.

Tests:
    8.1 RED:  test_registrar_guardia_resuelve_asignacion_de_sesion
    8.3 RED:  test_registrar_guardia_ignores_body_asignacion_id
    8.4 RED:  test_consultar_guardias_global_filtra_por_materia
    8.5 RED:  test_consultar_guardias_filtra_por_estado
    8.6 RED:  test_exportar_guardias_genera_csv
    8.7 RED:  test_guardias_tenant_isolation
    Router:   10.6 / 10.7

DB real: activia_trace_test. Sin mocks de DB.
"""
import datetime
import uuid
from datetime import date, time

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from pydantic import ValidationError

from app.core.database import build_session_factory
from app.core.dependencies import CurrentUser
from app.models.encuentro import DiaSemana, GuardiaEstado
from app.models.estructura import Carrera, Cohorte, EstadoEstructura, Materia
from app.models.rbac import Permiso, PermisoScope, Rol, RolPermiso
from app.models.tenant import Tenant, TenantEstado
from app.models.usuario import Asignacion, RolAsignacion, Usuario, UsuarioEstado
from app.repositories.audit_repository import AuditRepository
from app.repositories.guardia_repository import GuardiaRepository
from app.repositories.usuario_repository import AsignacionRepository, UsuarioRepository
from app.schemas.guardia import GuardiaFiltros, GuardiaRead, RegistrarGuardiaRequest
from app.services.guardia_service import GuardiaService


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

TEST_SECRET_KEY = "supersecretkeyfortesting1234567890"
TEST_ENCRYPTION_KEY = "E" * 32


def _make_jwt(tenant_id: uuid.UUID, user_id: uuid.UUID, roles: list, secret: str = TEST_SECRET_KEY) -> str:
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


def _make_current_user(tid: uuid.UUID, uid: uuid.UUID, roles: list | None = None) -> CurrentUser:
    return CurrentUser(user_id=uid, tenant_id=tid, roles=roles or ["TESTROL"])


def _make_usuario(tid: uuid.UUID, suffix: str) -> Usuario:
    from app.core.security.passwords import email_lookup_hash as _hash
    email = f"grd_{suffix}_{uuid.uuid4().hex[:6]}@test.com"
    return Usuario(
        tenant_id=tid,
        email_encrypted=email,
        email_hash=_hash(email),
        nombre="Test",
        apellidos=suffix,
        estado=UsuarioEstado.activo,
    )


# ---------------------------------------------------------------------------
# Session-scoped fixtures
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture(scope="module")
async def grd_setup(test_engine, create_tables):
    """
    Creates tenants, RBAC, academic structure, and a TUTOR asignacion for testing.
    """
    factory = build_session_factory(test_engine)
    session = factory()

    tid_a = uuid.uuid4()
    tid_b = uuid.uuid4()
    session.add(Tenant(id=tid_a, nombre="Guardia Tenant A", estado=TenantEstado.ACTIVO))
    session.add(Tenant(id=tid_b, nombre="Guardia Tenant B", estado=TenantEstado.ACTIVO))
    await session.flush()

    rol_a = Rol(tenant_id=tid_a, nombre="GRD_ROL_A")
    rol_b = Rol(tenant_id=tid_b, nombre="GRD_ROL_B")
    session.add_all([rol_a, rol_b])
    await session.flush()

    perm_a = Permiso(tenant_id=tid_a, codigo="encuentros:gestionar", modulo="encuentros", accion="gestionar")
    perm_b = Permiso(tenant_id=tid_b, codigo="encuentros:gestionar", modulo="encuentros", accion="gestionar")
    session.add_all([perm_a, perm_b])
    await session.flush()

    session.add(RolPermiso(tenant_id=tid_a, rol_id=rol_a.id, permiso_id=perm_a.id, scope=PermisoScope.global_))
    session.add(RolPermiso(tenant_id=tid_b, rol_id=rol_b.id, permiso_id=perm_b.id, scope=PermisoScope.global_))
    await session.flush()

    # Academic structure
    carrera_a = Carrera(tenant_id=tid_a, codigo=f"GC_{uuid.uuid4().hex[:4]}", nombre="Carrera GA", estado=EstadoEstructura.activa)
    materia_a = Materia(tenant_id=tid_a, codigo=f"GM_{uuid.uuid4().hex[:4]}", nombre="Materia GA", estado=EstadoEstructura.activa)
    carrera_b = Carrera(tenant_id=tid_b, codigo=f"GB_{uuid.uuid4().hex[:4]}", nombre="Carrera GB", estado=EstadoEstructura.activa)
    materia_b = Materia(tenant_id=tid_b, codigo=f"GN_{uuid.uuid4().hex[:4]}", nombre="Materia GB", estado=EstadoEstructura.activa)
    session.add_all([carrera_a, materia_a, carrera_b, materia_b])
    await session.flush()

    cohorte_a = Cohorte(tenant_id=tid_a, carrera_id=carrera_a.id, nombre="Coh GA", anio=2026, vig_desde=date.today(), estado=EstadoEstructura.activa)
    cohorte_b = Cohorte(tenant_id=tid_b, carrera_id=carrera_b.id, nombre="Coh GB", anio=2026, vig_desde=date.today(), estado=EstadoEstructura.activa)
    session.add_all([cohorte_a, cohorte_b])
    await session.flush()

    # TUTOR user + asignacion for tenant A
    usr_repo_a = UsuarioRepository(session=session, tenant_id=tid_a)
    user_tutor = _make_usuario(tid_a, "tutor_a")
    await usr_repo_a.add(user_tutor)

    asig_repo_a = AsignacionRepository(session=session, tenant_id=tid_a)
    asig_tutor = Asignacion(
        usuario_id=user_tutor.id,
        rol=RolAsignacion.TUTOR,
        materia_id=materia_a.id,
        carrera_id=carrera_a.id,
        cohorte_id=cohorte_a.id,
        desde=date.today(),
        comisiones=[],
    )
    await asig_repo_a.add(asig_tutor)

    # TUTOR user for tenant B
    usr_repo_b = UsuarioRepository(session=session, tenant_id=tid_b)
    user_tutor_b = _make_usuario(tid_b, "tutor_b")
    await usr_repo_b.add(user_tutor_b)

    asig_repo_b = AsignacionRepository(session=session, tenant_id=tid_b)
    asig_tutor_b = Asignacion(
        usuario_id=user_tutor_b.id,
        rol=RolAsignacion.TUTOR,
        materia_id=materia_b.id,
        carrera_id=carrera_b.id,
        cohorte_id=cohorte_b.id,
        desde=date.today(),
        comisiones=[],
    )
    await asig_repo_b.add(asig_tutor_b)

    await session.commit()
    await session.close()

    return {
        "tid_a": tid_a,
        "tid_b": tid_b,
        "rol_a": "GRD_ROL_A",
        "rol_b": "GRD_ROL_B",
        "mat_a": materia_a.id,
        "car_a": carrera_a.id,
        "coh_a": cohorte_a.id,
        "mat_b": materia_b.id,
        "car_b": carrera_b.id,
        "coh_b": cohorte_b.id,
        "user_tutor": user_tutor.id,
        "user_tutor_b": user_tutor_b.id,
        "asig_tutor": asig_tutor.id,
        "asig_tutor_b": asig_tutor_b.id,
    }


@pytest_asyncio.fixture(scope="module")
def grd_app(test_engine, grd_setup):
    from app.main import create_app
    app = create_app()
    factory = build_session_factory(test_engine)
    app.state.session_factory = factory
    return app


@pytest_asyncio.fixture(scope="module")
async def grd_client(grd_app) -> AsyncClient:
    async with AsyncClient(
        transport=ASGITransport(app=grd_app), base_url="http://test"
    ) as client:
        yield client


def _make_grd_service(session, tenant_id):
    grd_repo = GuardiaRepository(session=session, tenant_id=tenant_id)
    asig_repo = AsignacionRepository(session=session, tenant_id=tenant_id)
    audit_repo = AuditRepository(session=session, tenant_id=tenant_id)
    return GuardiaService(
        guardia_repo=grd_repo,
        asignacion_repo=asig_repo,
        audit_repo=audit_repo,
    )


# ---------------------------------------------------------------------------
# 8.1 RED → 8.2 GREEN
# test_registrar_guardia_resuelve_asignacion_de_sesion
# ---------------------------------------------------------------------------

@pytest.mark.asyncio(loop_scope="session")
async def test_registrar_guardia_resuelve_asignacion_de_sesion(db_session, create_tables, grd_setup, monkeypatch):
    """8.1 RED: TUTOR registers → asignacion_id from current_user, tenant from session, estado=Pendiente."""
    monkeypatch.setattr("app.core.config.Settings", _fake_settings)

    tid = grd_setup["tid_a"]
    mat_id = grd_setup["mat_a"]
    car_id = grd_setup["car_a"]
    coh_id = grd_setup["coh_a"]
    user_tutor = grd_setup["user_tutor"]
    asig_id = grd_setup["asig_tutor"]

    req = RegistrarGuardiaRequest(
        materia_id=mat_id,
        carrera_id=car_id,
        cohorte_id=coh_id,
        dia=DiaSemana.Lunes,
        horario="08:00-10:00",
    )
    actor = _make_current_user(tid, user_tutor, roles=["TUTOR"])

    svc = _make_grd_service(db_session, tid)
    guardia = await svc.registrar(req, actor)

    assert guardia.asignacion_id == asig_id
    assert guardia.estado == GuardiaEstado.Pendiente
    assert guardia.materia_id == mat_id

    # Verify in DB
    grd_repo = GuardiaRepository(session=db_session, tenant_id=tid)
    db_grd = await grd_repo.get_by_id(guardia.id)
    assert db_grd is not None
    assert db_grd.tenant_id == tid

    # Cleanup
    await grd_repo.delete(db_grd)
    await db_session.commit()


# ---------------------------------------------------------------------------
# 8.3 RED → GREEN: schema extra='forbid'
# ---------------------------------------------------------------------------

def test_registrar_guardia_ignores_body_asignacion_id():
    """8.3: RegistrarGuardiaRequest with asignacion_id field → ValidationError (extra='forbid')."""
    with pytest.raises(ValidationError):
        RegistrarGuardiaRequest(
            materia_id=uuid.uuid4(),
            carrera_id=uuid.uuid4(),
            cohorte_id=uuid.uuid4(),
            dia=DiaSemana.Martes,
            horario="09:00-11:00",
            asignacion_id=uuid.uuid4(),  # forbidden field
        )


def test_registrar_guardia_ignores_body_tenant_id():
    """8.3: RegistrarGuardiaRequest with tenant_id → ValidationError."""
    with pytest.raises(ValidationError):
        RegistrarGuardiaRequest(
            materia_id=uuid.uuid4(),
            carrera_id=uuid.uuid4(),
            cohorte_id=uuid.uuid4(),
            dia=DiaSemana.Martes,
            horario="09:00-11:00",
            tenant_id=uuid.uuid4(),  # forbidden field
        )


# ---------------------------------------------------------------------------
# 8.4 RED → GREEN: global filter by materia
# ---------------------------------------------------------------------------

@pytest.mark.asyncio(loop_scope="session")
async def test_consultar_guardias_global_filtra_por_materia(db_session, create_tables, grd_setup, monkeypatch):
    """8.4 RED: COORDINADOR queries by materia → all tutors' guardias of that materia."""
    monkeypatch.setattr("app.core.config.Settings", _fake_settings)

    tid = grd_setup["tid_a"]
    mat_id = grd_setup["mat_a"]
    car_id = grd_setup["car_a"]
    coh_id = grd_setup["coh_a"]
    user_tutor = grd_setup["user_tutor"]

    actor = _make_current_user(tid, user_tutor, roles=["TUTOR"])
    svc = _make_grd_service(db_session, tid)

    # Register 2 guardias
    g1 = await svc.registrar(RegistrarGuardiaRequest(
        materia_id=mat_id, carrera_id=car_id, cohorte_id=coh_id,
        dia=DiaSemana.Lunes, horario="08:00-10:00",
    ), actor)
    g2 = await svc.registrar(RegistrarGuardiaRequest(
        materia_id=mat_id, carrera_id=car_id, cohorte_id=coh_id,
        dia=DiaSemana.Martes, horario="10:00-12:00",
    ), actor)

    # COORDINADOR queries by materia
    coord_actor = _make_current_user(tid, uuid.uuid4(), roles=["COORDINADOR"])
    filtros = GuardiaFiltros(materia_id=mat_id)
    result = await svc.consultar(filtros, coord_actor)

    ids = {g.id for g in result}
    assert g1.id in ids
    assert g2.id in ids

    # Cleanup
    grd_repo = GuardiaRepository(session=db_session, tenant_id=tid)
    for gid in [g1.id, g2.id]:
        db_grd = await grd_repo.get_by_id(gid)
        if db_grd:
            await grd_repo.delete(db_grd)
    await db_session.commit()


# ---------------------------------------------------------------------------
# 8.5 RED → GREEN: filter by estado
# ---------------------------------------------------------------------------

@pytest.mark.asyncio(loop_scope="session")
async def test_consultar_guardias_filtra_por_estado(db_session, create_tables, grd_setup, monkeypatch):
    """8.5 RED: estado=Realizada → only that state returned."""
    monkeypatch.setattr("app.core.config.Settings", _fake_settings)

    tid = grd_setup["tid_a"]
    mat_id = grd_setup["mat_a"]
    car_id = grd_setup["car_a"]
    coh_id = grd_setup["coh_a"]
    user_tutor = grd_setup["user_tutor"]

    actor = _make_current_user(tid, user_tutor, roles=["TUTOR"])
    svc = _make_grd_service(db_session, tid)

    g_pendiente = await svc.registrar(RegistrarGuardiaRequest(
        materia_id=mat_id, carrera_id=car_id, cohorte_id=coh_id,
        dia=DiaSemana.Jueves, horario="14:00-16:00",
        estado=GuardiaEstado.Pendiente,
    ), actor)
    g_realizada = await svc.registrar(RegistrarGuardiaRequest(
        materia_id=mat_id, carrera_id=car_id, cohorte_id=coh_id,
        dia=DiaSemana.Viernes, horario="16:00-18:00",
        estado=GuardiaEstado.Realizada,
    ), actor)

    coord_actor = _make_current_user(tid, uuid.uuid4(), roles=["COORDINADOR"])
    filtros = GuardiaFiltros(materia_id=mat_id, estado=GuardiaEstado.Realizada)
    result = await svc.consultar(filtros, coord_actor)

    ids = {g.id for g in result}
    assert g_realizada.id in ids
    assert g_pendiente.id not in ids

    # Cleanup
    grd_repo = GuardiaRepository(session=db_session, tenant_id=tid)
    for gid in [g_pendiente.id, g_realizada.id]:
        db_grd = await grd_repo.get_by_id(gid)
        if db_grd:
            await grd_repo.delete(db_grd)
    await db_session.commit()


# ---------------------------------------------------------------------------
# 8.6 RED → GREEN: CSV export
# ---------------------------------------------------------------------------

@pytest.mark.asyncio(loop_scope="session")
async def test_exportar_guardias_genera_csv(db_session, create_tables, grd_setup, monkeypatch):
    """8.6 RED: export filtered register → CSV with one row per guardia."""
    monkeypatch.setattr("app.core.config.Settings", _fake_settings)

    tid = grd_setup["tid_a"]
    mat_id = grd_setup["mat_a"]
    car_id = grd_setup["car_a"]
    coh_id = grd_setup["coh_a"]
    user_tutor = grd_setup["user_tutor"]

    actor = _make_current_user(tid, user_tutor, roles=["TUTOR"])
    svc = _make_grd_service(db_session, tid)

    g = await svc.registrar(RegistrarGuardiaRequest(
        materia_id=mat_id, carrera_id=car_id, cohorte_id=coh_id,
        dia=DiaSemana.Lunes, horario="07:00-09:00",
    ), actor)

    coord_actor = _make_current_user(tid, uuid.uuid4(), roles=["COORDINADOR"])
    filtros = GuardiaFiltros(materia_id=mat_id)
    csv_content = await svc.exportar(filtros, coord_actor)

    lines = csv_content.strip().split("\n")
    assert len(lines) >= 2, f"Expected header + data rows, got {len(lines)} lines"
    header = lines[0]
    assert "guardia_id" in header or "id" in header
    assert "asignacion_id" in header
    assert str(g.id) in csv_content

    # Cleanup
    grd_repo = GuardiaRepository(session=db_session, tenant_id=tid)
    db_grd = await grd_repo.get_by_id(g.id)
    if db_grd:
        await grd_repo.delete(db_grd)
    await db_session.commit()


# ---------------------------------------------------------------------------
# 8.7 RED → GREEN: tenant isolation
# ---------------------------------------------------------------------------

@pytest.mark.asyncio(loop_scope="session")
async def test_guardias_tenant_isolation(db_session, create_tables, grd_setup, monkeypatch):
    """8.7 RED: T1 guardias not visible/exportable in T2."""
    monkeypatch.setattr("app.core.config.Settings", _fake_settings)

    tid_a = grd_setup["tid_a"]
    tid_b = grd_setup["tid_b"]
    mat_a = grd_setup["mat_a"]
    mat_b = grd_setup["mat_b"]
    car_a = grd_setup["car_a"]
    car_b = grd_setup["car_b"]
    coh_a = grd_setup["coh_a"]
    coh_b = grd_setup["coh_b"]
    user_a = grd_setup["user_tutor"]
    user_b = grd_setup["user_tutor_b"]

    actor_a = _make_current_user(tid_a, user_a, roles=["TUTOR"])
    actor_b = _make_current_user(tid_b, user_b, roles=["TUTOR"])

    svc_a = _make_grd_service(db_session, tid_a)
    svc_b = _make_grd_service(db_session, tid_b)

    ga = await svc_a.registrar(RegistrarGuardiaRequest(
        materia_id=mat_a, carrera_id=car_a, cohorte_id=coh_a,
        dia=DiaSemana.Lunes, horario="06:00-08:00",
    ), actor_a)
    gb = await svc_b.registrar(RegistrarGuardiaRequest(
        materia_id=mat_b, carrera_id=car_b, cohorte_id=coh_b,
        dia=DiaSemana.Martes, horario="06:00-08:00",
    ), actor_b)

    # Tenant A COORDINADOR only sees tenant A
    coord_a = _make_current_user(tid_a, uuid.uuid4(), roles=["COORDINADOR"])
    result_a = await svc_a.consultar(GuardiaFiltros(), coord_a)
    ids_a = {g.id for g in result_a}
    assert ga.id in ids_a
    assert gb.id not in ids_a

    # CSV export also scoped
    csv_a = await svc_a.exportar(GuardiaFiltros(), coord_a)
    assert str(ga.id) in csv_a
    assert str(gb.id) not in csv_a

    # Cleanup
    grd_repo_a = GuardiaRepository(session=db_session, tenant_id=tid_a)
    grd_repo_b = GuardiaRepository(session=db_session, tenant_id=tid_b)
    db_ga = await grd_repo_a.get_by_id(ga.id)
    if db_ga:
        await grd_repo_a.delete(db_ga)
    db_gb = await grd_repo_b.get_by_id(gb.id)
    if db_gb:
        await grd_repo_b.delete(db_gb)
    await db_session.commit()


# ---------------------------------------------------------------------------
# HTTP router integration tests (tasks 10.6 / 10.7)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio(loop_scope="session")
async def test_registrar_guardia_endpoint_creates_guardia(grd_client, grd_setup, db_session, monkeypatch):
    """10.6: POST /guardias → 201 with GuardiaRead."""
    monkeypatch.setattr("app.core.config.Settings", _fake_settings)
    tid = grd_setup["tid_a"]
    mat_id = grd_setup["mat_a"]
    car_id = grd_setup["car_a"]
    coh_id = grd_setup["coh_a"]
    user_tutor = grd_setup["user_tutor"]
    token = _make_jwt(tid, user_tutor, roles=[grd_setup["rol_a"]])

    resp = await grd_client.post(
        "/api/v1/guardias",
        json={
            "materia_id": str(mat_id),
            "carrera_id": str(car_id),
            "cohorte_id": str(coh_id),
            "dia": "Lunes",
            "horario": "08:00-10:00",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert "id" in data
    assert data["dia"] == "Lunes"

    # Cleanup
    grd_repo = GuardiaRepository(session=db_session, tenant_id=tid)
    db_grd = await grd_repo.get_by_id(uuid.UUID(data["id"]))
    if db_grd:
        await grd_repo.delete(db_grd)
    await db_session.commit()


@pytest.mark.asyncio(loop_scope="session")
async def test_guardia_endpoint_unauthorized_returns_403(grd_client, grd_setup, monkeypatch):
    """10.6: POST /guardias without permission → 403."""
    monkeypatch.setattr("app.core.config.Settings", _fake_settings)
    tid = grd_setup["tid_a"]
    token = _make_jwt(tid, uuid.uuid4(), roles=["SIN_PERMISO"])

    resp = await grd_client.post(
        "/api/v1/guardias",
        json={
            "materia_id": str(uuid.uuid4()),
            "carrera_id": str(uuid.uuid4()),
            "cohorte_id": str(uuid.uuid4()),
            "dia": "Lunes",
            "horario": "08:00-10:00",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio(loop_scope="session")
async def test_export_guardias_endpoint_returns_csv(grd_client, grd_setup, db_session, monkeypatch):
    """10.7: GET /guardias/export → CSV attachment."""
    monkeypatch.setattr("app.core.config.Settings", _fake_settings)
    tid = grd_setup["tid_a"]
    mat_id = grd_setup["mat_a"]
    car_id = grd_setup["car_a"]
    coh_id = grd_setup["coh_a"]
    user_tutor = grd_setup["user_tutor"]
    token = _make_jwt(tid, user_tutor, roles=[grd_setup["rol_a"]])

    # Create a guardia first
    post_resp = await grd_client.post(
        "/api/v1/guardias",
        json={
            "materia_id": str(mat_id),
            "carrera_id": str(car_id),
            "cohorte_id": str(coh_id),
            "dia": "Martes",
            "horario": "10:00-12:00",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert post_resp.status_code == 201
    grd_id = post_resp.json()["id"]

    resp = await grd_client.get(
        f"/api/v1/guardias/export?materia_id={mat_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200, resp.text
    assert "text/csv" in resp.headers.get("content-type", "")
    assert "attachment" in resp.headers.get("content-disposition", "")

    # Cleanup
    grd_repo = GuardiaRepository(session=db_session, tenant_id=tid)
    db_grd = await grd_repo.get_by_id(uuid.UUID(grd_id))
    if db_grd:
        await grd_repo.delete(db_grd)
    await db_session.commit()
