"""
test_aviso_service.py — TDD tests for C-15 AvisoService.

Tasks 5.1–5.5:
    5.1 Management: publish/modify/soft-delete; identity from session; scope/validity rejected.
    5.2 Audit AVISO_PUBLICAR on create.
    5.3 Acknowledgment: ack visible; cannot ack out-of-audience/window/inactive/deleted; idempotent.
    5.4 Ack-or-no-op with visibility guard.
    5.5 Feed/pending delegation to repository; derived counters.

DB real: activia_trace_test. Sin mocks.
"""
import asyncio
import uuid
from datetime import date, datetime, timedelta, timezone

import pytest
import pytest_asyncio
from dotenv import load_dotenv
import os
from fastapi import HTTPException
from pydantic import ValidationError
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


@pytest.fixture(scope="module")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="module")
async def svc_engine():
    engine = create_async_engine(TEST_DATABASE_URL, poolclass=NullPool, echo=False)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture(scope="module")
async def svc_session(svc_engine):
    import app.models  # noqa: F401

    async with svc_engine.begin() as conn:
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

    factory = build_session_factory(svc_engine)
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
    email = f"svc_{suffix}_{uuid.uuid4().hex[:6]}@test.com"
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


# ---------------------------------------------------------------------------
# 5.1 / 5.2 — Management + audit
# ---------------------------------------------------------------------------

@pytest.mark.asyncio(loop_scope="session")
async def test_publicar_aviso_global(svc_session):
    """5.1 RED: publish Global aviso → persisted under caller's tenant."""
    from app.schemas.aviso import CrearAvisoRequest
    from app.models.aviso import AvisoAlcance, AvisoSeveridad

    tid = uuid.uuid4()
    await _create_tenant(svc_session, tid, f"SvcPubT_{tid.hex[:4]}")
    await svc_session.commit()

    inicio, fin = _window()
    actor = _actor(tid, uuid.uuid4())
    svc = _make_service(svc_session, tid)

    req = CrearAvisoRequest(
        alcance=AvisoAlcance.Global,
        severidad=AvisoSeveridad.Info,
        titulo="Aviso global",
        cuerpo="Contenido",
        inicio_en=inicio,
        fin_en=fin,
    )
    result = await svc.publicar_aviso(req, actor)
    assert result.tenant_id == tid
    assert result.alcance == AvisoAlcance.Global

    # Cleanup
    from app.repositories.aviso_repository import AvisoRepository
    repo = AvisoRepository(session=svc_session, tenant_id=tid)
    av = await repo.get_by_id(result.id)
    if av:
        await repo.delete(av)
    await svc_session.commit()


@pytest.mark.asyncio(loop_scope="session")
async def test_publicar_aviso_registra_audit(svc_session):
    """5.2 GREEN: publish aviso → AVISO_PUBLICAR audit entry created."""
    from app.schemas.aviso import CrearAvisoRequest
    from app.models.aviso import AvisoAlcance, AvisoSeveridad
    from sqlalchemy import select
    from app.models.audit import AuditEvent, AuditAction

    tid = uuid.uuid4()
    await _create_tenant(svc_session, tid, f"SvcAuditT_{tid.hex[:4]}")
    await svc_session.commit()

    inicio, fin = _window()
    actor = _actor(tid, uuid.uuid4())
    svc = _make_service(svc_session, tid)

    req = CrearAvisoRequest(
        alcance=AvisoAlcance.Global,
        severidad=AvisoSeveridad.Alerta if hasattr(AvisoSeveridad, "Alerta") else AvisoSeveridad.Advertencia,
        titulo="Audit test",
        cuerpo="Body",
        inicio_en=inicio,
        fin_en=fin,
    )
    result = await svc.publicar_aviso(req, actor)

    # Verify audit entry
    stmt = select(AuditEvent).where(
        AuditEvent.tenant_id == tid,
        AuditEvent.accion == AuditAction.AVISO_PUBLICAR,
        AuditEvent.actor_user_id == actor.user_id,
    )
    r = await svc_session.execute(stmt)
    audit = r.scalar_one_or_none()
    assert audit is not None

    # Cleanup
    from app.repositories.aviso_repository import AvisoRepository
    repo = AvisoRepository(session=svc_session, tenant_id=tid)
    av = await repo.get_by_id(result.id)
    if av:
        await repo.delete(av)
    await svc_session.commit()


