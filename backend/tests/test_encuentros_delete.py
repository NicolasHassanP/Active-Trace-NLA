"""
test_encuentros_delete.py — TDD para Bug C: DELETE /encuentros/instancias/{id}.

Ciclo TDD:
    RED  : DELETE 204 en éxito, 404 si no existe, GET posterior excluye borradas.
    GREEN: agregar endpoint DELETE + service.dar_baja_instancia + repo.dar_baja.
    TRIANGULATE: soft delete (deleted_at seteado), GET /instancias no las muestra.
    REFACTOR: verificar permiso y tenant isolation.

DB real: activia_trace_test. Sin mocks de DB.
Usa los fixtures session-scoped de conftest (test_engine, create_tables, db_session).
"""
import uuid
from datetime import date, time

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.core.database import build_session_factory
from app.models.encuentro import DiaSemana, InstanciaEncuentroEstado
from app.models.estructura import Carrera, Cohorte, EstadoEstructura, Materia
from app.models.rbac import Permiso, PermisoScope, Rol, RolPermiso
from app.models.tenant import Tenant, TenantEstado
from app.models.usuario import Asignacion, RolAsignacion
from app.repositories.encuentro_repository import (
    InstanciaEncuentroRepository,
    SlotEncuentroRepository,
)
from app.repositories.usuario_repository import AsignacionRepository
from app.schemas.encuentro import CrearSlotRequest
from app.services.encuentro_service import EncuentroService
from tests.conftest import create_usuario_con_identidad
import datetime as dt


# ---------------------------------------------------------------------------
# JWT helper
# ---------------------------------------------------------------------------

TEST_SECRET = "supersecretkeyfortesting1234567890"
TEST_ENC_KEY = "E" * 32


def _make_jwt(tenant_id, user_id, roles):
    from jose import jwt as jose_jwt
    now = dt.datetime.now(tz=dt.timezone.utc)
    payload = {
        "sub": str(user_id),
        "tenant_id": str(tenant_id),
        "roles": roles,
        "iat": int(now.timestamp()),
        "exp": int((now + dt.timedelta(minutes=30)).timestamp()),
        "type": "access",
    }
    return jose_jwt.encode(payload, TEST_SECRET, algorithm="HS256")


def _fake_settings():
    class FakeSettings:
        SECRET_KEY = TEST_SECRET
        ENCRYPTION_KEY = TEST_ENC_KEY
        ACCESS_TOKEN_EXPIRE_MINUTES = 30
        MFA_TOKEN_EXPIRE_MINUTES = 10
        REFRESH_TOKEN_EXPIRE_DAYS = 7
        RECOVERY_TOKEN_EXPIRE_MINUTES = 30
        LOGIN_RATE_LIMIT = "10/minute"
    return FakeSettings()


# ---------------------------------------------------------------------------
# Module-scoped setup
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture(scope="module")
async def del_setup(test_engine, create_tables):
    """Creates one tenant with RBAC + academic structure + user + asignacion."""
    factory = build_session_factory(test_engine)
    session = factory()

    tid = uuid.uuid4()
    session.add(Tenant(id=tid, nombre=f"DelEnc_{tid.hex[:4]}", estado=TenantEstado.ACTIVO))
    await session.flush()

    rol = Rol(tenant_id=tid, nombre="DEL_ROL")
    session.add(rol)
    await session.flush()

    perm = Permiso(
        tenant_id=tid,
        codigo="encuentros:gestionar",
        modulo="encuentros",
        accion="gestionar",
    )
    session.add(perm)
    await session.flush()

    session.add(RolPermiso(
        tenant_id=tid, rol_id=rol.id, permiso_id=perm.id, scope=PermisoScope.global_
    ))
    await session.flush()

    carrera = Carrera(
        tenant_id=tid,
        codigo=f"DC_{uuid.uuid4().hex[:4]}",
        nombre="Carrera Del",
        estado=EstadoEstructura.activa,
    )
    materia = Materia(
        tenant_id=tid,
        codigo=f"DM_{uuid.uuid4().hex[:4]}",
        nombre="Materia Del",
        estado=EstadoEstructura.activa,
    )
    session.add(carrera)
    session.add(materia)
    await session.flush()

    cohorte = Cohorte(
        tenant_id=tid,
        carrera_id=carrera.id,
        nombre="Coh Del",
        anio=2026,
        vig_desde=date.today(),
        estado=EstadoEstructura.activa,
    )
    session.add(cohorte)
    await session.flush()

    user = await create_usuario_con_identidad(
        session, tid,
        email=f"del_enc_{uuid.uuid4().hex[:6]}@test.com",
        nombre="Test", apellidos="DelEnc",
    )

    asig_repo = AsignacionRepository(session=session, tenant_id=tid)
    asig = Asignacion(
        usuario_id=user.id,
        rol=RolAsignacion.COORDINADOR,
        materia_id=materia.id,
        carrera_id=carrera.id,
        cohorte_id=cohorte.id,
        desde=date.today(),
        comisiones=[],
    )
    await asig_repo.add(asig)
    await session.commit()
    await session.close()

    return {
        "tid": tid,
        "rol": "DEL_ROL",
        "mat_id": materia.id,
        "user_id": user.id,
        "auth_id": user.auth_identity_id,
        "asig_id": asig.id,
    }


