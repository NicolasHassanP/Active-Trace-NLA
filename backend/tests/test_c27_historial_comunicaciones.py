"""
TDD tests for C-27: historial de comunicaciones propias del remitente.

Tasks covered:
    2.1 — RED: list_by_sender retorna solo comunicaciones del sender en el tenant
    2.3 — TRIANGULATE: filtro por estado
    2.4 — TRIANGULATE: paginación retorna total correcto y items con tamaño limit
    3.1 — RED: MisEnviosResponse valida Pydantic con extra='forbid'
    4.1 — RED: GET /comunicaciones/mis-envios → 200 MisEnviosResponse
    4.3 — TRIANGULATE: usuario sin permiso → 403
    4.4 — TRIANGULATE: filtro por estado retorna solo esas comunicaciones
    4.5 — TRIANGULATE: usuario sin envíos propios → total=0, items=[]

Design decisions tested:
    D1 — GET con query params (no POST).
    D2 — list_by_sender en el repositorio.
    D3 — identidad del remitente SIEMPRE de resolve_domain_user_id(), no de query params.
    D4 — MisEnviosResponse con metadata de paginación.
    D6 — Permiso reutilizado: comunicacion:enviar.

Uses real DB, no mocks.
"""
import datetime
import uuid
from typing import Optional

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text, delete

from app.models.auth import AuthIdentity
from app.models.comunicacion import Comunicacion, ComunicacionEstado
from app.models.rbac import Permiso, PermisoScope, Rol, RolPermiso
from app.models.tenant import Tenant, TenantEstado
from app.models.usuario import Usuario, UsuarioEstado
from app.repositories.comunicacion_repository import ComunicacionRepository
from app.schemas.comunicacion import MisEnviosResponse
from app.core.database import build_session_factory

TEST_SECRET_KEY = "supersecretkeyfortesting1234567890"
TEST_ENCRYPTION_KEY = "E" * 32


# ---------------------------------------------------------------------------
# JWT helper
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------

async def _make_tenant(session, name_prefix: str = "TenantC27") -> Tenant:
    from app.core.security.passwords import email_lookup_hash
    t = Tenant(
        nombre=f"{name_prefix}-{uuid.uuid4().hex[:6]}",
        estado=TenantEstado.ACTIVO,
    )
    session.add(t)
    await session.commit()
    await session.refresh(t)
    return t


async def _make_usuario(session, tenant_id: uuid.UUID) -> Usuario:
    from app.core.security.passwords import email_lookup_hash
    email = f"user{uuid.uuid4().hex[:4]}@c27test.edu"
    u = Usuario(
        tenant_id=tenant_id,
        email_encrypted=email,
        email_hash=email_lookup_hash(email),
        nombre="C27",
        apellidos="Test",
        estado=UsuarioEstado.activo,
    )
    session.add(u)
    await session.commit()
    await session.refresh(u)
    return u


async def _encolar_directo(
    session,
    tenant_id: uuid.UUID,
    enviado_por: Optional[uuid.UUID],
    estado: ComunicacionEstado = ComunicacionEstado.Pendiente,
    n: int = 1,
) -> list:
    """Crea registros de Comunicacion directamente en DB para tests de repositorio."""
    created = []
    lote_id = uuid.uuid4()
    for i in range(n):
        com = Comunicacion(
            tenant_id=tenant_id,
            destinatario=f"dest{i}@c27test.edu",
            asunto=f"Asunto-{i}",
            cuerpo="Cuerpo de prueba",
            estado=estado,
            lote_id=lote_id,
            enviado_por=enviado_por,
        )
        session.add(com)
        created.append(com)
    await session.commit()
    for com in created:
        await session.refresh(com)
    return created


async def _setup_permiso_enviar(session, tenant_id: uuid.UUID, rol_nombre: str = "PROFESOR") -> tuple:
    """Crea Rol + Permiso comunicacion:enviar + RolPermiso para el tenant."""
    permiso = Permiso(
        tenant_id=tenant_id,
        codigo="comunicacion:enviar",
        modulo="comunicacion",
        accion="enviar",
    )
    session.add(permiso)
    await session.commit()
    await session.refresh(permiso)

    rol = Rol(tenant_id=tenant_id, nombre=f"{rol_nombre}-{uuid.uuid4().hex[:4]}")
    session.add(rol)
    await session.commit()
    await session.refresh(rol)

    rp = RolPermiso(
        tenant_id=tenant_id,
        rol_id=rol.id,
        permiso_id=permiso.id,
        scope=PermisoScope.propio,
    )
    session.add(rp)
    await session.commit()
    return rol, permiso