@pytest.mark.asyncio(loop_scope="session")
async def test_soft_delete_aviso_through_service(svc_session):
    """5.1 GREEN: soft-delete via service → deleted_at set, not in feed."""
    from app.schemas.aviso import CrearAvisoRequest
    from app.models.aviso import AvisoAlcance, AvisoSeveridad

    tid = uuid.uuid4()
    await _create_tenant(svc_session, tid, f"SvcDelT_{tid.hex[:4]}")
    await svc_session.commit()

    inicio, fin = _window()
    actor = _actor(tid, uuid.uuid4())
    svc = _make_service(svc_session, tid)

    req = CrearAvisoRequest(
        alcance=AvisoAlcance.Global,
        severidad=AvisoSeveridad.Info,
        titulo="Del test",
        cuerpo="Body",
        inicio_en=inicio,
        fin_en=fin,
    )
    aviso = await svc.publicar_aviso(req, actor)

    await svc.eliminar_aviso(aviso.id, actor)

    from app.repositories.aviso_repository import AvisoRepository
    repo = AvisoRepository(session=svc_session, tenant_id=tid)
    fetched = await repo.get_by_id(aviso.id)
    assert fetched is None  # soft-deleted → invisible

    await svc_session.commit()


@pytest.mark.asyncio(loop_scope="session")
async def test_modificar_aviso_otro_tenant_returns_404(svc_session):
    """5.1 TRIANGULATE: modify aviso from another tenant → 404."""
    from app.schemas.aviso import CrearAvisoRequest, ActualizarAvisoRequest
    from app.models.aviso import AvisoAlcance, AvisoSeveridad

    tid_a = uuid.uuid4()
    tid_b = uuid.uuid4()
    await _create_tenant(svc_session, tid_a, f"SvcA_{tid_a.hex[:4]}")
    await _create_tenant(svc_session, tid_b, f"SvcB_{tid_b.hex[:4]}")
    await svc_session.commit()

    inicio, fin = _window()
    actor_a = _actor(tid_a, uuid.uuid4())
    svc_a = _make_service(svc_session, tid_a)

    req = CrearAvisoRequest(
        alcance=AvisoAlcance.Global,
        severidad=AvisoSeveridad.Info,
        titulo="Aviso A",
        cuerpo="Body",
        inicio_en=inicio,
        fin_en=fin,
    )
    aviso = await svc_a.publicar_aviso(req, actor_a)

    # Tenant B tries to modify tenant A's aviso
    actor_b = _actor(tid_b, uuid.uuid4())
    svc_b = _make_service(svc_session, tid_b)

    with pytest.raises(HTTPException) as exc_info:
        await svc_b.modificar_aviso(
            aviso.id,
            ActualizarAvisoRequest(activo=False),
            actor_b,
        )
    assert exc_info.value.status_code == 404

    # Cleanup
    from app.repositories.aviso_repository import AvisoRepository
    repo_a = AvisoRepository(session=svc_session, tenant_id=tid_a)
    av = await repo_a.get_by_id(aviso.id)
    if av:
        await repo_a.delete(av)
    await svc_session.commit()


# ---------------------------------------------------------------------------
# 5.3 / 5.4 — Acknowledgment
# ---------------------------------------------------------------------------

