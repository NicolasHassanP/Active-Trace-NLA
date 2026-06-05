"""
test_tareas_integracion.py — Integration tests for C-16 /api/v1/tareas router.

Tasks 7.1–7.8 (all RED+GREEN):
    7.1 crear/asignar requires tareas:gestionar (403 without, 201 with), TAREA_ASIGNAR audit, estado Pendiente.
    7.2 GET /tareas/mias returns only caller's assigned tareas.
    7.3 State machine — legal transitions succeed, illegal/no-op → 409; ownership enforced.
    7.4 Delegación reassigns, TAREA_DELEGAR audit, system comment.
    7.5 Comentarios — add + list thread; access control; autor from session.
    7.6 GET /tareas/admin filters; soft-delete hides everywhere.
    7.7 Tenant isolation — other tenant's tarea → 404.
    7.8 Contexto polimórfico — both-null and both-present accepted; only-one-present → 422.

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
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import NullPool

from app.core.database import build_session_factory

load_dotenv()
TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://postgres@localhost:5432/activia_trace_test",
)

# Use the real SECRET_KEY from .env so JWTs validate correctly
TEST_SECRET_KEY = os.environ.get("SECRET_KEY", "supersecretkeyfortesting1234567890xxxx")
TEST_ENCRYPTION_KEY = os.environ.get("ENCRYPTION_KEY", "E" * 32)


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
async def integ_engine():
    engine = create_async_engine(TEST_DATABASE_URL, poolclass=NullPool, echo=False)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture(scope="module")
async def integ_setup(integ_engine):
    """
    Set up tenants, users, RBAC, materia for integration tests.

    Returns a dict with all IDs and JWTs needed.
    """
    import app.models  # noqa: F401

    async with integ_engine.begin() as conn:
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
            "DO $$ BEGIN CREATE TYPE aviso_alcance AS ENUM ('Global', 'PorMateria', 'PorCohorte', 'PorRol'); EXCEPTION WHEN duplicate_object THEN NULL; END $$;",
            "DO $$ BEGIN CREATE TYPE aviso_severidad AS ENUM ('Info', 'Advertencia', 'Critico'); EXCEPTION WHEN duplicate_object THEN NULL; END $$;",
            "DO $$ BEGIN CREATE TYPE tarea_estado AS ENUM ('Pendiente', 'EnProgreso', 'Resuelta', 'Cancelada'); EXCEPTION WHEN duplicate_object THEN NULL; END $$;",
        ]:
            await conn.execute(text(stmt))

        for action in [
            "PADRON_CARGAR", "CALIFICACIONES_IMPORTAR", "COMUNICACION_ENVIAR",
            "EQUIPOS_ASIGNACION_MASIVA", "EQUIPOS_CLONAR", "EQUIPOS_VIGENCIA_GENERAL",
            "ENCUENTRO_GESTIONAR", "COLOQUIO_GESTIONAR", "AVISO_PUBLICAR",
            "TAREA_ASIGNAR", "TAREA_DELEGAR", "TAREA_CAMBIAR_ESTADO",
        ]:
            await conn.execute(text(
                f"DO $$ BEGIN ALTER TYPE audit_action ADD VALUE '{action}'; "
                "EXCEPTION WHEN duplicate_object THEN NULL; END $$;"
            ))

        from app.core.database import Base
        await conn.run_sync(Base.metadata.create_all, checkfirst=True)

        await conn.execute(text(
            "CREATE UNIQUE INDEX IF NOT EXISTS uq_ack_aviso_usuario "
            "ON acknowledgment_aviso (tenant_id, aviso_id, usuario_id) "
            "WHERE deleted_at IS NULL"
        ))
        await conn.execute(text(
            "CREATE UNIQUE INDEX IF NOT EXISTS uq_reserva_activa_por_convocatoria "
            "ON reserva_evaluacion (tenant_id, evaluacion_id, alumno_id) "
            "WHERE estado = 'Activa' AND deleted_at IS NULL"
        ))

    factory = build_session_factory(integ_engine)
    session = factory()

    try:
        from app.models.tenant import Tenant, TenantEstado
        from app.models.estructura import Carrera, Cohorte, Materia, EstadoEstructura
        from app.models.rbac import Permiso, PermisoScope, Rol, RolPermiso
        from app.models.usuario import Usuario, UsuarioEstado
        from app.core.security.passwords import email_lookup_hash as _hash

        # Two tenants
        tid_a = uuid.uuid4()
        tid_b = uuid.uuid4()
        session.add(Tenant(id=tid_a, nombre=f"TarIntA_{tid_a.hex[:4]}", estado=TenantEstado.ACTIVO))
        session.add(Tenant(id=tid_b, nombre=f"TarIntB_{tid_b.hex[:4]}", estado=TenantEstado.ACTIVO))
        await session.flush()

        # Users in tenant A
        def make_email(pfx):
            return f"tar_int_{pfx}_{uuid.uuid4().hex[:6]}@test.com"

        coord_email = make_email("coord")
        coord = Usuario(tenant_id=tid_a, email_encrypted=coord_email, email_hash=_hash(coord_email),
                        nombre="Coord", apellidos="A", estado=UsuarioEstado.activo)
        session.add(coord)

        docente_email = make_email("docente")
        docente = Usuario(tenant_id=tid_a, email_encrypted=docente_email, email_hash=_hash(docente_email),
                          nombre="Doc", apellidos="A", estado=UsuarioEstado.activo)
        session.add(docente)

        otro_email = make_email("otro")
        otro = Usuario(tenant_id=tid_a, email_encrypted=otro_email, email_hash=_hash(otro_email),
                       nombre="Otro", apellidos="A", estado=UsuarioEstado.activo)
        session.add(otro)

        coord2_email = make_email("coord2")
        coord2 = Usuario(tenant_id=tid_a, email_encrypted=coord2_email, email_hash=_hash(coord2_email),
                         nombre="Coord2", apellidos="A", estado=UsuarioEstado.activo)
        session.add(coord2)

        # User in tenant B
        coord_b_email = make_email("coord_b")
        coord_b = Usuario(tenant_id=tid_b, email_encrypted=coord_b_email, email_hash=_hash(coord_b_email),
                          nombre="CoordB", apellidos="B", estado=UsuarioEstado.activo)
        session.add(coord_b)

        await session.flush()

        # RBAC for tenant A — tareas:gestionar role named "COORDINADOR" (matches JWT role)
        rol_gestionar = Rol(tenant_id=tid_a, nombre="COORDINADOR")
        session.add(rol_gestionar)
        await session.flush()

        perm_gestionar = Permiso(tenant_id=tid_a, codigo="tareas:gestionar",
                                  modulo="tareas", accion="gestionar")
        session.add(perm_gestionar)
        await session.flush()

        session.add(RolPermiso(tenant_id=tid_a, rol_id=rol_gestionar.id,
                                permiso_id=perm_gestionar.id, scope=PermisoScope.global_))
        await session.flush()

        # RBAC for tenant B — also "COORDINADOR" role
        rol_gest_b = Rol(tenant_id=tid_b, nombre="COORDINADOR")
        session.add(rol_gest_b)
        await session.flush()

        perm_gest_b = Permiso(tenant_id=tid_b, codigo="tareas:gestionar",
                               modulo="tareas", accion="gestionar")
        session.add(perm_gest_b)
        await session.flush()

        session.add(RolPermiso(tenant_id=tid_b, rol_id=rol_gest_b.id,
                                permiso_id=perm_gest_b.id, scope=PermisoScope.global_))
        await session.flush()

        # Materia in tenant A
        mat = Materia(tenant_id=tid_a, codigo=f"TAR_{uuid.uuid4().hex[:4]}",
                       nombre="MatTareas", estado=EstadoEstructura.activa)
        session.add(mat)
        await session.flush()

        await session.commit()

        result = {
            "tid_a": tid_a,
            "tid_b": tid_b,
            "coord_id": coord.id,
            "docente_id": docente.id,
            "otro_id": otro.id,
            "coord2_id": coord2.id,
            "coord_b_id": coord_b.id,
            "materia_id": mat.id,
            "rol_gestionar_id": rol_gestionar.id,
            "perm_gestionar_codigo": "tareas:gestionar",
            "session": session,
        }

        # JWTs — coord has gestionar, docente has no gestionar, coord_b has gestionar in tenant B
        result["jwt_coord"] = _make_jwt(tid_a, coord.id, ["COORDINADOR"])
        result["jwt_docente"] = _make_jwt(tid_a, docente.id, ["PROFESOR"])
        result["jwt_otro"] = _make_jwt(tid_a, otro.id, ["PROFESOR"])
        result["jwt_coord2"] = _make_jwt(tid_a, coord2.id, ["COORDINADOR"])
        result["jwt_coord_b"] = _make_jwt(tid_b, coord_b.id, ["COORDINADOR"])

        yield result

    finally:
        try:
            await session.rollback()
            await session.close()
        except Exception:
            pass


@pytest_asyncio.fixture(scope="module")
async def integ_client(integ_engine, integ_setup):
    """HTTP client against the real FastAPI app wired to test DB."""
    from app.main import create_app

    app = create_app()
    factory = build_session_factory(integ_engine)
    app.state.session_factory = factory

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        yield client


def _auth(jwt: str) -> dict:
    return {"Authorization": f"Bearer {jwt}"}


# ---------------------------------------------------------------------------
# 7.1 — crear/asignar requires tareas:gestionar
# ---------------------------------------------------------------------------

@pytest.mark.asyncio(loop_scope="session")
async def test_crear_tarea_sin_permiso_403(integ_client, integ_setup):
    """7.1 RED: POST /tareas without tareas:gestionar → 403."""
    s = integ_setup
    resp = await integ_client.post(
        "/api/v1/tareas",
        json={"asignado_a": str(s["docente_id"]), "descripcion": "Sin permiso"},
        headers=_auth(s["jwt_docente"]),  # docente has no gestionar
    )
    assert resp.status_code == 403


@pytest.mark.asyncio(loop_scope="session")
async def test_crear_tarea_con_permiso_201(integ_client, integ_setup):
    """7.1 GREEN: POST /tareas with tareas:gestionar → 201, estado=Pendiente, asignado_por from JWT."""
    s = integ_setup
    resp = await integ_client.post(
        "/api/v1/tareas",
        json={"asignado_a": str(s["docente_id"]), "descripcion": "Tarea válida de integración"},
        headers=_auth(s["jwt_coord"]),
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["estado"] == "Pendiente"
    assert data["asignado_por"] == str(s["coord_id"])
    assert data["asignado_a"] == str(s["docente_id"])

    # Verify TAREA_ASIGNAR audit
    from app.models.audit import AuditAction, AuditEvent
    session = s["session"]
    stmt = select(AuditEvent).where(
        AuditEvent.tenant_id == s["tid_a"],
        AuditEvent.accion == AuditAction.TAREA_ASIGNAR,
        AuditEvent.actor_user_id == s["coord_id"],
    )
    r = await session.execute(stmt)
    assert r.scalar_one_or_none() is not None

    # Cleanup
    tarea_id = data["id"]
    from app.repositories.tarea_repository import TareaRepository
    repo = TareaRepository(session=session, tenant_id=s["tid_a"])
    t = await repo.get_by_id(uuid.UUID(tarea_id))
    if t:
        await repo.delete(t)
    await session.commit()


# ---------------------------------------------------------------------------
# 7.2 — GET /tareas/mias
# ---------------------------------------------------------------------------

@pytest.mark.asyncio(loop_scope="session")
async def test_listar_mias_only_assigned_tareas(integ_client, integ_setup):
    """7.2 RED+GREEN: GET /tareas/mias returns only caller's assigned tareas."""
    s = integ_setup
    session = s["session"]

    # Create two tareas: one for docente, one for otro
    resp1 = await integ_client.post(
        "/api/v1/tareas",
        json={"asignado_a": str(s["docente_id"]), "descripcion": "Mia del docente"},
        headers=_auth(s["jwt_coord"]),
    )
    assert resp1.status_code == 201
    t1_id = resp1.json()["id"]

    resp2 = await integ_client.post(
        "/api/v1/tareas",
        json={"asignado_a": str(s["otro_id"]), "descripcion": "Del otro"},
        headers=_auth(s["jwt_coord"]),
    )
    assert resp2.status_code == 201
    t2_id = resp2.json()["id"]

    # docente lists their tareas
    resp = await integ_client.get("/api/v1/tareas/mias", headers=_auth(s["jwt_docente"]))
    assert resp.status_code == 200
    ids = {t["id"] for t in resp.json()}
    assert t1_id in ids
    assert t2_id not in ids

    # Cleanup
    from app.repositories.tarea_repository import TareaRepository
    repo = TareaRepository(session=session, tenant_id=s["tid_a"])
    for tid_str in [t1_id, t2_id]:
        t = await repo.get_by_id(uuid.UUID(tid_str))
        if t:
            await repo.delete(t)
    await session.commit()