async def _cleanup(session, tenant_id: uuid.UUID) -> None:
    await session.execute(delete(RolPermiso).where(RolPermiso.tenant_id == tenant_id))
    await session.execute(delete(Permiso).where(Permiso.tenant_id == tenant_id))
    await session.execute(delete(Rol).where(Rol.tenant_id == tenant_id))
    await session.execute(text("DELETE FROM audit_event WHERE tenant_id = :tid"), {"tid": str(tenant_id)})
    await session.execute(text("DELETE FROM comunicacion WHERE tenant_id = :tid"), {"tid": str(tenant_id)})
    await session.execute(text("DELETE FROM usuario WHERE tenant_id = :tid"), {"tid": str(tenant_id)})
    await session.execute(text("DELETE FROM tenants WHERE id = :id"), {"id": str(tenant_id)})
    await session.commit()


# ===========================================================================
# Fixtures para integration tests (router)
# ===========================================================================

@pytest_asyncio.fixture(scope="module")
async def c27_data(test_engine, create_tables):
    """Crea tenant + sender + RBAC mínimo para tests de integración C-27."""
    import app.core.config as config_mod
    _original_settings = config_mod.Settings

    class PatchedSettings:
        SECRET_KEY = TEST_SECRET_KEY
        ENCRYPTION_KEY = TEST_ENCRYPTION_KEY
        DATABASE_URL = "postgresql+asyncpg://postgres@localhost:5432/activia_trace_test"
        MOODLE_BASE_URL = None
        ACCESS_TOKEN_EXPIRE_MINUTES = 30
        MFA_TOKEN_EXPIRE_MINUTES = 10
        REFRESH_TOKEN_EXPIRE_DAYS = 7
        RECOVERY_TOKEN_EXPIRE_MINUTES = 30
        LOGIN_RATE_LIMIT = "10/minute"
        PADRON_MAX_ROWS = 5000
        UMBRAL_PCT_DEFECTO = 60
        VALORES_APROBATORIOS_DEFECTO = ["Satisfactorio", "Supera lo esperado"]
        NOTA_MAXIMA_DEFECTO = 10.0
        MOODLE_TOKEN = None
        MOODLE_SYNC_HOUR = 3

    config_mod.Settings = PatchedSettings

    from app.core.security.passwords import email_lookup_hash

    factory = build_session_factory(test_engine)
    session = factory()

    tid = uuid.uuid4()
    session.add(Tenant(id=tid, nombre=f"C27-{tid}", estado=TenantEstado.ACTIVO))
    await session.flush()

    # Rol con permiso comunicacion:enviar
    rol_sender = Rol(tenant_id=tid, nombre=f"ROL_SENDER_{tid}")
    rol_sin = Rol(tenant_id=tid, nombre=f"ROL_SIN_{tid}")
    session.add_all([rol_sender, rol_sin])
    await session.flush()

    perm = Permiso(
        tenant_id=tid,
        codigo="comunicacion:enviar",
        modulo="comunicacion",
        accion="enviar",
    )
    session.add(perm)
    await session.flush()

    session.add(RolPermiso(
        tenant_id=tid, rol_id=rol_sender.id, permiso_id=perm.id, scope=PermisoScope.propio,
    ))
    await session.flush()

    # Usuarios: sender (con permiso), sin_permiso, other_sender
    # Para que resolve_domain_user_id funcione necesitamos:
    #   1. AuthIdentity con email
    #   2. Usuario con auth_identity_id = auth_identity.id
    #   3. JWT sub = auth_identity.id

    uid_other = uuid.uuid4()

    # sender con permiso
    email_sender = f"sender_{tid}@c27.edu"
    auth_sender = AuthIdentity(
        tenant_id=tid,
        email_encrypted=email_sender,
        email_hash=email_lookup_hash(email_sender),
        password_hash="dummy_argon2_hash",
        roles=[rol_sender.nombre],
    )
    session.add(auth_sender)
    await session.flush()

    usuario_sender = Usuario(
        tenant_id=tid,
        email_encrypted=email_sender,
        email_hash=email_lookup_hash(email_sender),
        nombre="Sender", apellidos="C27", estado=UsuarioEstado.activo,
        auth_identity_id=auth_sender.id,
    )
    session.add(usuario_sender)
    await session.flush()

    # sin_permiso (no AuthIdentity needed — solo necesitamos el JWT sub)
    email_sin = f"sin_{tid}@c27.edu"
    auth_sin = AuthIdentity(
        tenant_id=tid,
        email_encrypted=email_sin,
        email_hash=email_lookup_hash(email_sin),
        password_hash="dummy_argon2_hash",
        roles=[rol_sin.nombre],
    )
    session.add(auth_sin)
    await session.flush()

    usuario_sin = Usuario(
        tenant_id=tid,
        email_encrypted=email_sin,
        email_hash=email_lookup_hash(email_sin),
        nombre="SinPerm", apellidos="C27", estado=UsuarioEstado.activo,
        auth_identity_id=auth_sin.id,
    )
    session.add(usuario_sin)
    await session.flush()

    # other_sender
    session.add(Usuario(
        id=uid_other, tenant_id=tid,
        email_encrypted=f"other_{tid}@c27.edu",
        email_hash=email_lookup_hash(f"other_{tid}@c27.edu"),
        nombre="Other", apellidos="C27", estado=UsuarioEstado.activo,
    ))
    await session.commit()
    await session.refresh(usuario_sender)
    await session.refresh(usuario_sin)
    await session.refresh(auth_sender)
    await session.refresh(auth_sin)

    yield {
        "tid": tid,
        # Para JWT: usar auth_identity_id como sub
        "auth_sender_id": auth_sender.id,   # sub del JWT del sender
        "auth_sin_id": auth_sin.id,          # sub del JWT del usuario sin permisos
        # Para FK de comunicacion.enviado_por: usar usuario.id
        "uid_sender": usuario_sender.id,
        "uid_sin": usuario_sin.id,
        "uid_other": uid_other,
        "rol_sender": rol_sender.nombre,
        "rol_sin": rol_sin.nombre,
    }

    # Cleanup
    await session.execute(delete(RolPermiso).where(RolPermiso.tenant_id == tid))
    await session.execute(delete(Permiso).where(Permiso.tenant_id == tid))
    await session.execute(delete(Rol).where(Rol.tenant_id == tid))
    await session.execute(text("DELETE FROM audit_event WHERE tenant_id = :tid"), {"tid": str(tid)})
    await session.execute(text("DELETE FROM comunicacion WHERE tenant_id = :tid"), {"tid": str(tid)})
    await session.execute(delete(Usuario).where(Usuario.tenant_id == tid))
    await session.execute(delete(AuthIdentity).where(AuthIdentity.tenant_id == tid))
    await session.execute(text("DELETE FROM tenants WHERE id = :id"), {"id": str(tid)})
    await session.commit()
    await session.close()

    config_mod.Settings = _original_settings