@pytest.mark.asyncio(loop_scope="session")
async def test_ack_visible_aviso(svc_session):
    """5.3 RED: ack visible in-window aviso → AcknowledgmentAviso created."""
    from app.schemas.aviso import CrearAvisoRequest
    from app.models.aviso import AvisoAlcance, AvisoSeveridad

    tid = uuid.uuid4()
    await _create_tenant(svc_session, tid, f"SvcAck_{tid.hex[:4]}")
    usuario = await _create_usuario(svc_session, tid, "ack_u")
    await svc_session.commit()

    inicio, fin = _window()
    actor = _actor(tid, usuario.id)
    svc = _make_service(svc_session, tid)

    req = CrearAvisoRequest(
        alcance=AvisoAlcance.Global,
        severidad=AvisoSeveridad.Info,
        titulo="Ack test",
        cuerpo="Body",
        inicio_en=inicio,
        fin_en=fin,
        requiere_ack=True,
    )
    aviso = await svc.publicar_aviso(req, _actor(tid, uuid.uuid4()))

    result = await svc.acknowledger_aviso(aviso.id, actor)
    assert result.usuario_id == usuario.id
    assert result.aviso_id == aviso.id
    assert result.confirmado_at is not None

    # Cleanup
    from app.repositories.aviso_repository import AvisoRepository, AcknowledgmentRepository
    ack_repo = AcknowledgmentRepository(session=svc_session, tenant_id=tid)
    ack = await ack_repo.get_by_id(result.id)
    if ack:
        await ack_repo.delete(ack)
    aviso_repo = AvisoRepository(session=svc_session, tenant_id=tid)
    av = await aviso_repo.get_by_id(aviso.id)
    if av:
        await aviso_repo.delete(av)
    await svc_session.commit()


@pytest.mark.asyncio(loop_scope="session")
async def test_ack_idempotent_no_duplicate(svc_session):
    """5.3 GREEN: ack same aviso twice → exactly one AcknowledgmentAviso."""
    from app.schemas.aviso import CrearAvisoRequest
    from app.models.aviso import AvisoAlcance, AvisoSeveridad
    from sqlalchemy import select
    from app.models.aviso import AcknowledgmentAviso

    tid = uuid.uuid4()
    await _create_tenant(svc_session, tid, f"SvcIdem_{tid.hex[:4]}")
    usuario = await _create_usuario(svc_session, tid, "idem_u")
    await svc_session.commit()

    inicio, fin = _window()
    actor = _actor(tid, usuario.id)
    svc = _make_service(svc_session, tid)

    req = CrearAvisoRequest(
        alcance=AvisoAlcance.Global,
        severidad=AvisoSeveridad.Info,
        titulo="Idem test",
        cuerpo="Body",
        inicio_en=inicio,
        fin_en=fin,
        requiere_ack=True,
    )
    aviso = await svc.publicar_aviso(req, _actor(tid, uuid.uuid4()))

    # Ack twice
    await svc.acknowledger_aviso(aviso.id, actor)
    await svc.acknowledger_aviso(aviso.id, actor)

    stmt = select(AcknowledgmentAviso).where(
        AcknowledgmentAviso.tenant_id == tid,
        AcknowledgmentAviso.aviso_id == aviso.id,
        AcknowledgmentAviso.usuario_id == usuario.id,
        AcknowledgmentAviso.deleted_at.is_(None),
    )
    r = await svc_session.execute(stmt)
    acks = r.scalars().all()
    assert len(acks) == 1

    # Cleanup
    from app.repositories.aviso_repository import AvisoRepository, AcknowledgmentRepository
    ack_repo = AcknowledgmentRepository(session=svc_session, tenant_id=tid)
    for ack in acks:
        await ack_repo.delete(ack)
    aviso_repo = AvisoRepository(session=svc_session, tenant_id=tid)
    av = await aviso_repo.get_by_id(aviso.id)
    if av:
        await aviso_repo.delete(av)
    await svc_session.commit()