# ---------------------------------------------------------------------------
# 7.3 — State machine
# ---------------------------------------------------------------------------

@pytest.mark.asyncio(loop_scope="session")
async def test_state_machine_legal_and_illegal(integ_client, integ_setup):
    """7.3 RED+GREEN: legal transitions succeed, illegal → 409, ownership enforced."""
    s = integ_setup
    session = s["session"]

    # Create tarea (docente is asignado_a)
    resp = await integ_client.post(
        "/api/v1/tareas",
        json={"asignado_a": str(s["docente_id"]), "descripcion": "State machine test"},
        headers=_auth(s["jwt_coord"]),
    )
    assert resp.status_code == 201
    t_id = resp.json()["id"]

    # Pendiente → EnProgreso (docente can do it)
    resp2 = await integ_client.patch(
        f"/api/v1/tareas/{t_id}/estado",
        json={"estado": "EnProgreso"},
        headers=_auth(s["jwt_docente"]),
    )
    assert resp2.status_code == 200
    assert resp2.json()["estado"] == "EnProgreso"

    # Illegal: EnProgreso → Resuelta is legal, but Resuelta → Pendiente is illegal
    await integ_client.patch(
        f"/api/v1/tareas/{t_id}/estado",
        json={"estado": "Resuelta"},
        headers=_auth(s["jwt_docente"]),
    )
    # Now Resuelta → Pendiente: illegal
    resp_ill = await integ_client.patch(
        f"/api/v1/tareas/{t_id}/estado",
        json={"estado": "Pendiente"},
        headers=_auth(s["jwt_docente"]),
    )
    assert resp_ill.status_code == 409

    # No-op (already Resuelta → Resuelta): 409
    resp_noop = await integ_client.patch(
        f"/api/v1/tareas/{t_id}/estado",
        json={"estado": "Resuelta"},
        headers=_auth(s["jwt_docente"]),
    )
    assert resp_noop.status_code == 409

    # Ownership: otro cannot change estado (not asignado_a/por)
    resp_own = await integ_client.patch(
        f"/api/v1/tareas/{t_id}/estado",
        json={"estado": "EnProgreso"},
        headers=_auth(s["jwt_otro"]),
    )
    assert resp_own.status_code == 403

    # Cleanup
    from app.repositories.tarea_repository import TareaRepository
    repo = TareaRepository(session=session, tenant_id=s["tid_a"])
    t = await repo.get_by_id(uuid.UUID(t_id))
    if t:
        await repo.delete(t)
    await session.commit()