@pytest_asyncio.fixture(scope="module")
def c27_app(test_engine, c27_data):
    import app.core.config as config_mod
    _original = config_mod.Settings

    class PatchedSettings:
        SECRET_KEY = TEST_SECRET_KEY
        ENCRYPTION_KEY = TEST_ENCRYPTION_KEY
        DATABASE_URL = "postgresql+asyncpg://postgres@localhost:5432/activia_trace_test"
        MOODLE_BASE_URL = None
        ACCESS_TOKEN_EXPIRE_MINUTES = 30
        MFA_TOKEN_EXPIRE_MINUTES = 10
        REFRESH_TOKEN_EXPIRE_DAYS = 7
        RECOVERY_TOKEN_EXPIRE_MINUTES = 30
        LOGIN_RATE_LIMIT = "10/minute"
        PADRON_MAX_ROWS = 5000
        UMBRAL_PCT_DEFECTO = 60
        VALORES_APROBATORIOS_DEFECTO = ["Satisfactorio", "Supera lo esperado"]
        NOTA_MAXIMA_DEFECTO = 10.0
        MOODLE_TOKEN = None
        MOODLE_SYNC_HOUR = 3

    config_mod.Settings = PatchedSettings

    from app.main import create_app
    app = create_app()
    factory = build_session_factory(test_engine)
    app.state.session_factory = factory

    yield app

    config_mod.Settings = _original