@pytest.mark.asyncio(loop_scope="session")
async def test_ack_inactive_aviso_raises_403(svc_session):
    """5.3 TRIANGULATE: cannot ack inactive aviso → 403/404."""
    from app.schemas.aviso import CrearAvisoRequest
    from app.models.aviso import AvisoAlcance, AvisoSeveridad

    tid = uuid.uuid4()
    await _create_tenant(svc_session, tid, f"SvcInAck_{tid.hex[:4]}")
    usuario = await _create_usuario(svc_session, tid, "inactive_u")
    await svc_session.commit()

    inicio, fin = _window()
    actor_pub = _actor(tid, uuid.uuid4())
    actor_u = _actor(tid, usuario.id)
    svc = _make_service(svc_session, tid)

    req = CrearAvisoRequest(
        alcance=AvisoAlcance.Global,
        severidad=AvisoSeveridad.Info,
        titulo="Inactive ack",
        cuerpo="Body",
        inicio_en=inicio,
        fin_en=fin,
        requiere_ack=True,
        activo=False,  # inactive
    )
    aviso = await svc.publicar_aviso(req, actor_pub)

    with pytest.raises(HTTPException) as exc_info:
        await svc.acknowledger_aviso(aviso.id, actor_u)
    assert exc_info.value.status_code in (403, 404)

    # Cleanup
    from app.repositories.aviso_repository import AvisoRepository
    repo = AvisoRepository(session=svc_session, tenant_id=tid)
    av = await repo.get_by_id(aviso.id)
    if av:
        await repo.delete(av)
    await svc_session.commit()


# ---------------------------------------------------------------------------
# 5.5 — Feed / pending with derived counters
# ---------------------------------------------------------------------------

@pytest.mark.asyncio(loop_scope="session")
async def test_listar_feed_includes_ack_count(svc_session):
    """5.5 RED+GREEN: feed items include derived ack_count."""
    from app.schemas.aviso import CrearAvisoRequest
    from app.models.aviso import AvisoAlcance, AvisoSeveridad

    tid = uuid.uuid4()
    await _create_tenant(svc_session, tid, f"SvcFeed_{tid.hex[:4]}")
    usuario = await _create_usuario(svc_session, tid, "feed_u")
    await svc_session.commit()

    inicio, fin = _window()
    actor = _actor(tid, usuario.id)
    svc = _make_service(svc_session, tid)

    req = CrearAvisoRequest(
        alcance=AvisoAlcance.Global,
        severidad=AvisoSeveridad.Info,
        titulo="Feed count",
        cuerpo="Body",
        inicio_en=inicio,
        fin_en=fin,
        requiere_ack=True,
    )
    aviso = await svc.publicar_aviso(req, _actor(tid, uuid.uuid4()))

    # No acks yet → count = 0
    feed_before = await svc.listar_feed(
        usuario_id=usuario.id, roles=["COORDINADOR"], cohorte_id=None, actor=actor
    )
    item_before = next((x for x in feed_before if x.id == aviso.id), None)
    assert item_before is not None
    assert item_before.ack_count == 0

    # Ack once
    await svc.acknowledger_aviso(aviso.id, actor)

    feed_after = await svc.listar_feed(
        usuario_id=usuario.id, roles=["COORDINADOR"], cohorte_id=None, actor=actor
    )
    item_after = next((x for x in feed_after if x.id == aviso.id), None)
    assert item_after is not None
    assert item_after.ack_count == 1

    # Cleanup
    from app.repositories.aviso_repository import AvisoRepository, AcknowledgmentRepository
    ack_repo = AcknowledgmentRepository(session=svc_session, tenant_id=tid)
    from sqlalchemy import select
    from app.models.aviso import AcknowledgmentAviso
    stmt = select(AcknowledgmentAviso).where(
        AcknowledgmentAviso.tenant_id == tid,
        AcknowledgmentAviso.aviso_id == aviso.id,
        AcknowledgmentAviso.deleted_at.is_(None),
    )
    r = await svc_session.execute(stmt)
    for ack in r.scalars().all():
        await ack_repo.delete(ack)
    aviso_repo = AvisoRepository(session=svc_session, tenant_id=tid)
    av = await aviso_repo.get_by_id(aviso.id)
    if av:
        await aviso_repo.delete(av)
    await svc_session.commit()