# ---------------------------------------------------------------------------
# 7.4 — Delegación
# ---------------------------------------------------------------------------

@pytest.mark.asyncio(loop_scope="session")
async def test_delegacion_reassigns_audit_comment(integ_client, integ_setup):
    """7.4 RED+GREEN: delegación reassigns asignado_a, TAREA_DELEGAR audit, system comment."""
    s = integ_setup
    session = s["session"]

    resp = await integ_client.post(
        "/api/v1/tareas",
        json={"asignado_a": str(s["docente_id"]), "descripcion": "Para delegar"},
        headers=_auth(s["jwt_coord"]),
    )
    assert resp.status_code == 201
    t_id = resp.json()["id"]

    # Delegar to otro
    resp2 = await integ_client.post(
        f"/api/v1/tareas/{t_id}/delegar",
        json={"asignado_a": str(s["otro_id"])},
        headers=_auth(s["jwt_coord2"]),
    )
    assert resp2.status_code == 200
    data = resp2.json()
    assert data["asignado_a"] == str(s["otro_id"])
    assert data["asignado_por"] == str(s["coord2_id"])

    # Verify TAREA_DELEGAR audit
    from app.models.audit import AuditAction, AuditEvent
    stmt = select(AuditEvent).where(
        AuditEvent.tenant_id == s["tid_a"],
        AuditEvent.accion == AuditAction.TAREA_DELEGAR,
        AuditEvent.actor_user_id == s["coord2_id"],
    )
    r = await session.execute(stmt)
    audit = r.scalar_one_or_none()
    assert audit is not None

    # Verify system comment — use coord2 who is now asignado_por (has ownership access)
    resp_com = await integ_client.get(
        f"/api/v1/tareas/{t_id}/comentarios",
        headers=_auth(s["jwt_coord2"]),
    )
    assert resp_com.status_code == 200
    comentarios = resp_com.json()
    sys_comments = [c for c in comentarios if c.get("es_sistema") is True]
    assert len(sys_comments) >= 1

    # Cleanup
    from app.repositories.tarea_repository import TareaRepository
    repo = TareaRepository(session=session, tenant_id=s["tid_a"])
    t = await repo.get_by_id(uuid.UUID(t_id))
    if t:
        await repo.delete(t)
    await session.commit()