@pytest_asyncio.fixture(scope="module")
async def c27_client(c27_app) -> AsyncClient:
    async with AsyncClient(
        transport=ASGITransport(app=c27_app), base_url="http://test"
    ) as client:
        yield client


# ===========================================================================
# § 2.1 — RED: list_by_sender retorna solo comunicaciones del sender en el tenant
# ===========================================================================

@pytest.mark.asyncio(loop_scope="function")
async def test_list_by_sender_retorna_solo_del_sender(db_session, create_tables):
    """list_by_sender() retorna solo las comunicaciones del sender en el tenant, no las de otros."""
    tenant = await _make_tenant(db_session)
    sender = await _make_usuario(db_session, tenant.id)
    other = await _make_usuario(db_session, tenant.id)

    try:
        await _encolar_directo(db_session, tenant.id, sender.id, n=3)
        await _encolar_directo(db_session, tenant.id, other.id, n=2)

        repo = ComunicacionRepository(session=db_session, tenant_id=tenant.id)
        items, total = await repo.list_by_sender(sender_id=sender.id, offset=0, limit=50)

        assert total == 3
        assert len(items) == 3
        for item in items:
            assert item.enviado_por == sender.id
            assert item.tenant_id == tenant.id
            assert item.deleted_at is None

    finally:
        await _cleanup(db_session, tenant.id)


@pytest.mark.asyncio(loop_scope="function")
async def test_list_by_sender_excluye_soft_deleted(db_session, create_tables):
    """list_by_sender() excluye comunicaciones con deleted_at IS NOT NULL."""
    import datetime as dt
    tenant = await _make_tenant(db_session)
    sender = await _make_usuario(db_session, tenant.id)

    try:
        coms = await _encolar_directo(db_session, tenant.id, sender.id, n=3)

        # Soft-delete uno
        coms[0].deleted_at = dt.datetime.now(tz=dt.timezone.utc)
        await db_session.commit()

        repo = ComunicacionRepository(session=db_session, tenant_id=tenant.id)
        items, total = await repo.list_by_sender(sender_id=sender.id, offset=0, limit=50)

        assert total == 2
        assert len(items) == 2
        for item in items:
            assert item.deleted_at is None

    finally:
        await _cleanup(db_session, tenant.id)


# ===========================================================================
# § 2.3 — TRIANGULATE: filtro por estado retorna solo comunicaciones con ese estado
# ===========================================================================

@pytest.mark.asyncio(loop_scope="function")
async def test_list_by_sender_filtra_por_estado(db_session, create_tables):
    """list_by_sender() con estado=Enviado retorna solo comunicaciones Enviadas."""
    tenant = await _make_tenant(db_session)
    sender = await _make_usuario(db_session, tenant.id)

    try:
        await _encolar_directo(db_session, tenant.id, sender.id, estado=ComunicacionEstado.Pendiente, n=2)
        await _encolar_directo(db_session, tenant.id, sender.id, estado=ComunicacionEstado.Enviado, n=3)

        repo = ComunicacionRepository(session=db_session, tenant_id=tenant.id)
        items, total = await repo.list_by_sender(
            sender_id=sender.id,
            estado=ComunicacionEstado.Enviado,
            offset=0,
            limit=50,
        )

        assert total == 3
        assert len(items) == 3
        for item in items:
            assert item.estado == ComunicacionEstado.Enviado

    finally:
        await _cleanup(db_session, tenant.id)


# ===========================================================================
# § 2.4 — TRIANGULATE: paginación retorna total correcto y items con tamaño limit
# ===========================================================================

@pytest.mark.asyncio(loop_scope="function")
async def test_list_by_sender_paginacion_retorna_total_correcto(db_session, create_tables):
    """list_by_sender() con offset=0, limit=5 retorna 5 items pero total=15."""
    tenant = await _make_tenant(db_session)
    sender = await _make_usuario(db_session, tenant.id)

    try:
        await _encolar_directo(db_session, tenant.id, sender.id, n=15)

        repo = ComunicacionRepository(session=db_session, tenant_id=tenant.id)
        items, total = await repo.list_by_sender(sender_id=sender.id, offset=0, limit=5)

        assert total == 15
        assert len(items) == 5

    finally:
        await _cleanup(db_session, tenant.id)


