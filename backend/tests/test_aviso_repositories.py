"""
test_aviso_repositories.py — TDD tests for C-15 AvisoRepository + AcknowledgmentRepository.

Tasks 4.1–4.6: CRUD, feed audience query (4 branches), pending feed, ack COUNT.

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
async def repo_engine():
    engine = create_async_engine(TEST_DATABASE_URL, poolclass=NullPool, echo=False)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture(scope="module")
async def repo_session(repo_engine):
    """Create all tables (idempotent) and return a shared async session."""
    import app.models  # noqa: F401

    async with repo_engine.begin() as conn:
        # Enums
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

        # audit_action values
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

        # Partial unique index for ack (idempotent)
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

    factory = build_session_factory(repo_engine)
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
    """Return (inicio_en, fin_en) relative to now."""
    now = _now()
    return now + timedelta(days=delta_start), now + timedelta(days=delta_end)


async def _create_tenant(session, tid, name):
    from app.models.tenant import Tenant, TenantEstado
    t = Tenant(id=tid, nombre=name, estado=TenantEstado.ACTIVO)
    session.add(t)
    await session.flush()
    return t


async def _create_estructura(session, tid):
    from app.models.estructura import Carrera, Cohorte, Materia, EstadoEstructura
    car = Carrera(tenant_id=tid, codigo=f"C_{uuid.uuid4().hex[:4]}", nombre="Carrera", estado=EstadoEstructura.activa)
    mat = Materia(tenant_id=tid, codigo=f"M_{uuid.uuid4().hex[:4]}", nombre="Materia", estado=EstadoEstructura.activa)
    session.add(car)
    session.add(mat)
    await session.flush()
    coh = Cohorte(tenant_id=tid, carrera_id=car.id, nombre="Coh", anio=2026,
                  vig_desde=date.today(), estado=EstadoEstructura.activa)
    session.add(coh)
    await session.flush()
    return car, mat, coh


async def _create_usuario(session, tid, suffix, rol="PROFESOR"):
    from app.models.usuario import Usuario, UsuarioEstado, Asignacion, RolAsignacion
    from app.core.security.passwords import email_lookup_hash as _hash
    email = f"repo_{suffix}_{uuid.uuid4().hex[:6]}@test.com"
    u = Usuario(
        tenant_id=tid, email_encrypted=email, email_hash=_hash(email),
        nombre="Test", apellidos=suffix, estado=UsuarioEstado.activo,
    )
    session.add(u)
    await session.flush()
    return u


async def _create_usuario_con_cohorte(session, tid, cohorte_id, suffix="coh_user"):
    """Create a usuario and link them to a cohorte via Asignacion."""
    from app.models.usuario import Usuario, UsuarioEstado, Asignacion, RolAsignacion
    from app.core.security.passwords import email_lookup_hash as _hash
    email = f"repo_{suffix}_{uuid.uuid4().hex[:6]}@test.com"
    u = Usuario(
        tenant_id=tid, email_encrypted=email, email_hash=_hash(email),
        nombre="Test", apellidos=suffix, estado=UsuarioEstado.activo,
    )
    session.add(u)
    await session.flush()
    asig = Asignacion(
        tenant_id=tid,
        usuario_id=u.id,
        rol=RolAsignacion.TUTOR,
        cohorte_id=cohorte_id,
        desde=date.today(),
    )
    session.add(asig)
    await session.flush()
    return u


async def _create_usuario_con_materia(session, tid, materia_id, suffix="mat_user"):
    """Create a usuario and link them to a materia via Asignacion."""
    from app.models.usuario import Usuario, UsuarioEstado, Asignacion, RolAsignacion
    from app.core.security.passwords import email_lookup_hash as _hash
    email = f"repo_{suffix}_{uuid.uuid4().hex[:6]}@test.com"
    u = Usuario(
        tenant_id=tid, email_encrypted=email, email_hash=_hash(email),
        nombre="Test", apellidos=suffix, estado=UsuarioEstado.activo,
    )
    session.add(u)
    await session.flush()
    asig = Asignacion(
        tenant_id=tid,
        usuario_id=u.id,
        rol=RolAsignacion.PROFESOR,
        materia_id=materia_id,
        desde=date.today(),
    )
    session.add(asig)
    await session.flush()
    return u


def _make_aviso_repo(session, tid):
    from app.repositories.aviso_repository import AvisoRepository
    return AvisoRepository(session=session, tenant_id=tid)


def _make_ack_repo(session, tid):
    from app.repositories.aviso_repository import AcknowledgmentRepository
    return AcknowledgmentRepository(session=session, tenant_id=tid)


def _new_aviso(tid, alcance, inicio_en, fin_en, **kwargs):
    from app.models.aviso import Aviso, AvisoSeveridad
    return Aviso(
        tenant_id=tid,
        alcance=alcance,
        severidad=kwargs.pop("severidad", AvisoSeveridad.Info),
        titulo=kwargs.pop("titulo", "Test Aviso"),
        cuerpo=kwargs.pop("cuerpo", "Contenido"),
        inicio_en=inicio_en,
        fin_en=fin_en,
        orden=kwargs.pop("orden", 1),
        activo=kwargs.pop("activo", True),
        requiere_ack=kwargs.pop("requiere_ack", False),
        **kwargs,
    )


# ---------------------------------------------------------------------------
# Task 4.1 / 4.2 — CRUD scoped to tenant
# ---------------------------------------------------------------------------

@pytest.mark.asyncio(loop_scope="session")
async def test_crear_aviso_y_recuperar(repo_session):
    """4.1 RED: create aviso → same tenant can retrieve it."""
    from app.models.aviso import AvisoAlcance

    tid = uuid.uuid4()
    await _create_tenant(repo_session, tid, f"RepoCRUDT_{tid.hex[:4]}")
    await repo_session.commit()

    inicio, fin = _window()
    aviso = _new_aviso(tid, AvisoAlcance.Global, inicio, fin)
    repo = _make_aviso_repo(repo_session, tid)
    aviso = await repo.add(aviso)

    fetched = await repo.get_by_id(aviso.id)
    assert fetched is not None
    assert fetched.id == aviso.id
    assert fetched.tenant_id == tid

    # Cleanup
    await repo.delete(fetched)
    await repo_session.commit()


@pytest.mark.asyncio(loop_scope="session")
async def test_aviso_cross_tenant_returns_nothing(repo_session):
    """4.1 TRIANGULATE: aviso from tenant A is invisible to tenant B."""
    from app.models.aviso import AvisoAlcance

    tid_a = uuid.uuid4()
    tid_b = uuid.uuid4()
    await _create_tenant(repo_session, tid_a, f"CrossA_{tid_a.hex[:4]}")
    await _create_tenant(repo_session, tid_b, f"CrossB_{tid_b.hex[:4]}")
    await repo_session.commit()

    inicio, fin = _window()
    aviso = _new_aviso(tid_a, AvisoAlcance.Global, inicio, fin)
    repo_a = _make_aviso_repo(repo_session, tid_a)
    aviso = await repo_a.add(aviso)

    # Tenant B cannot see it
    repo_b = _make_aviso_repo(repo_session, tid_b)
    fetched = await repo_b.get_by_id(aviso.id)
    assert fetched is None

    # Cleanup
    await repo_a.delete(aviso)
    await repo_session.commit()


@pytest.mark.asyncio(loop_scope="session")
async def test_soft_delete_hides_aviso(repo_session):
    """4.2 GREEN: soft-deleted aviso not returned in normal queries."""
    from app.models.aviso import AvisoAlcance

    tid = uuid.uuid4()
    await _create_tenant(repo_session, tid, f"SoftDelT_{tid.hex[:4]}")
    await repo_session.commit()

    inicio, fin = _window()
    aviso = _new_aviso(tid, AvisoAlcance.Global, inicio, fin)
    repo = _make_aviso_repo(repo_session, tid)
    aviso = await repo.add(aviso)
    aviso_id = aviso.id

    await repo.delete(aviso)

    fetched = await repo.get_by_id(aviso_id)
    assert fetched is None

    await repo_session.commit()


# ---------------------------------------------------------------------------
# Task 4.3 / 4.4 — Recipient feed query (all 4 branches)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio(loop_scope="session")
async def test_feed_global_shown_to_any_user(repo_session):
    """4.3 RED: Global aviso appears for any user in the tenant."""
    from app.models.aviso import AvisoAlcance

    tid = uuid.uuid4()
    await _create_tenant(repo_session, tid, f"FeedGlobal_{tid.hex[:4]}")
    usuario = await _create_usuario(repo_session, tid, "g_user")
    await repo_session.commit()

    inicio, fin = _window()
    aviso = _new_aviso(tid, AvisoAlcance.Global, inicio, fin)
    repo = _make_aviso_repo(repo_session, tid)
    aviso = await repo.add(aviso)

    feed = await repo.get_recipient_feed(
        usuario_id=usuario.id,
        roles=["PROFESOR"],
        cohorte_id=None,
    )
    assert any(a.id == aviso.id for a in feed)

    await repo.delete(aviso)
    await repo_session.commit()


@pytest.mark.asyncio(loop_scope="session")
async def test_feed_por_rol_shown_only_to_target_role(repo_session):
    """4.3 TRIANGULATE: PorRol aviso shown to matching role only."""
    from app.models.aviso import AvisoAlcance

    tid = uuid.uuid4()
    await _create_tenant(repo_session, tid, f"FeedRol_{tid.hex[:4]}")
    await repo_session.commit()

    inicio, fin = _window()
    aviso = _new_aviso(tid, AvisoAlcance.PorRol, inicio, fin, rol_destino="COORDINADOR")
    repo = _make_aviso_repo(repo_session, tid)
    aviso = await repo.add(aviso)

    # COORDINADOR sees it
    feed_coord = await repo.get_recipient_feed(
        usuario_id=uuid.uuid4(), roles=["COORDINADOR"], cohorte_id=None
    )
    assert any(a.id == aviso.id for a in feed_coord)

    # PROFESOR does NOT see it
    feed_prof = await repo.get_recipient_feed(
        usuario_id=uuid.uuid4(), roles=["PROFESOR"], cohorte_id=None
    )
    assert not any(a.id == aviso.id for a in feed_prof)

    await repo.delete(aviso)
    await repo_session.commit()


@pytest.mark.asyncio(loop_scope="session")
async def test_feed_por_cohorte_shown_only_to_correct_cohorte(repo_session):
    """4.3 TRIANGULATE: PorCohorte aviso shown only to users in that cohorte."""
    from app.models.aviso import AvisoAlcance
    from app.models.estructura import EstadoEstructura, Carrera, Cohorte

    tid = uuid.uuid4()
    await _create_tenant(repo_session, tid, f"FeedCoh_{tid.hex[:4]}")
    car = Carrera(tenant_id=tid, codigo=f"C_{uuid.uuid4().hex[:4]}", nombre="C", estado=EstadoEstructura.activa)
    repo_session.add(car)
    await repo_session.flush()
    coh1 = Cohorte(tenant_id=tid, carrera_id=car.id, nombre="C1", anio=2026, vig_desde=date.today(), estado=EstadoEstructura.activa)
    coh2 = Cohorte(tenant_id=tid, carrera_id=car.id, nombre="C2", anio=2026, vig_desde=date.today(), estado=EstadoEstructura.activa)
    repo_session.add(coh1)
    repo_session.add(coh2)
    await repo_session.commit()

    inicio, fin = _window()
    aviso = _new_aviso(tid, AvisoAlcance.PorCohorte, inicio, fin, cohorte_id=coh1.id)
    repo = _make_aviso_repo(repo_session, tid)
    aviso = await repo.add(aviso)

    feed_c1 = await repo.get_recipient_feed(
        usuario_id=uuid.uuid4(), roles=["PROFESOR"], cohorte_id=coh1.id
    )
    assert any(a.id == aviso.id for a in feed_c1)

    feed_c2 = await repo.get_recipient_feed(
        usuario_id=uuid.uuid4(), roles=["PROFESOR"], cohorte_id=coh2.id
    )
    assert not any(a.id == aviso.id for a in feed_c2)

    await repo.delete(aviso)
    await repo_session.commit()


@pytest.mark.asyncio(loop_scope="session")
async def test_feed_por_materia_shown_only_to_linked_users(repo_session):
    """4.3 TRIANGULATE: PorMateria aviso shown only to users linked to that materia."""
    from app.models.aviso import AvisoAlcance
    from app.models.estructura import Materia, EstadoEstructura

    tid = uuid.uuid4()
    await _create_tenant(repo_session, tid, f"FeedMat_{tid.hex[:4]}")
    mat1 = Materia(tenant_id=tid, codigo=f"M1_{uuid.uuid4().hex[:4]}", nombre="M1", estado=EstadoEstructura.activa)
    mat2 = Materia(tenant_id=tid, codigo=f"M2_{uuid.uuid4().hex[:4]}", nombre="M2", estado=EstadoEstructura.activa)
    repo_session.add(mat1)
    repo_session.add(mat2)
    await repo_session.flush()
    user_mat1 = await _create_usuario_con_materia(repo_session, tid, mat1.id, "mat1_user")
    user_mat2 = await _create_usuario_con_materia(repo_session, tid, mat2.id, "mat2_user")
    await repo_session.commit()

    inicio, fin = _window()
    aviso = _new_aviso(tid, AvisoAlcance.PorMateria, inicio, fin, materia_id=mat1.id)
    repo = _make_aviso_repo(repo_session, tid)
    aviso = await repo.add(aviso)

    feed_user1 = await repo.get_recipient_feed(
        usuario_id=user_mat1.id, roles=["PROFESOR"], cohorte_id=None
    )
    assert any(a.id == aviso.id for a in feed_user1)

    feed_user2 = await repo.get_recipient_feed(
        usuario_id=user_mat2.id, roles=["PROFESOR"], cohorte_id=None
    )
    assert not any(a.id == aviso.id for a in feed_user2)

    await repo.delete(aviso)
    await repo_session.commit()


@pytest.mark.asyncio(loop_scope="session")
async def test_feed_excludes_inactive_aviso(repo_session):
    """4.4 GREEN: inactive aviso (activo=False) does not appear in feed."""
    from app.models.aviso import AvisoAlcance

    tid = uuid.uuid4()
    await _create_tenant(repo_session, tid, f"FeedInactive_{tid.hex[:4]}")
    await repo_session.commit()

    inicio, fin = _window()
    aviso = _new_aviso(tid, AvisoAlcance.Global, inicio, fin, activo=False)
    repo = _make_aviso_repo(repo_session, tid)
    aviso = await repo.add(aviso)

    feed = await repo.get_recipient_feed(
        usuario_id=uuid.uuid4(), roles=["PROFESOR"], cohorte_id=None
    )
    assert not any(a.id == aviso.id for a in feed)

    await repo.delete(aviso)
    await repo_session.commit()


@pytest.mark.asyncio(loop_scope="session")
async def test_feed_excludes_future_aviso(repo_session):
    """4.4 GREEN: not-yet-started aviso does not appear in feed."""
    from app.models.aviso import AvisoAlcance

    tid = uuid.uuid4()
    await _create_tenant(repo_session, tid, f"FeedFuture_{tid.hex[:4]}")
    await repo_session.commit()

    inicio, fin = _window(delta_start=2, delta_end=5)  # future window
    aviso = _new_aviso(tid, AvisoAlcance.Global, inicio, fin)
    repo = _make_aviso_repo(repo_session, tid)
    aviso = await repo.add(aviso)

    feed = await repo.get_recipient_feed(
        usuario_id=uuid.uuid4(), roles=["PROFESOR"], cohorte_id=None
    )
    assert not any(a.id == aviso.id for a in feed)

    await repo.delete(aviso)
    await repo_session.commit()


@pytest.mark.asyncio(loop_scope="session")
async def test_feed_excludes_expired_aviso(repo_session):
    """4.4 GREEN: expired aviso does not appear in feed."""
    from app.models.aviso import AvisoAlcance

    tid = uuid.uuid4()
    await _create_tenant(repo_session, tid, f"FeedExpired_{tid.hex[:4]}")
    await repo_session.commit()

    inicio, fin = _window(delta_start=-5, delta_end=-2)  # past window
    aviso = _new_aviso(tid, AvisoAlcance.Global, inicio, fin)
    repo = _make_aviso_repo(repo_session, tid)
    aviso = await repo.add(aviso)

    feed = await repo.get_recipient_feed(
        usuario_id=uuid.uuid4(), roles=["PROFESOR"], cohorte_id=None
    )
    assert not any(a.id == aviso.id for a in feed)

    await repo.delete(aviso)
    await repo_session.commit()


@pytest.mark.asyncio(loop_scope="session")
async def test_feed_ordering_by_orden_then_severidad(repo_session):
    """4.4 GREEN: feed ordered orden ASC, then severidad DESC (Critico > Advertencia > Info)."""
    from app.models.aviso import AvisoAlcance, AvisoSeveridad

    tid = uuid.uuid4()
    await _create_tenant(repo_session, tid, f"FeedOrder_{tid.hex[:4]}")
    await repo_session.commit()

    inicio, fin = _window()
    repo = _make_aviso_repo(repo_session, tid)

    a_low = _new_aviso(tid, AvisoAlcance.Global, inicio, fin, orden=5, severidad=AvisoSeveridad.Critico, titulo="orden5")
    a_high = _new_aviso(tid, AvisoAlcance.Global, inicio, fin, orden=1, severidad=AvisoSeveridad.Info, titulo="orden1")
    a_tie_crit = _new_aviso(tid, AvisoAlcance.Global, inicio, fin, orden=2, severidad=AvisoSeveridad.Critico, titulo="orden2Crit")
    a_tie_info = _new_aviso(tid, AvisoAlcance.Global, inicio, fin, orden=2, severidad=AvisoSeveridad.Info, titulo="orden2Info")

    a_low = await repo.add(a_low)
    a_high = await repo.add(a_high)
    a_tie_crit = await repo.add(a_tie_crit)
    a_tie_info = await repo.add(a_tie_info)

    feed = await repo.get_recipient_feed(
        usuario_id=uuid.uuid4(), roles=["PROFESOR"], cohorte_id=None
    )

    ids = [a.id for a in feed]
    idx_high = ids.index(a_high.id)
    idx_low = ids.index(a_low.id)
    idx_crit = ids.index(a_tie_crit.id)
    idx_info = ids.index(a_tie_info.id)

    assert idx_high < idx_low, "orden=1 must come before orden=5"
    assert idx_crit < idx_info, "Critico must come before Info when orden is equal"

    for a in [a_low, a_high, a_tie_crit, a_tie_info]:
        await repo.delete(a)
    await repo_session.commit()


# ---------------------------------------------------------------------------
# Task 4.5 — Pending feed (requiere_ack + no active ack)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio(loop_scope="session")
async def test_pending_feed_excludes_acked_aviso(repo_session):
    """4.5 RED: acknowledged aviso drops from pending feed but stays in full feed."""
    from app.models.aviso import AvisoAlcance, AcknowledgmentAviso

    tid = uuid.uuid4()
    await _create_tenant(repo_session, tid, f"PendAck_{tid.hex[:4]}")
    usuario = await _create_usuario(repo_session, tid, "pend_user")
    await repo_session.commit()

    inicio, fin = _window()
    aviso = _new_aviso(tid, AvisoAlcance.Global, inicio, fin, requiere_ack=True)
    repo = _make_aviso_repo(repo_session, tid)
    ack_repo = _make_ack_repo(repo_session, tid)
    aviso = await repo.add(aviso)

    # Before ack: appears in pending feed
    pending_before = await repo.get_pending_feed(
        usuario_id=usuario.id, roles=["PROFESOR"], cohorte_id=None
    )
    assert any(a.id == aviso.id for a in pending_before)

    # Acknowledge
    ack = AcknowledgmentAviso(
        tenant_id=tid,
        aviso_id=aviso.id,
        usuario_id=usuario.id,
        confirmado_at=datetime.now(tz=timezone.utc),
    )
    ack = await ack_repo.add(ack)

    # After ack: does NOT appear in pending
    pending_after = await repo.get_pending_feed(
        usuario_id=usuario.id, roles=["PROFESOR"], cohorte_id=None
    )
    assert not any(a.id == aviso.id for a in pending_after)

    # But full feed still shows it
    full_feed = await repo.get_recipient_feed(
        usuario_id=usuario.id, roles=["PROFESOR"], cohorte_id=None
    )
    assert any(a.id == aviso.id for a in full_feed)

    # Cleanup
    await ack_repo.delete(ack)
    await repo.delete(aviso)
    await repo_session.commit()


@pytest.mark.asyncio(loop_scope="session")
async def test_non_requiere_ack_never_in_pending(repo_session):
    """4.5 TRIANGULATE: aviso with requiere_ack=False never in pending feed."""
    from app.models.aviso import AvisoAlcance

    tid = uuid.uuid4()
    await _create_tenant(repo_session, tid, f"NoAck_{tid.hex[:4]}")
    await repo_session.commit()

    inicio, fin = _window()
    aviso = _new_aviso(tid, AvisoAlcance.Global, inicio, fin, requiere_ack=False)
    repo = _make_aviso_repo(repo_session, tid)
    aviso = await repo.add(aviso)

    pending = await repo.get_pending_feed(
        usuario_id=uuid.uuid4(), roles=["PROFESOR"], cohorte_id=None
    )
    assert not any(a.id == aviso.id for a in pending)

    await repo.delete(aviso)
    await repo_session.commit()


# ---------------------------------------------------------------------------
# Task 4.6 — Derived ack COUNT
# ---------------------------------------------------------------------------

@pytest.mark.asyncio(loop_scope="session")
async def test_ack_count_reflects_active_acks(repo_session):
    """4.6 RED: ack count = number of active AcknowledgmentAviso rows."""
    from app.models.aviso import AvisoAlcance, AcknowledgmentAviso

    tid = uuid.uuid4()
    await _create_tenant(repo_session, tid, f"AckCnt_{tid.hex[:4]}")
    u1 = await _create_usuario(repo_session, tid, "cnt_u1")
    u2 = await _create_usuario(repo_session, tid, "cnt_u2")
    u3 = await _create_usuario(repo_session, tid, "cnt_u3")
    await repo_session.commit()

    inicio, fin = _window()
    aviso = _new_aviso(tid, AvisoAlcance.Global, inicio, fin, requiere_ack=True)
    repo = _make_aviso_repo(repo_session, tid)
    ack_repo = _make_ack_repo(repo_session, tid)
    aviso = await repo.add(aviso)

    now = datetime.now(tz=timezone.utc)
    acks = []
    for u in [u1, u2, u3]:
        ack = AcknowledgmentAviso(
            tenant_id=tid, aviso_id=aviso.id, usuario_id=u.id, confirmado_at=now
        )
        acks.append(await ack_repo.add(ack))

    count = await ack_repo.count_acks(aviso.id)
    assert count == 3

    # Soft-delete one ack → count drops to 2
    await ack_repo.delete(acks[0])
    count2 = await ack_repo.count_acks(aviso.id)
    assert count2 == 2

    # Cleanup
    for ack in acks[1:]:
        await ack_repo.delete(ack)
    await repo.delete(aviso)
    await repo_session.commit()


@pytest.mark.asyncio(loop_scope="session")
async def test_ack_count_cross_tenant_scoped(repo_session):
    """4.6 TRIANGULATE: ack count only includes same tenant."""
    from app.models.aviso import AvisoAlcance, AcknowledgmentAviso

    tid_a = uuid.uuid4()
    tid_b = uuid.uuid4()
    await _create_tenant(repo_session, tid_a, f"AckCntA_{tid_a.hex[:4]}")
    await _create_tenant(repo_session, tid_b, f"AckCntB_{tid_b.hex[:4]}")
    u_a = await _create_usuario(repo_session, tid_a, "ack_cnt_a")
    await repo_session.commit()

    inicio, fin = _window()
    aviso = _new_aviso(tid_a, AvisoAlcance.Global, inicio, fin, requiere_ack=True)
    repo_a = _make_aviso_repo(repo_session, tid_a)
    ack_repo_a = _make_ack_repo(repo_session, tid_a)
    aviso = await repo_a.add(aviso)

    ack = AcknowledgmentAviso(
        tenant_id=tid_a, aviso_id=aviso.id, usuario_id=u_a.id,
        confirmado_at=datetime.now(tz=timezone.utc)
    )
    ack = await ack_repo_a.add(ack)

    # Tenant B's repo cannot see tenant A's ack
    ack_repo_b = _make_ack_repo(repo_session, tid_b)
    count_b = await ack_repo_b.count_acks(aviso.id)
    assert count_b == 0

    count_a = await ack_repo_a.count_acks(aviso.id)
    assert count_a == 1

    await ack_repo_a.delete(ack)
    await repo_a.delete(aviso)
    await repo_session.commit()