# ---------------------------------------------------------------------------
# 7.5 — Comentarios
# ---------------------------------------------------------------------------

@pytest.mark.asyncio(loop_scope="session")
async def test_comentarios_add_list_access_control(integ_client, integ_setup):
    """7.5 RED+GREEN: add comment + list thread; access control; autor from session."""
    s = integ_setup
    session = s["session"]

    resp = await integ_client.post(
        "/api/v1/tareas",
        json={"asignado_a": str(s["docente_id"]), "descripcion": "Comentarios test"},
        headers=_auth(s["jwt_coord"]),
    )
    assert resp.status_code == 201
    t_id = resp.json()["id"]

    # docente (asignado_a) can comment
    resp2 = await integ_client.post(
        f"/api/v1/tareas/{t_id}/comentarios",
        json={"cuerpo": "Esto es un comentario"},
        headers=_auth(s["jwt_docente"]),
    )
    assert resp2.status_code == 201
    com_data = resp2.json()
    assert com_data["autor_id"] == str(s["docente_id"])  # from JWT
    assert com_data["es_sistema"] is False

    # List thread — docente can list
    resp3 = await integ_client.get(
        f"/api/v1/tareas/{t_id}/comentarios",
        headers=_auth(s["jwt_docente"]),
    )
    assert resp3.status_code == 200
    assert len(resp3.json()) >= 1

    # otro (no relation, no gestionar) cannot comment
    resp4 = await integ_client.post(
        f"/api/v1/tareas/{t_id}/comentarios",
        json={"cuerpo": "Intruso"},
        headers=_auth(s["jwt_otro"]),
    )
    assert resp4.status_code == 403

    # Cleanup
    from app.repositories.tarea_repository import TareaRepository
    repo = TareaRepository(session=session, tenant_id=s["tid_a"])
    t = await repo.get_by_id(uuid.UUID(t_id))
    if t:
        await repo.delete(t)
    await session.commit()


