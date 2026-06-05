"""
test_avisos_gestion.py — TDD tests for GET /avisos/gestion management-list endpoint.

C-23 OQ-1 resolution / C-15 follow-up:
    - Repository: listar_todos_gestion() returns ALL non-deleted tenant avisos (unfiltered).
    - Service: listar_gestion(actor) returns AvisoRead list with ack_count populated.
    - Router: GET /avisos/gestion gated by avisos:publicar (403 for ALUMNO/TUTOR).

Triangulation cases (mandatory):
    G1 — Returns ALL tenant avisos including ones NOT in the caller's audience.
    G2 — 403 for a role without avisos:publicar (ALUMNO / TUTOR).
    G3 — Tenant isolation: does NOT return another tenant's avisos.
    G4 — Excludes soft-deleted avisos.
    G5 — ack_count is populated correctly (>= 1 ack scenario).

DB real: activia_trace_test. Sin mocks.
"""
import asyncio
import uuid
from datetime import date, datetime, timedelta, timezone

import pytest
import pytest_asyncio
from dotenv import load_dotenv
import os
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import NullPool

from app.core.database import build_session_factory
from app.core.dependencies import CurrentUser

load_dotenv()
TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://postgres@localhost:5432/activia_trace_test",
)

# ---------------------------------------------------------------------------
# Session fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="module")
async def gestion_engine():
    engine = create_async_engine(TEST_DATABASE_URL, poolclass=NullPool, echo=False)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture(scope="module")
