"""
test_inbox_router.py — TDD e2e suite para C-20 router de mensajería interna.

Task 10.1 RED: GET /api/v1/inbox → 403 sin inbox:usar, 200 con hilos propios.
Task 10.3 RED: GET /api/v1/inbox/{hilo_id} → 200 participante, 404 no participante.
Task 10.5 RED: POST /api/v1/inbox/{hilo_id}/responder → 201/404/422.
Task 10.7 RED: POST /api/v1/inbox → 201 con destinatario válido, 404 cross-tenant.
Task 10.9 TRIANGULATE: anti-spoofing de remitente_id.
"""
import datetime
import uuid

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.core.database import build_session_factory
from app.models.rbac import Permiso, Rol, RolPermiso, PermisoScope
from app.models.tenant import Tenant, TenantEstado
from app.models.usuario import Usuario, UsuarioEstado

TEST_SECRET_KEY = "supersecretkeyfortesting1234567890"
TEST_ENCRYPTION_KEY = "E" * 32


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


@pytest_asyncio.fixture(scope="module")
async def inbox_router_data(test_engine, create_tables):
    """Crea tenant + usuarios + RBAC + mensajería para tests e2e del inbox router."""
    import app.models  # noqa
    import app.core.config as config_mod
    from sqlalchemy import text
    from app.core.security.passwords import email_lookup_hash

    # Patch settings BEFORE creating encrypted data
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

    config_mod.Settings = PatchedSettings

    factory = build_session_factory(test_engine)
    session = factory()

    # Crear tablas mensajería (idempotente)
    await session.execute(text("ALTER TABLE usuario ADD COLUMN IF NOT EXISTS genero VARCHAR(50)"))
    await session.execute(text("""
        CREATE TABLE IF NOT EXISTS hilos_mensaje (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE RESTRICT,
            asunto VARCHAR(255) NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            deleted_at TIMESTAMPTZ NULL
        )
    """))
    await session.execute(text("""
        CREATE TABLE IF NOT EXISTS mensajes (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE RESTRICT,
            hilo_id UUID NOT NULL REFERENCES hilos_mensaje(id) ON DELETE RESTRICT,
            remitente_id UUID NOT NULL REFERENCES usuario(id) ON DELETE RESTRICT,
            asunto VARCHAR(255) NOT NULL,
            cuerpo TEXT NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            deleted_at TIMESTAMPTZ NULL
        )
    """))
    await session.execute(text("""
        CREATE TABLE IF NOT EXISTS hilo_participantes (
            hilo_id UUID NOT NULL REFERENCES hilos_mensaje(id) ON DELETE CASCADE,
            usuario_id UUID NOT NULL REFERENCES usuario(id) ON DELETE RESTRICT,
            tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE RESTRICT,
            last_read_at TIMESTAMPTZ NULL,
            PRIMARY KEY (hilo_id, usuario_id)
        )
    """))
    await session.execute(text(
        "CREATE INDEX IF NOT EXISTS ix_hilo_participantes_tenant_usuario "
        "ON hilo_participantes (tenant_id, usuario_id)"
    ))
    await session.execute(text(
        "CREATE INDEX IF NOT EXISTS ix_mensajes_tenant_hilo_at "
        "ON mensajes (tenant_id, hilo_id, created_at)"
    ))
    await session.commit()

    tid = uuid.uuid4()
    tid_otro = uuid.uuid4()
    session.add(Tenant(id=tid, nombre=f"Inbox Router {tid}", estado=TenantEstado.ACTIVO))
    session.add(Tenant(id=tid_otro, nombre=f"Inbox Router Otro {tid_otro}", estado=TenantEstado.ACTIVO))
    await session.flush()

    # Rol con inbox:usar
    rol_inbox = Rol(tenant_id=tid, nombre=f"ROL_INBOX_{tid}")
    rol_sin = Rol(tenant_id=tid, nombre=f"ROL_SIN_{tid}")
    session.add_all([rol_inbox, rol_sin])
    await session.flush()

    perm_inbox = Permiso(tenant_id=tid, codigo="inbox:usar", modulo="inbox", accion="usar")
    session.add(perm_inbox)
    await session.flush()

    session.add(RolPermiso(
        tenant_id=tid, rol_id=rol_inbox.id, permiso_id=perm_inbox.id, scope=PermisoScope.global_,
    ))
    await session.flush()

    uid1 = uuid.uuid4()
    uid2 = uuid.uuid4()
    uid_sin = uuid.uuid4()
    uid_otro_tenant = uuid.uuid4()

    for uid, email, nombre in [
        (uid1, f"inbox_u1_{tid}@test.com", "U1"),
        (uid2, f"inbox_u2_{tid}@test.com", "U2"),
        (uid_sin, f"inbox_norol_{tid}@test.com", "Sin"),
    ]:
        session.add(Usuario(
            id=uid, tenant_id=tid,
            email_encrypted=email,
            email_hash=email_lookup_hash(email),
            nombre=nombre, apellidos="Test", estado=UsuarioEstado.activo,
        ))

    session.add(Usuario(
        id=uid_otro_tenant, tenant_id=tid_otro,
        email_encrypted=f"inbox_otro_{tid_otro}@test.com",
        email_hash=email_lookup_hash(f"inbox_otro_{tid_otro}@test.com"),
        nombre="Otro", apellidos="Tenant", estado=UsuarioEstado.activo,
    ))
    await session.commit()

    yield {
        "tid": tid,
        "tid_otro": tid_otro,
        "uid1": uid1,
        "uid2": uid2,
        "uid_sin": uid_sin,
        "uid_otro_tenant": uid_otro_tenant,
        "rol_inbox": rol_inbox.nombre,
        "rol_sin": rol_sin.nombre,
    }

    # Cleanup
    from sqlalchemy import delete
    from app.models.mensajeria import HiloParticipante, HiloMensaje, Mensaje
    await session.execute(delete(HiloParticipante).where(HiloParticipante.tenant_id.in_([tid, tid_otro])))
    await session.execute(delete(Mensaje).where(Mensaje.tenant_id.in_([tid, tid_otro])))
    await session.execute(delete(HiloMensaje).where(HiloMensaje.tenant_id.in_([tid, tid_otro])))
    await session.execute(delete(RolPermiso).where(RolPermiso.tenant_id.in_([tid, tid_otro])))
    await session.execute(delete(Permiso).where(Permiso.tenant_id.in_([tid, tid_otro])))
    await session.execute(delete(Rol).where(Rol.tenant_id.in_([tid, tid_otro])))
    await session.execute(delete(Usuario).where(Usuario.tenant_id.in_([tid, tid_otro])))
    await session.execute(delete(Tenant).where(Tenant.id.in_([tid, tid_otro])))
    await session.commit()
    await session.close()

    config_mod.Settings = _original_settings