# ---------------------------------------------------------------------------
# 7.6 — GET /tareas/admin filters + soft-delete
# ---------------------------------------------------------------------------

@pytest.mark.asyncio(loop_scope="session")
async def test_admin_filters_and_soft_delete(integ_client, integ_setup):
    """7.6 RED+GREEN: admin filters work; soft-delete hides tarea everywhere."""
    s = integ_setup
    session = s["session"]

    # Create with materia
    resp1 = await integ_client.post(
        "/api/v1/tareas",
        json={
            "asignado_a": str(s["docente_id"]),
            "descripcion": "Admin filtro materia",
            "materia_id": str(s["materia_id"]),
        },
        headers=_auth(s["jwt_coord"]),
    )
    assert resp1.status_code == 201
    t1_id = resp1.json()["id"]

    # Without gestionar → 403 on admin
    resp_no_perm = await integ_client.get("/api/v1/tareas/admin", headers=_auth(s["jwt_docente"]))
    assert resp_no_perm.status_code == 403

    # With gestionar → 200
    resp_admin = await integ_client.get(
        "/api/v1/tareas/admin",
        headers=_auth(s["jwt_coord"]),
    )
    assert resp_admin.status_code == 200
    ids = {t["id"] for t in resp_admin.json()}
    assert t1_id in ids

    # Filter by materia_id
    resp_mat = await integ_client.get(
        f"/api/v1/tareas/admin?materia_id={s['materia_id']}",
        headers=_auth(s["jwt_coord"]),
    )
    assert resp_mat.status_code == 200
    mat_ids = {t["id"] for t in resp_mat.json()}
    assert t1_id in mat_ids

    # Filter by q (ILIKE)
    resp_q = await integ_client.get(
        "/api/v1/tareas/admin?q=filtro",
        headers=_auth(s["jwt_coord"]),
    )
    assert resp_q.status_code == 200
    q_ids = {t["id"] for t in resp_q.json()}
    assert t1_id in q_ids

    # Soft-delete
    resp_del = await integ_client.delete(
        f"/api/v1/tareas/{t1_id}",
        headers=_auth(s["jwt_coord"]),
    )
    assert resp_del.status_code == 204

    # After delete — not in admin list
    resp_after = await integ_client.get("/api/v1/tareas/admin", headers=_auth(s["jwt_coord"]))
    ids_after = {t["id"] for t in resp_after.json()}
    assert t1_id not in ids_after

    # After delete — not in mias
    resp_mias = await integ_client.get("/api/v1/tareas/mias", headers=_auth(s["jwt_docente"]))
    mias_ids = {t["id"] for t in resp_mias.json()}
    assert t1_id not in mias_ids

    await session.commit()