@pytest_asyncio.fixture(scope="module")
def del_app(test_engine, del_setup):
    from app.main import create_app
    app = create_app()
    factory = build_session_factory(test_engine)
    app.state.session_factory = factory
    return app


@pytest_asyncio.fixture(scope="module")
async def del_client(del_app) -> AsyncClient:
    async with AsyncClient(
        transport=ASGITransport(app=del_app), base_url="http://test"
    ) as client:
        yield client


def _make_enc_service(session, tid, del_setup):
    from app.repositories.audit_repository import AuditRepository
    slot_repo = SlotEncuentroRepository(session=session, tenant_id=tid)
    inst_repo = InstanciaEncuentroRepository(session=session, tenant_id=tid)
    asig_repo = AsignacionRepository(session=session, tenant_id=tid)
    audit_repo = AuditRepository(session=session, tenant_id=tid)
    return EncuentroService(
        slot_repo=slot_repo,
        instancia_repo=inst_repo,
        asignacion_repo=asig_repo,
        audit_repo=audit_repo,
    )


# ---------------------------------------------------------------------------
# RED: DELETE /encuentros/instancias/{id} → 204
# ---------------------------------------------------------------------------

@pytest.mark.asyncio(loop_scope="session")
async def test_delete_instancia_returns_204(del_client, del_setup, db_session, monkeypatch):
    """
    RED: DELETE /encuentros/instancias/{id} con permiso → 204.
    Sin el endpoint, retorna 405 Method Not Allowed → test falla.
    """
    monkeypatch.setattr("app.core.config.Settings", _fake_settings)
    tid = del_setup["tid"]
    mat_id = del_setup["mat_id"]
    token = _make_jwt(tid, del_setup["auth_id"], roles=[del_setup["rol"]])

    # Create a slot with one instance via API
    slot_resp = await del_client.post(
        "/api/v1/encuentros/slots",
        json={
            "materia_id": str(mat_id),
            "titulo": "Para borrar",
            "hora": "10:00:00",
            "fecha_unica": "2026-12-20",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert slot_resp.status_code == 201, slot_resp.text
    instancia_id = slot_resp.json()["instancias"][0]["id"]

    # DELETE the instance
    del_resp = await del_client.delete(
        f"/api/v1/encuentros/instancias/{instancia_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert del_resp.status_code == 204, f"Expected 204, got {del_resp.status_code}: {del_resp.text}"


# ---------------------------------------------------------------------------
# TRIANGULATE: GET /instancias depois de DELETE não mostra instância borrada
# ---------------------------------------------------------------------------

@pytest.mark.asyncio(loop_scope="session")
async def test_delete_instancia_soft_delete_excluida_de_listado(
    del_client, del_setup, db_session, monkeypatch
):
    """
    TRIANGULATE: tras DELETE, GET /instancias no incluye la instancia borrada.
    También verifica que deleted_at fue seteado (soft delete, no hard delete).
    """
    monkeypatch.setattr("app.core.config.Settings", _fake_settings)
    tid = del_setup["tid"]
    mat_id = del_setup["mat_id"]
    token = _make_jwt(tid, del_setup["auth_id"], roles=[del_setup["rol"]])

    # Create slot
    slot_resp = await del_client.post(
        "/api/v1/encuentros/slots",
        json={
            "materia_id": str(mat_id),
            "titulo": "SoftDelTest",
            "hora": "11:00:00",
            "fecha_unica": "2026-12-21",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert slot_resp.status_code == 201
    instancia_id = slot_resp.json()["instancias"][0]["id"]
    slot_id = slot_resp.json()["slot"]["id"]

    # DELETE
    del_resp = await del_client.delete(
        f"/api/v1/encuentros/instancias/{instancia_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert del_resp.status_code == 204

    # GET /instancias — la instancia borrada NO debe aparecer
    list_resp = await del_client.get(
        "/api/v1/encuentros/instancias",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert list_resp.status_code == 200
    ids_en_listado = [i["id"] for i in list_resp.json()]
    assert instancia_id not in ids_en_listado, \
        "La instancia borrada no debe aparecer en el listado"

    # Verificar soft delete: deleted_at seteado (no hard delete)
    from sqlalchemy import select
    from app.models.encuentro import InstanciaEncuentro
    stmt = select(InstanciaEncuentro).where(
        InstanciaEncuentro.id == uuid.UUID(instancia_id),
    )
    r = await db_session.execute(stmt)
    inst = r.scalar_one_or_none()
    assert inst is not None, "La instancia debe existir en DB (soft delete, no hard delete)"
    assert inst.deleted_at is not None, "deleted_at debe estar seteado tras el DELETE"

    # Cleanup slot (instance already soft-deleted)
    slot_repo = SlotEncuentroRepository(session=db_session, tenant_id=tid)
    slot = await slot_repo.get_by_id(uuid.UUID(slot_id))
    if slot:
        await slot_repo.delete(slot)
    await db_session.commit()


# ---------------------------------------------------------------------------
# TRIANGULATE: DELETE 404 si la instancia no existe
# ---------------------------------------------------------------------------

@pytest.mark.asyncio(loop_scope="session")
async def test_delete_instancia_inexistente_returns_404(
    del_client, del_setup, monkeypatch
):
    """
    TRIANGULATE: DELETE /encuentros/instancias/{id} con id inexistente → 404.
    """
    monkeypatch.setattr("app.core.config.Settings", _fake_settings)
    tid = del_setup["tid"]
    token = _make_jwt(tid, del_setup["auth_id"], roles=[del_setup["rol"]])

    del_resp = await del_client.delete(
        f"/api/v1/encuentros/instancias/{uuid.uuid4()}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert del_resp.status_code == 404, \
        f"Expected 404 for non-existent id, got {del_resp.status_code}"


# ---------------------------------------------------------------------------
# TRIANGULATE: DELETE sin permiso → 403
# ---------------------------------------------------------------------------

@pytest.mark.asyncio(loop_scope="session")
async def test_delete_instancia_sin_permiso_returns_403(
    del_client, del_setup, db_session, monkeypatch
):
    """
    TRIANGULATE: DELETE sin permiso encuentros:gestionar → 403.
    """
    monkeypatch.setattr("app.core.config.Settings", _fake_settings)
    tid = del_setup["tid"]
    mat_id = del_setup["mat_id"]
    token_con_perm = _make_jwt(tid, del_setup["auth_id"], roles=[del_setup["rol"]])

    # Create instance to try to delete
    slot_resp = await del_client.post(
        "/api/v1/encuentros/slots",
        json={
            "materia_id": str(mat_id),
            "titulo": "Para perm test",
            "hora": "12:00:00",
            "fecha_unica": "2026-12-22",
        },
        headers={"Authorization": f"Bearer {token_con_perm}"},
    )
    assert slot_resp.status_code == 201
    instancia_id = slot_resp.json()["instancias"][0]["id"]
    slot_id = slot_resp.json()["slot"]["id"]

    # DELETE sin permiso
    token_sin_perm = _make_jwt(tid, del_setup["auth_id"], roles=["SIN_PERMISO"])
    del_resp = await del_client.delete(
        f"/api/v1/encuentros/instancias/{instancia_id}",
        headers={"Authorization": f"Bearer {token_sin_perm}"},
    )
    assert del_resp.status_code == 403, \
        f"Expected 403 without permission, got {del_resp.status_code}"

    # Cleanup
    slot_repo = SlotEncuentroRepository(session=db_session, tenant_id=tid)
    inst_repo = InstanciaEncuentroRepository(session=db_session, tenant_id=tid)
    slot = await slot_repo.get_by_id(uuid.UUID(slot_id))
    if slot:
        await slot_repo.delete(slot)
    insts = await inst_repo.list_by_slot(uuid.UUID(slot_id))
    for i in insts:
        await inst_repo.delete(i)
    await db_session.commit()