@pytest.mark.asyncio(loop_scope="function")
async def test_list_by_sender_paginacion_multiples_paginas(db_session, create_tables):
    """list_by_sender() segunda y tercera página retornan los items correctos."""
    tenant = await _make_tenant(db_session)
    sender = await _make_usuario(db_session, tenant.id)

    try:
        await _encolar_directo(db_session, tenant.id, sender.id, n=12)

        repo = ComunicacionRepository(session=db_session, tenant_id=tenant.id)
        items_p1, total_p1 = await repo.list_by_sender(sender_id=sender.id, offset=0, limit=5)
        items_p2, total_p2 = await repo.list_by_sender(sender_id=sender.id, offset=5, limit=5)
        items_p3, total_p3 = await repo.list_by_sender(sender_id=sender.id, offset=10, limit=5)

        assert total_p1 == total_p2 == total_p3 == 12
        assert len(items_p1) == 5
        assert len(items_p2) == 5
        assert len(items_p3) == 2  # Los últimos 2

    finally:
        await _cleanup(db_session, tenant.id)


# ===========================================================================
# § 3.1 — RED: MisEnviosResponse valida Pydantic con extra='forbid'
# ===========================================================================

def test_mis_envios_response_schema_valida():
    """MisEnviosResponse acepta campos válidos."""
    from datetime import datetime, timezone

    sample_item = {
        "id": str(uuid.uuid4()),
        "tenant_id": str(uuid.uuid4()),
        "estado": "Enviado",
        "lote_id": str(uuid.uuid4()),
        "asunto": "Test asunto",
        "cuerpo": "Test cuerpo",
        "destinatario_email": "dest@test.edu",
        "enviado_at": None,
        "error_detalle": None,
        "enviado_por": None,
        "aprobado_por": None,
        "creado_en": datetime.now(tz=timezone.utc).isoformat(),
        "actualizado_en": datetime.now(tz=timezone.utc).isoformat(),
    }

    response = MisEnviosResponse(
        total=1,
        offset=0,
        limit=20,
        items=[sample_item],
    )
    assert response.total == 1
    assert response.offset == 0
    assert response.limit == 20
    assert len(response.items) == 1


def test_mis_envios_response_rechaza_campos_extra():
    """MisEnviosResponse rechaza campos no declarados (extra='forbid')."""
    import pytest
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        MisEnviosResponse(
            total=0,
            offset=0,
            limit=20,
            items=[],
            campo_extra="no_permitido",  # type: ignore[call-arg]
        )


def test_mis_envios_response_lista_vacia():
    """MisEnviosResponse acepta lista vacía (usuario sin envíos)."""
    response = MisEnviosResponse(total=0, offset=0, limit=20, items=[])
    assert response.total == 0
    assert response.items == []


# ===========================================================================
# § 4.1 — RED: GET /comunicaciones/mis-envios → 200 MisEnviosResponse
# ===========================================================================