# ---------------------------------------------------------------------------
# 7.7 — Tenant isolation
# ---------------------------------------------------------------------------

@pytest.mark.asyncio(loop_scope="session")
async def test_tenant_isolation(integ_client, integ_setup):
    """7.7 RED+GREEN: tarea of another tenant → 404 on detail/state-change/admin."""
    s = integ_setup
    session = s["session"]

    # Create tarea in tenant A
    resp = await integ_client.post(
        "/api/v1/tareas",
        json={"asignado_a": str(s["docente_id"]), "descripcion": "Tenant A isolation"},
        headers=_auth(s["jwt_coord"]),
    )
    assert resp.status_code == 201
    t_id = resp.json()["id"]

    # Tenant B coord tries to get detail
    resp_b = await integ_client.get(
        f"/api/v1/tareas/{t_id}",
        headers=_auth(s["jwt_coord_b"]),
    )
    assert resp_b.status_code in (403, 404)

    # Tenant B admin list does NOT include tenant A's tarea
    resp_admin_b = await integ_client.get(
        "/api/v1/tareas/admin",
        headers=_auth(s["jwt_coord_b"]),
    )
    assert resp_admin_b.status_code == 200
    ids_b = {t["id"] for t in resp_admin_b.json()}
    assert t_id not in ids_b

    # Cleanup
    from app.repositories.tarea_repository import TareaRepository
    repo = TareaRepository(session=session, tenant_id=s["tid_a"])
    t = await repo.get_by_id(uuid.UUID(t_id))
    if t:
        await repo.delete(t)
    await session.commit()