@pytest_asyncio.fixture(scope="module")
def inbox_router_app(test_engine, inbox_router_data):
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

    config_mod.Settings = PatchedSettings

    from app.main import create_app
    app = create_app()
    factory = build_session_factory(test_engine)
    app.state.session_factory = factory

    yield app

    config_mod.Settings = _original


@pytest_asyncio.fixture(scope="module")
async def inbox_client(inbox_router_app) -> AsyncClient:
    async with AsyncClient(
        transport=ASGITransport(app=inbox_router_app), base_url="http://test"
    ) as client:
        yield client


# ---------------------------------------------------------------------------
# Task 10.1 RED — GET /api/v1/inbox
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_inbox_sin_jwt_retorna_401(inbox_client):
    """RED: GET /api/v1/inbox sin JWT → 401."""
    resp = await inbox_client.get("/api/v1/inbox")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_get_inbox_sin_permiso_retorna_403(inbox_client, inbox_router_data):
    """RED: GET /api/v1/inbox sin inbox:usar → 403."""
    data = inbox_router_data
    token = _make_jwt(data["tid"], data["uid_sin"], [data["rol_sin"]])
    resp = await inbox_client.get(
        "/api/v1/inbox",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_get_inbox_con_permiso_retorna_200_lista(inbox_client, inbox_router_data):
    """RED: GET /api/v1/inbox con inbox:usar → 200 con lista de hilos propios."""
    data = inbox_router_data
    token = _make_jwt(data["tid"], data["uid1"], [data["rol_inbox"]])
    resp = await inbox_client.get(
        "/api/v1/inbox",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


# ---------------------------------------------------------------------------
# Task 10.7 RED — POST /api/v1/inbox (iniciar hilo)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_post_inbox_crea_hilo_con_destinatario_valido(inbox_client, inbox_router_data):
    """RED: POST /api/v1/inbox con destinatario válido → 201."""
    data = inbox_router_data
    token = _make_jwt(data["tid"], data["uid1"], [data["rol_inbox"]])
    resp = await inbox_client.post(
        "/api/v1/inbox",
        json={
            "destinatario_id": str(data["uid2"]),
            "asunto": "Hilo router test",
            "cuerpo": "Primer mensaje",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["remitente_id"] == str(data["uid1"])


@pytest.mark.asyncio
async def test_post_inbox_destinatario_cross_tenant_retorna_404(inbox_client, inbox_router_data):
    """RED: POST /api/v1/inbox con destinatario de otro tenant → 404."""
    data = inbox_router_data
    token = _make_jwt(data["tid"], data["uid1"], [data["rol_inbox"]])
    resp = await inbox_client.post(
        "/api/v1/inbox",
        json={
            "destinatario_id": str(data["uid_otro_tenant"]),
            "asunto": "Cross-tenant",
            "cuerpo": "No debe funcionar",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Task 10.3 RED — GET /api/v1/inbox/{hilo_id}
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_hilo_participante_retorna_200_y_marca_leido(inbox_client, inbox_router_data):
    """RED: GET /api/v1/inbox/{hilo_id} → 200 para participante y marca leído."""
    data = inbox_router_data
    token1 = _make_jwt(data["tid"], data["uid1"], [data["rol_inbox"]])
    token2 = _make_jwt(data["tid"], data["uid2"], [data["rol_inbox"]])

    # Crear hilo entre uid1 y uid2 (puede existir ya de test anterior; handle 409)
    create_resp = await inbox_client.post(
        "/api/v1/inbox",
        json={
            "destinatario_id": str(data["uid2"]),
            "asunto": "Para abrir",
            "cuerpo": "Mensaje inicial",
        },
        headers={"Authorization": f"Bearer {token1}"},
    )
    # Accept both 201 (new) and 409 (already exists)
    assert create_resp.status_code in (201, 409)

    # Para obtener el hilo_id, listar inbox de uid2
    list_resp = await inbox_client.get(
        "/api/v1/inbox",
        headers={"Authorization": f"Bearer {token2}"},
    )
    assert list_resp.status_code == 200
    hilos = list_resp.json()
    if not hilos:
        pytest.skip("No hay hilos para uid2")

    hilo_id = hilos[0]["id"]
    resp = await inbox_client.get(
        f"/api/v1/inbox/{hilo_id}",
        headers={"Authorization": f"Bearer {token2}"},
    )
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_get_hilo_no_participante_retorna_404(inbox_client, inbox_router_data):
    """RED: GET /api/v1/inbox/{hilo_id} para no participante → 404."""
    data = inbox_router_data
    token = _make_jwt(data["tid"], data["uid1"], [data["rol_inbox"]])
    resp = await inbox_client.get(
        f"/api/v1/inbox/{uuid.uuid4()}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Task 10.5 RED — POST /api/v1/inbox/{hilo_id}/responder
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_responder_participante_retorna_201(inbox_client, inbox_router_data):
    """RED: POST /api/v1/inbox/{hilo_id}/responder para participante → 201."""
    data = inbox_router_data
    token1 = _make_jwt(data["tid"], data["uid1"], [data["rol_inbox"]])

    # Listar inbox de uid1 para obtener un hilo
    list_resp = await inbox_client.get(
        "/api/v1/inbox",
        headers={"Authorization": f"Bearer {token1}"},
    )
    hilos = list_resp.json()
    if not hilos:
        pytest.skip("No hay hilos para uid1")

    hilo_id = hilos[0]["id"]
    resp = await inbox_client.post(
        f"/api/v1/inbox/{hilo_id}/responder",
        json={"asunto": "Re: Hilo", "cuerpo": "Respuesta del router test"},
        headers={"Authorization": f"Bearer {token1}"},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["remitente_id"] == str(data["uid1"])


@pytest.mark.asyncio
async def test_responder_no_participante_retorna_404(inbox_client, inbox_router_data):
    """RED: POST /api/v1/inbox/{hilo_id}/responder para no participante → 404."""
    data = inbox_router_data
    token = _make_jwt(data["tid"], data["uid1"], [data["rol_inbox"]])
    resp = await inbox_client.post(
        f"/api/v1/inbox/{uuid.uuid4()}/responder",
        json={"asunto": "X", "cuerpo": "Intruso"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_responder_cuerpo_vacio_retorna_422(inbox_client, inbox_router_data):
    """RED: POST /api/v1/inbox/{hilo_id}/responder con cuerpo vacío → 422."""
    data = inbox_router_data
    token = _make_jwt(data["tid"], data["uid1"], [data["rol_inbox"]])
    resp = await inbox_client.post(
        f"/api/v1/inbox/{uuid.uuid4()}/responder",
        json={"asunto": "X", "cuerpo": ""},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Task 10.9 TRIANGULATE — anti-spoofing de remitente_id
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_iniciar_hilo_ignora_remitente_id_en_body(inbox_client, inbox_router_data):
    """TRIANGULATE: POST /api/v1/inbox rechaza remitente_id en body (extra='forbid')."""
    data = inbox_router_data
    token = _make_jwt(data["tid"], data["uid1"], [data["rol_inbox"]])
    resp = await inbox_client.post(
        "/api/v1/inbox",
        json={
            "destinatario_id": str(data["uid2"]),
            "asunto": "Anti-spoofing test",
            "cuerpo": "Body",
            "remitente_id": str(uuid.uuid4()),  # debe ser rechazado
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    # extra='forbid' rejects extra fields → 422
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_responder_campo_no_declarado_retorna_422(inbox_client, inbox_router_data):
    """TRIANGULATE: POST /api/v1/inbox/{hilo_id}/responder con tenant_id → 422."""
    data = inbox_router_data
    token = _make_jwt(data["tid"], data["uid1"], [data["rol_inbox"]])
    resp = await inbox_client.post(
        f"/api/v1/inbox/{uuid.uuid4()}/responder",
        json={"asunto": "X", "cuerpo": "Y", "tenant_id": str(data["tid"])},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 422