@pytest.mark.asyncio(loop_scope="function")
async def test_mis_envios_endpoint_200_con_items(c27_client, c27_data, test_engine, create_tables):
    """GET /comunicaciones/mis-envios responde 200 con MisEnviosResponse para el sender."""
    from app.core.database import build_session_factory

    factory = build_session_factory(test_engine)
    session = factory()

    tid = c27_data["tid"]
    uid_sender = c27_data["uid_sender"]       # usuario.id → FK en comunicacion.enviado_por
    auth_sender_id = c27_data["auth_sender_id"]  # auth_identity.id → sub del JWT
    rol_sender = c27_data["rol_sender"]

    try:
        # Crear comunicaciones del sender (enviado_por = usuario.id del sender)
        lote_id = uuid.uuid4()
        for i in range(3):
            com = Comunicacion(
                tenant_id=tid,
                destinatario=f"dest{i}@c27int.edu",
                asunto=f"Asunto-{i}",
                cuerpo="Cuerpo",
                estado=ComunicacionEstado.Enviado,
                lote_id=lote_id,
                enviado_por=uid_sender,
            )
            session.add(com)
        await session.commit()

        # JWT sub = auth_identity.id (para que resolve_domain_user_id funcione)
        token = _make_jwt(tid, auth_sender_id, [rol_sender])
        response = await c27_client.get(
            "/api/v1/comunicaciones/mis-envios",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert "total" in data
        assert "offset" in data
        assert "limit" in data
        assert "items" in data
        assert data["total"] >= 3
        for item in data["items"]:
            assert item["tenant_id"] == str(tid)

    finally:
        await session.execute(
            text("DELETE FROM comunicacion WHERE tenant_id = :tid AND enviado_por = :uid"),
            {"tid": str(tid), "uid": str(uid_sender)},
        )
        await session.commit()
        await session.close()


# ===========================================================================
# § 4.3 — TRIANGULATE: usuario sin permiso → 403
# ===========================================================================

@pytest.mark.asyncio(loop_scope="function")
async def test_mis_envios_sin_permiso_403(c27_client, c27_data):
    """GET /comunicaciones/mis-envios sin permiso comunicacion:enviar responde 403."""
    tid = c27_data["tid"]
    auth_sin_id = c27_data["auth_sin_id"]  # auth_identity.id del usuario sin permisos
    rol_sin = c27_data["rol_sin"]

    # El role ROL_SIN no tiene permiso comunicacion:enviar → 403
    token = _make_jwt(tid, auth_sin_id, [rol_sin])
    response = await c27_client.get(
        "/api/v1/comunicaciones/mis-envios",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 403


# ===========================================================================
# § 4.4 — TRIANGULATE: filtro por estado retorna solo las comunicaciones en ese estado
# ===========================================================================

@pytest.mark.asyncio(loop_scope="function")
async def test_mis_envios_filtra_por_estado_via_endpoint(c27_client, c27_data, test_engine, create_tables):
    """GET /comunicaciones/mis-envios?estado=Enviado retorna solo comunicaciones Enviadas."""
    from app.core.database import build_session_factory

    factory = build_session_factory(test_engine)
    session = factory()

    tid = c27_data["tid"]
    uid_sender = c27_data["uid_sender"]
    auth_sender_id = c27_data["auth_sender_id"]
    rol_sender = c27_data["rol_sender"]

    try:
        # Crear comunicaciones con distintos estados
        for estado, n in [(ComunicacionEstado.Pendiente, 2), (ComunicacionEstado.Enviado, 3)]:
            lote_id = uuid.uuid4()
            for i in range(n):
                session.add(Comunicacion(
                    tenant_id=tid,
                    destinatario=f"f{i}@c27filter.edu",
                    asunto=f"F-{estado.value}-{i}",
                    cuerpo="Filtro test",
                    estado=estado,
                    lote_id=lote_id,
                    enviado_por=uid_sender,
                ))
        await session.commit()

        token = _make_jwt(tid, auth_sender_id, [rol_sender])
        response = await c27_client.get(
            "/api/v1/comunicaciones/mis-envios?estado=Enviado",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert data["total"] >= 3
        for item in data["items"]:
            assert item["estado"] == "Enviado"

    finally:
        await session.execute(
            text("DELETE FROM comunicacion WHERE tenant_id = :tid AND enviado_por = :uid"),
            {"tid": str(tid), "uid": str(uid_sender)},
        )
        await session.commit()
        await session.close()


# ===========================================================================
# § 4.5 — TRIANGULATE: usuario sin envíos propios → total=0, items=[]
# ===========================================================================

@pytest.mark.asyncio(loop_scope="function")
async def test_mis_envios_sin_envios_propios_lista_vacia(c27_client, c27_data, test_engine, create_tables):
    """GET /comunicaciones/mis-envios para sender sin envíos responde total=0, items=[]."""
    # Este test NO crea comunicaciones del sender — el sender autentica pero no tiene nada.
    # Cualquier comunicación previa de otros tests fue limpiada en finally.
    tid = c27_data["tid"]
    auth_sender_id = c27_data["auth_sender_id"]
    rol_sender = c27_data["rol_sender"]

    # JWT con sender que NO tiene comunicaciones propias
    token = _make_jwt(tid, auth_sender_id, [rol_sender])
    response = await c27_client.get(
        "/api/v1/comunicaciones/mis-envios",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    data = response.json()
    assert data["total"] == 0
    assert data["items"] == []