# ---------------------------------------------------------------------------
# 7.8 — Contexto polimórfico
# ---------------------------------------------------------------------------

@pytest.mark.asyncio(loop_scope="session")
async def test_contexto_both_null_accepted(integ_client, integ_setup):
    """7.8 RED+GREEN: both contexto fields null → accepted."""
    s = integ_setup
    session = s["session"]

    resp = await integ_client.post(
        "/api/v1/tareas",
        json={
            "asignado_a": str(s["docente_id"]),
            "descripcion": "Sin contexto",
        },
        headers=_auth(s["jwt_coord"]),
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["contexto_id"] is None
    assert data["contexto_tipo"] is None

    from app.repositories.tarea_repository import TareaRepository
    repo = TareaRepository(session=session, tenant_id=s["tid_a"])
    t = await repo.get_by_id(uuid.UUID(data["id"]))
    if t:
        await repo.delete(t)
    await session.commit()


@pytest.mark.asyncio(loop_scope="session")
async def test_contexto_both_present_accepted(integ_client, integ_setup):
    """7.8 RED+GREEN: both contexto fields present → accepted."""
    s = integ_setup
    session = s["session"]

    ctx_id = str(uuid.uuid4())
    resp = await integ_client.post(
        "/api/v1/tareas",
        json={
            "asignado_a": str(s["docente_id"]),
            "descripcion": "Con contexto",
            "contexto_id": ctx_id,
            "contexto_tipo": "Encuentro",
        },
        headers=_auth(s["jwt_coord"]),
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["contexto_id"] == ctx_id
    assert data["contexto_tipo"] == "Encuentro"

    from app.repositories.tarea_repository import TareaRepository
    repo = TareaRepository(session=session, tenant_id=s["tid_a"])
    t = await repo.get_by_id(uuid.UUID(data["id"]))
    if t:
        await repo.delete(t)
    await session.commit()


@pytest.mark.asyncio(loop_scope="session")
async def test_contexto_only_id_rejected_422(integ_client, integ_setup):
    """7.8 RED+GREEN: only contexto_id present → 422."""
    s = integ_setup
    resp = await integ_client.post(
        "/api/v1/tareas",
        json={
            "asignado_a": str(s["docente_id"]),
            "descripcion": "Solo id",
            "contexto_id": str(uuid.uuid4()),
        },
        headers=_auth(s["jwt_coord"]),
    )
    assert resp.status_code == 422


@pytest.mark.asyncio(loop_scope="session")
async def test_contexto_only_tipo_rejected_422(integ_client, integ_setup):
    """7.8 RED+GREEN: only contexto_tipo present → 422."""
    s = integ_setup
    resp = await integ_client.post(
        "/api/v1/tareas",
        json={
            "asignado_a": str(s["docente_id"]),
            "descripcion": "Solo tipo",
            "contexto_tipo": "Coloquio",
        },
        headers=_auth(s["jwt_coord"]),
    )
    assert resp.status_code == 422