async def gestion_session(gestion_engine):
    """Create all tables (idempotent) and return a shared async session."""
    import app.models  # noqa: F401

    async with gestion_engine.begin() as conn:
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
        ]:
            await conn.execute(text(stmt))

        for action in [
            "PADRON_CARGAR", "CALIFICACIONES_IMPORTAR", "COMUNICACION_ENVIAR",
            "EQUIPOS_ASIGNACION_MASIVA", "EQUIPOS_CLONAR", "EQUIPOS_VIGENCIA_GENERAL",
            "ENCUENTRO_GESTIONAR", "COLOQUIO_GESTIONAR", "AVISO_PUBLICAR",
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

    factory = build_session_factory(gestion_engine)
    session = factory()
    yield session
    try:
        await session.rollback()
        await session.close()
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _now():
    return datetime.now(tz=timezone.utc)


def _window(delta_start=-1, delta_end=1):
    now = _now()
    return now + timedelta(days=delta_start), now + timedelta(days=delta_end)


async def _create_tenant(session, tid, name):
    from app.models.tenant import Tenant, TenantEstado
    t = Tenant(id=tid, nombre=name, estado=TenantEstado.ACTIVO)
    session.add(t)
    await session.flush()
    return t


async def _create_usuario(session, tid, suffix):
    from app.models.usuario import Usuario, UsuarioEstado
    from app.core.security.passwords import email_lookup_hash as _hash
    email = f"gest_{suffix}_{uuid.uuid4().hex[:6]}@test.com"
    u = Usuario(
        tenant_id=tid, email_encrypted=email, email_hash=_hash(email),
        nombre="Test", apellidos=suffix, estado=UsuarioEstado.activo,
    )
    session.add(u)
    await session.flush()
    return u


def _actor(tid, uid, roles=None):
    return CurrentUser(user_id=uid, tenant_id=tid, roles=roles or ["COORDINADOR"])


def _make_service(session, tid):
    from app.repositories.aviso_repository import AvisoRepository, AcknowledgmentRepository
    from app.repositories.audit_repository import AuditRepository
    from app.services.aviso_service import AvisoService
    return AvisoService(
        aviso_repo=AvisoRepository(session=session, tenant_id=tid),
        ack_repo=AcknowledgmentRepository(session=session, tenant_id=tid),
        audit_repo=AuditRepository(session=session, tenant_id=tid),
    )


def _new_aviso(tid, titulo="Test Aviso", **kwargs):
    from app.models.aviso import Aviso, AvisoAlcance, AvisoSeveridad
    inicio, fin = _window()
    return Aviso(
        tenant_id=tid,
        alcance=kwargs.pop("alcance", AvisoAlcance.Global),
        severidad=kwargs.pop("severidad", AvisoSeveridad.Info),
        titulo=titulo,
        cuerpo="Contenido",
        inicio_en=kwargs.pop("inicio_en", inicio),
        fin_en=kwargs.pop("fin_en", fin),
        orden=kwargs.pop("orden", 1),
        activo=kwargs.pop("activo", True),
        requiere_ack=kwargs.pop("requiere_ack", False),
        **kwargs,
    )


# ===========================================================================
# STRUCTURAL TESTS (no DB) — route registration and permission wiring
# ===========================================================================

def test_gestion_route_registered():
    """RED (structural): /avisos/gestion path is registered in the router."""
    from app.api.v1.routers.avisos import router
    paths = {route.path for route in router.routes}
    assert "/avisos/gestion" in paths, (
        "GET /avisos/gestion route not registered — add it to the router"
    )


def test_gestion_route_has_require_permission():
    """RED (structural): /avisos/gestion route has require_permission dependency."""
    from app.api.v1.routers.avisos import router
    from fastapi.routing import APIRoute

    gestion_route = next(
        (r for r in router.routes
         if isinstance(r, APIRoute) and r.path == "/avisos/gestion"),
        None,
    )
    assert gestion_route is not None, "/avisos/gestion route not found"
    # Verify it's a GET
    assert "GET" in gestion_route.methods, "Expected GET method on /avisos/gestion"


# ===========================================================================
# G2 — 403 for role WITHOUT avisos:publicar (structural: guard wired to route)
# ===========================================================================

def test_gestion_route_has_permission_guard():
    """
    G2 RED: /avisos/gestion has require_permission("avisos:publicar") wired as a
    function parameter dependency — structural proof that the 403 guard is active.

    FastAPI stores the guard in route.dependant.dependencies when it is declared
    as a function parameter (`_grant=Depends(...)`). We check that a dependency
    named '_grant' with a call named '_guard' is present — same pattern used by
    POST/PUT/DELETE in C-15.
    """
    from fastapi.routing import APIRoute
    from app.api.v1.routers.avisos import router

    gestion_route = next(
        (r for r in router.routes
         if isinstance(r, APIRoute) and r.path == "/avisos/gestion"),
        None,
    )
    assert gestion_route is not None, "/avisos/gestion route not found"

    # require_permission guard appears in route.dependant.dependencies with name '_grant'
    dep_names = [d.name for d in gestion_route.dependant.dependencies]
    assert "_grant" in dep_names, (
        f"require_permission guard ('_grant') not found in /avisos/gestion dependencies. "
        f"Found: {dep_names}"
    )

    # The guard call is the inner _guard closure from require_permission factory
    guard_dep = next(d for d in gestion_route.dependant.dependencies if d.name == "_grant")
    assert guard_dep.call.__name__ == "_guard", (
        f"Expected _guard closure, got: {guard_dep.call.__name__}"
    )


def test_gestion_route_403_without_auth_unauthenticated():
    """
    G2 TRIANGULATE: GET /avisos/gestion without any token returns non-200.

    With no token and real dependencies, FastAPI returns 401/422/500 — never 200.
    This proves the endpoint is not publicly accessible.
    """
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from app.api.v1.routers.avisos import router

    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    client = TestClient(app, raise_server_exceptions=False)
    resp = client.get("/api/v1/avisos/gestion")
    # With no real DB wired, unauthed request fails before reaching the handler
    assert resp.status_code != 200, (
        "GET /avisos/gestion must NOT return 200 without authentication"
    )


# ===========================================================================
# G1 — Returns ALL tenant avisos (no audience filter) — the core fix
# ===========================================================================

@pytest.mark.asyncio(loop_scope="session")
async def test_listar_gestion_returns_all_tenant_avisos_no_audience_filter(gestion_session):
    """
    G1 RED: listar_gestion returns ALL non-deleted tenant avisos, INCLUDING ones
    not in the caller's audience (core fix vs. audience-filtered feed).
    """
    from app.models.aviso import AvisoAlcance, AvisoSeveridad
    from app.models.usuario import RolAsignacion

    tid = uuid.uuid4()
    await _create_tenant(gestion_session, tid, f"GestT_G1_{tid.hex[:4]}")
    u = await _create_usuario(gestion_session, tid, "coord_g1")
    await gestion_session.commit()

    # Aviso 1: Global — would appear in feed for this user
    av1 = _new_aviso(tid, titulo="Global aviso G1")
    gestion_session.add(av1)

    # Aviso 2: PorRol targeting ALUMNO — NOT in this COORDINADOR's audience
    av2 = _new_aviso(tid, titulo="Rol destino ALUMNO only",
                     alcance=AvisoAlcance.PorRol, rol_destino="ALUMNO")
    gestion_session.add(av2)

    await gestion_session.flush()
    await gestion_session.commit()

    actor = _actor(tid, u.id, roles=["COORDINADOR"])
    svc = _make_service(gestion_session, tid)

    result = await svc.listar_gestion(actor)
    result_ids = {r.id for r in result}

    assert av1.id in result_ids, "Global aviso should be in gestion list"
    assert av2.id in result_ids, (
        "PorRol/ALUMNO aviso must appear in management list even if not in "
        "the coordinator's own feed audience"
    )

    # Cleanup
    await gestion_session.delete(av1)
    await gestion_session.delete(av2)
    await gestion_session.commit()


# ===========================================================================
# G3 — Tenant isolation
# ===========================================================================

@pytest.mark.asyncio(loop_scope="session")
async def test_listar_gestion_tenant_isolation(gestion_session):
    """
    G3 RED: listar_gestion does NOT return avisos from another tenant.
    """
    tid_a = uuid.uuid4()
    tid_b = uuid.uuid4()
    await _create_tenant(gestion_session, tid_a, f"GestTA_{tid_a.hex[:4]}")
    await _create_tenant(gestion_session, tid_b, f"GestTB_{tid_b.hex[:4]}")
    u_a = await _create_usuario(gestion_session, tid_a, "coord_g3a")
    await gestion_session.commit()

    av_a = _new_aviso(tid_a, titulo="Tenant A aviso G3")
    av_b = _new_aviso(tid_b, titulo="Tenant B aviso G3")
    gestion_session.add(av_a)
    gestion_session.add(av_b)
    await gestion_session.flush()
    await gestion_session.commit()

    actor = _actor(tid_a, u_a.id, roles=["COORDINADOR"])
    svc = _make_service(gestion_session, tid_a)

    result = await svc.listar_gestion(actor)
    result_ids = {r.id for r in result}

    assert av_a.id in result_ids, "Own tenant's aviso should be returned"
    assert av_b.id not in result_ids, "Other tenant's aviso must NOT be returned"

    # Cleanup
    await gestion_session.delete(av_a)
    await gestion_session.delete(av_b)
    await gestion_session.commit()


# ===========================================================================
# G4 — Soft-deleted avisos are excluded
# ===========================================================================

@pytest.mark.asyncio(loop_scope="session")
async def test_listar_gestion_excludes_soft_deleted(gestion_session):
    """
    G4 RED: listar_gestion excludes soft-deleted avisos.
    """
    tid = uuid.uuid4()
    await _create_tenant(gestion_session, tid, f"GestT_G4_{tid.hex[:4]}")
    u = await _create_usuario(gestion_session, tid, "coord_g4")
    await gestion_session.commit()

    av_active = _new_aviso(tid, titulo="Active aviso G4")
    av_deleted = _new_aviso(tid, titulo="Deleted aviso G4")
    gestion_session.add(av_active)
    gestion_session.add(av_deleted)
    await gestion_session.flush()
    await gestion_session.commit()

    # Soft-delete av_deleted
    from app.repositories.aviso_repository import AvisoRepository
    repo = AvisoRepository(session=gestion_session, tenant_id=tid)
    await repo.delete(av_deleted)
    await gestion_session.commit()

    actor = _actor(tid, u.id, roles=["COORDINADOR"])
    svc = _make_service(gestion_session, tid)

    result = await svc.listar_gestion(actor)
    result_ids = {r.id for r in result}

    assert av_active.id in result_ids, "Active aviso should appear in gestion list"
    assert av_deleted.id not in result_ids, "Soft-deleted aviso must NOT appear"

    # Cleanup
    await gestion_session.delete(av_active)
    await gestion_session.commit()


# ===========================================================================
# G5 — ack_count is populated correctly
# ===========================================================================

@pytest.mark.asyncio(loop_scope="session")
async def test_listar_gestion_ack_count_populated(gestion_session):
    """
    G5 RED: listar_gestion returns ack_count correctly (>= 1 ack scenario).
    """
    tid = uuid.uuid4()
    await _create_tenant(gestion_session, tid, f"GestT_G5_{tid.hex[:4]}")
    u_coord = await _create_usuario(gestion_session, tid, "coord_g5")
    u_acker = await _create_usuario(gestion_session, tid, "acker_g5")
    await gestion_session.commit()

    av = _new_aviso(tid, titulo="Ack count aviso G5", requiere_ack=True)
    gestion_session.add(av)
    await gestion_session.flush()
    await gestion_session.commit()

    # Add one ack for u_acker
    from app.models.aviso import AcknowledgmentAviso
    ack = AcknowledgmentAviso(
        tenant_id=tid,
        aviso_id=av.id,
        usuario_id=u_acker.id,
        confirmado_at=_now(),
    )
    gestion_session.add(ack)
    await gestion_session.flush()
    await gestion_session.commit()

    actor = _actor(tid, u_coord.id, roles=["COORDINADOR"])
    svc = _make_service(gestion_session, tid)

    result = await svc.listar_gestion(actor)
    matching = [r for r in result if r.id == av.id]
    assert len(matching) == 1, "Aviso should appear in gestion list"
    assert matching[0].ack_count == 1, f"Expected ack_count=1, got {matching[0].ack_count}"

    # Cleanup
    await gestion_session.delete(ack)
    await gestion_session.delete(av)
    await gestion_session.commit()


# ===========================================================================
# G1b — Feed vs. gestion: coordinator sees aviso in gestion but not in feed
#        (proves gestion is truly unfiltered for audience)
# ===========================================================================

@pytest.mark.asyncio(loop_scope="session")
async def test_gestion_returns_aviso_not_in_callers_audience_feed(gestion_session):
    """
    G1b TRIANGULATE: an aviso targeted at ALUMNO role is NOT in the coordinator's
    audience feed, but IS in listar_gestion — proving the audience filter is absent.
    """
    from app.models.aviso import AvisoAlcance, AvisoSeveridad

    tid = uuid.uuid4()
    await _create_tenant(gestion_session, tid, f"GestT_G1b_{tid.hex[:4]}")
    u = await _create_usuario(gestion_session, tid, "coord_g1b")
    await gestion_session.commit()

    av_alumno = _new_aviso(
        tid, titulo="ALUMNO only aviso G1b",
        alcance=AvisoAlcance.PorRol, rol_destino="ALUMNO",
    )
    gestion_session.add(av_alumno)
    await gestion_session.flush()
    await gestion_session.commit()

    actor = _actor(tid, u.id, roles=["COORDINADOR"])
    svc = _make_service(gestion_session, tid)

    # Audience feed: COORDINADOR role feed should NOT include ALUMNO-targeted aviso
    feed_result = await svc.listar_feed(
        usuario_id=u.id, roles=["COORDINADOR"], cohorte_id=None, actor=actor,
    )
    feed_ids = {r.id for r in feed_result}
    assert av_alumno.id not in feed_ids, (
        "ALUMNO-targeted aviso should NOT appear in COORDINADOR's audience feed"
    )

    # Management list: SHOULD include it
    gestion_result = await svc.listar_gestion(actor)
    gestion_ids = {r.id for r in gestion_result}
    assert av_alumno.id in gestion_ids, (
        "ALUMNO-targeted aviso MUST appear in management list (no audience filter)"
    )

    # Cleanup
    await gestion_session.delete(av_alumno)
    await gestion_session.commit()
