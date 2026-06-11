"""
test_tarea_service.py — TDD tests for C-16 TareaService.

Tasks 5.1–5.9:
    5.1 RED: publicar/asignar sets Pendiente, resolves identity from session, TAREA_ASIGNAR audit.
    5.3 RED: cambiar_estado covers every legal/illegal/no-op transition (D3 matrix).
    5.5 RED: delegar reassigns, overwrites asignado_por, TAREA_DELEGAR audit, system comment.
    5.7 RED: ownership enforcement (D7) — without gestionar, only asignado_a/asignado_por.
    5.9 TRIANGULATE: edge cases (delegate across tenant → 404, comment on foreign tarea → 403).

DB real: activia_trace_test. Sin mocks.
"""
import asyncio
import uuid

import pytest
import pytest_asyncio
from dotenv import load_dotenv
import os
from fastapi import HTTPException
from sqlalchemy import select, text
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

async def _create_tenant(session, tid, name):
    from app.models.tenant import Tenant, TenantEstado
    t = Tenant(id=tid, nombre=name, estado=TenantEstado.ACTIVO)
    session.add(t)
    await session.flush()
    return t


async def _create_usuario(session, tid, suffix=""):
    from app.models.usuario import Usuario, UsuarioEstado
    from app.core.security.passwords import email_lookup_hash as _hash
    email = f"svc_tarea_{suffix}_{uuid.uuid4().hex[:6]}@test.com"
    u = Usuario(
        tenant_id=tid, email_encrypted=email, email_hash=_hash(email),
        nombre="Test", apellidos=suffix, estado=UsuarioEstado.activo,
    )
    session.add(u)
    await session.flush()
    return u


def _actor(tid, uid, roles=None):
    """Actor representing a COORDINADOR/ADMIN with tareas:gestionar context."""
    return CurrentUser(user_id=uid, tenant_id=tid, roles=roles or ["COORDINADOR"])


def _actor_docente(tid, uid):
    """Actor representing a docente WITHOUT tareas:gestionar."""
    return CurrentUser(user_id=uid, tenant_id=tid, roles=["PROFESOR"])


def _make_service(session, tid):
    from app.repositories.tarea_repository import TareaRepository, ComentarioTareaRepository
    from app.repositories.audit_repository import AuditRepository
    from app.repositories.mensajeria_repository import MensajeriaRepository
    from app.services.tarea_service import TareaService
    return TareaService(
        tarea_repo=TareaRepository(session=session, tenant_id=tid),
        comentario_repo=ComentarioTareaRepository(session=session, tenant_id=tid),
        audit_repo=AuditRepository(session=session, tenant_id=tid),
        mensajeria_repo=MensajeriaRepository(session=session, tenant_id=tid),
    )


async def _cleanup_tarea(session, tid, tarea_id):
    from app.repositories.tarea_repository import TareaRepository
    repo = TareaRepository(session=session, tenant_id=tid)
    t = await repo.get_by_id(tarea_id, include_deleted=True)
    if t and t.deleted_at is None:
        await repo.delete(t)


# ---------------------------------------------------------------------------
# 5.1 / 5.2 — publicar + TAREA_ASIGNAR audit
# ---------------------------------------------------------------------------

@pytest.mark.asyncio(loop_scope="session")
async def test_publicar_crea_tarea_pendiente(svc_session):
    """5.1 RED: publicar sets estado=Pendiente, tenant_id and asignado_por from session."""
    from app.models.tarea import TareaEstado
    from app.schemas.tarea import TareaCreate

    tid = uuid.uuid4()
    await _create_tenant(svc_session, tid, f"SvcPubT_{tid.hex[:4]}")
    docente = await _create_usuario(svc_session, tid, "pub_docente")
    coord = await _create_usuario(svc_session, tid, "pub_coord")
    await svc_session.commit()

    actor = _actor(tid, coord.id)
    svc = _make_service(svc_session, tid)

    req = TareaCreate(asignado_a=docente.id, descripcion="Revisar actas")
    tarea = await svc.publicar(req, actor)

    assert tarea.estado == TareaEstado.Pendiente
    assert tarea.tenant_id == tid
    assert tarea.asignado_por == coord.id  # from JWT, not body
    assert tarea.asignado_a == docente.id

    await _cleanup_tarea(svc_session, tid, tarea.id)
    await svc_session.commit()


@pytest.mark.asyncio(loop_scope="session")
async def test_publicar_emite_audit_asignar(svc_session):
    """5.2 GREEN: publicar writes TAREA_ASIGNAR audit entry."""
    from app.models.audit import AuditAction, AuditEvent
    from app.schemas.tarea import TareaCreate

    tid = uuid.uuid4()
    await _create_tenant(svc_session, tid, f"SvcAuditT_{tid.hex[:4]}")
    docente = await _create_usuario(svc_session, tid, "audit_doc")
    coord = await _create_usuario(svc_session, tid, "audit_coord")
    await svc_session.commit()

    actor = _actor(tid, coord.id)
    svc = _make_service(svc_session, tid)

    req = TareaCreate(asignado_a=docente.id, descripcion="Para auditar")
    tarea = await svc.publicar(req, actor)

    stmt = select(AuditEvent).where(
        AuditEvent.tenant_id == tid,
        AuditEvent.accion == AuditAction.TAREA_ASIGNAR,
        AuditEvent.actor_user_id == coord.id,
    )
    r = await svc_session.execute(stmt)
    audit = r.scalar_one_or_none()
    assert audit is not None
    assert str(tarea.id) in (audit.entidad_id or "")

    await _cleanup_tarea(svc_session, tid, tarea.id)
    await svc_session.commit()


# ---------------------------------------------------------------------------
# 5.3 / 5.4 — cambiar_estado + D3 matrix
# ---------------------------------------------------------------------------

@pytest.mark.asyncio(loop_scope="session")
async def test_cambiar_estado_legal_transitions(svc_session):
    """5.3 RED: every legal transition succeeds with TAREA_CAMBIAR_ESTADO audit."""
    from app.models.tarea import TareaEstado
    from app.models.audit import AuditAction, AuditEvent
    from app.schemas.tarea import TareaCreate

    tid = uuid.uuid4()
    await _create_tenant(svc_session, tid, f"SvcEstT_{tid.hex[:4]}")
    docente = await _create_usuario(svc_session, tid, "est_doc")
    coord = await _create_usuario(svc_session, tid, "est_coord")
    await svc_session.commit()

    actor = _actor(tid, coord.id)
    actor_docente = _actor_docente(tid, docente.id)
    svc = _make_service(svc_session, tid)

    req = TareaCreate(asignado_a=docente.id, descripcion="Transicion legal")
    tarea = await svc.publicar(req, actor)
    assert tarea.estado == TareaEstado.Pendiente

    # Pendiente → EnProgreso (asignado_a can do it without gestionar)
    tarea = await svc.cambiar_estado(tarea.id, TareaEstado.EnProgreso, actor_docente, has_gestionar=False)
    assert tarea.estado == TareaEstado.EnProgreso

    # EnProgreso → Resuelta
    tarea = await svc.cambiar_estado(tarea.id, TareaEstado.Resuelta, actor_docente, has_gestionar=False)
    assert tarea.estado == TareaEstado.Resuelta

    # Resuelta → EnProgreso (reopen)
    tarea = await svc.cambiar_estado(tarea.id, TareaEstado.EnProgreso, actor, has_gestionar=True)
    assert tarea.estado == TareaEstado.EnProgreso

    # EnProgreso → Cancelada
    tarea = await svc.cambiar_estado(tarea.id, TareaEstado.Cancelada, actor, has_gestionar=True)
    assert tarea.estado == TareaEstado.Cancelada

    # Verify audit entries were created
    stmt = select(AuditEvent).where(
        AuditEvent.tenant_id == tid,
        AuditEvent.accion == AuditAction.TAREA_CAMBIAR_ESTADO,
    )
    r = await svc_session.execute(stmt)
    audits = r.scalars().all()
    assert len(audits) >= 4

    await _cleanup_tarea(svc_session, tid, tarea.id)
    await svc_session.commit()


@pytest.mark.asyncio(loop_scope="session")
async def test_cambiar_estado_pendiente_to_cancelada(svc_session):
    """5.3 RED: Pendiente → Cancelada is legal."""
    from app.models.tarea import TareaEstado
    from app.schemas.tarea import TareaCreate

    tid = uuid.uuid4()
    await _create_tenant(svc_session, tid, f"SvcCancT_{tid.hex[:4]}")
    docente = await _create_usuario(svc_session, tid, "canc_doc")
    coord = await _create_usuario(svc_session, tid, "canc_coord")
    await svc_session.commit()

    actor = _actor(tid, coord.id)
    svc = _make_service(svc_session, tid)

    req = TareaCreate(asignado_a=docente.id, descripcion="A cancelar")
    tarea = await svc.publicar(req, actor)

    tarea = await svc.cambiar_estado(tarea.id, TareaEstado.Cancelada, actor, has_gestionar=True)
    assert tarea.estado == TareaEstado.Cancelada

    await _cleanup_tarea(svc_session, tid, tarea.id)
    await svc_session.commit()


@pytest.mark.asyncio(loop_scope="session")
async def test_cambiar_estado_illegal_transitions_return_409(svc_session):
    """5.3 RED: each illegal transition returns HTTP 409."""
    from app.models.tarea import TareaEstado
    from app.schemas.tarea import TareaCreate

    tid = uuid.uuid4()
    await _create_tenant(svc_session, tid, f"SvcIllT_{tid.hex[:4]}")
    docente = await _create_usuario(svc_session, tid, "ill_doc")
    coord = await _create_usuario(svc_session, tid, "ill_coord")
    await svc_session.commit()

    actor = _actor(tid, coord.id)
    svc = _make_service(svc_session, tid)

    # Resuelta → Pendiente (illegal per D3)
    req = TareaCreate(asignado_a=docente.id, descripcion="Para transicion ilegal")
    tarea = await svc.publicar(req, actor)
    tarea = await svc.cambiar_estado(tarea.id, TareaEstado.Resuelta, actor, has_gestionar=True)
    assert tarea.estado == TareaEstado.Resuelta

    with pytest.raises(HTTPException) as exc_info:
        await svc.cambiar_estado(tarea.id, TareaEstado.Pendiente, actor, has_gestionar=True)
    assert exc_info.value.status_code == 409

    # Cancelada → EnProgreso (terminal-final, D3)
    req2 = TareaCreate(asignado_a=docente.id, descripcion="A cancelar luego")
    tarea2 = await svc.publicar(req2, actor)
    tarea2 = await svc.cambiar_estado(tarea2.id, TareaEstado.Cancelada, actor, has_gestionar=True)

    with pytest.raises(HTTPException) as exc_info2:
        await svc.cambiar_estado(tarea2.id, TareaEstado.EnProgreso, actor, has_gestionar=True)
    assert exc_info2.value.status_code == 409

    for t_id in [tarea.id, tarea2.id]:
        await _cleanup_tarea(svc_session, tid, t_id)
    await svc_session.commit()


@pytest.mark.asyncio(loop_scope="session")
async def test_cambiar_estado_noop_returns_409(svc_session):
    """5.3 RED: same-state transition (no-op) returns 409."""
    from app.models.tarea import TareaEstado
    from app.schemas.tarea import TareaCreate

    tid = uuid.uuid4()
    await _create_tenant(svc_session, tid, f"SvcNoop_{tid.hex[:4]}")
    docente = await _create_usuario(svc_session, tid, "noop_doc")
    coord = await _create_usuario(svc_session, tid, "noop_coord")
    await svc_session.commit()

    actor = _actor(tid, coord.id)
    svc = _make_service(svc_session, tid)

    req = TareaCreate(asignado_a=docente.id, descripcion="No-op test")
    tarea = await svc.publicar(req, actor)

    with pytest.raises(HTTPException) as exc_info:
        await svc.cambiar_estado(tarea.id, TareaEstado.Pendiente, actor, has_gestionar=True)
    assert exc_info.value.status_code == 409

    await _cleanup_tarea(svc_session, tid, tarea.id)
    await svc_session.commit()


# ---------------------------------------------------------------------------
# 5.5 / 5.6 — delegar
# ---------------------------------------------------------------------------

@pytest.mark.asyncio(loop_scope="session")
async def test_delegar_reassigns_and_emits_audit_and_comment(svc_session):
    """5.5 RED: delegar reassigns, overwrites asignado_por, TAREA_DELEGAR audit, system comment."""
    from app.models.audit import AuditAction, AuditEvent
    from app.models.tarea import ComentarioTarea
    from app.schemas.tarea import TareaCreate

    tid = uuid.uuid4()
    await _create_tenant(svc_session, tid, f"SvcDelT_{tid.hex[:4]}")
    docente1 = await _create_usuario(svc_session, tid, "del_d1")
    docente2 = await _create_usuario(svc_session, tid, "del_d2")
    coord1 = await _create_usuario(svc_session, tid, "del_coord1")
    coord2 = await _create_usuario(svc_session, tid, "del_coord2")
    await svc_session.commit()

    actor = _actor(tid, coord1.id)
    actor_delegante = _actor(tid, coord2.id)
    svc = _make_service(svc_session, tid)

    req = TareaCreate(asignado_a=docente1.id, descripcion="Para delegar")
    tarea = await svc.publicar(req, actor)
    assert tarea.asignado_a == docente1.id

    tarea = await svc.delegar(tarea.id, docente2.id, actor_delegante)

    assert tarea.asignado_a == docente2.id
    assert tarea.asignado_por == coord2.id

    # Verify TAREA_DELEGAR audit
    stmt = select(AuditEvent).where(
        AuditEvent.tenant_id == tid,
        AuditEvent.accion == AuditAction.TAREA_DELEGAR,
        AuditEvent.actor_user_id == coord2.id,
    )
    r = await svc_session.execute(stmt)
    audit = r.scalar_one_or_none()
    assert audit is not None
    assert audit.before is not None
    assert audit.after is not None

    # Verify system comment
    stmt2 = select(ComentarioTarea).where(
        ComentarioTarea.tenant_id == tid,
        ComentarioTarea.tarea_id == tarea.id,
        ComentarioTarea.es_sistema.is_(True),
        ComentarioTarea.deleted_at.is_(None),
    )
    r2 = await svc_session.execute(stmt2)
    sys_comment = r2.scalar_one_or_none()
    assert sys_comment is not None
    assert "delega" in sys_comment.cuerpo.lower() or "asign" in sys_comment.cuerpo.lower()

    await _cleanup_tarea(svc_session, tid, tarea.id)
    await svc_session.commit()


# ---------------------------------------------------------------------------
# 5.7 / 5.8 — Ownership enforcement (D7)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio(loop_scope="session")
async def test_cambiar_estado_sin_permiso_sin_ownership_returns_403(svc_session):
    """5.7 RED: without tareas:gestionar and not asignado_a/asignado_por → 403."""
    from app.models.tarea import TareaEstado
    from app.schemas.tarea import TareaCreate

    tid = uuid.uuid4()
    await _create_tenant(svc_session, tid, f"SvcOwn1_{tid.hex[:4]}")
    docente = await _create_usuario(svc_session, tid, "own_doc1")
    coord = await _create_usuario(svc_session, tid, "own_coord1")
    tercero = await _create_usuario(svc_session, tid, "own_tercero")
    await svc_session.commit()

    actor = _actor(tid, coord.id)
    svc = _make_service(svc_session, tid)

    req = TareaCreate(asignado_a=docente.id, descripcion="Ownership test")
    tarea = await svc.publicar(req, actor)

    # Tercero is NOT asignado_a/asignado_por and has no gestionar
    actor_tercero = _actor_docente(tid, tercero.id)
    with pytest.raises(HTTPException) as exc_info:
        await svc.cambiar_estado(tarea.id, TareaEstado.EnProgreso, actor_tercero, has_gestionar=False)
    assert exc_info.value.status_code == 403

    await _cleanup_tarea(svc_session, tid, tarea.id)
    await svc_session.commit()


@pytest.mark.asyncio(loop_scope="session")
async def test_cambiar_estado_asignado_a_puede_sin_permiso(svc_session):
    """5.7 RED: asignado_a can change estado without tareas:gestionar."""
    from app.models.tarea import TareaEstado
    from app.schemas.tarea import TareaCreate

    tid = uuid.uuid4()
    await _create_tenant(svc_session, tid, f"SvcOwn2_{tid.hex[:4]}")
    docente = await _create_usuario(svc_session, tid, "own_doc2")
    coord = await _create_usuario(svc_session, tid, "own_coord2")
    await svc_session.commit()

    actor = _actor(tid, coord.id)
    svc = _make_service(svc_session, tid)

    req = TareaCreate(asignado_a=docente.id, descripcion="Self-service")
    tarea = await svc.publicar(req, actor)

    # docente is asignado_a → can change estado without gestionar
    actor_docente = _actor_docente(tid, docente.id)
    tarea = await svc.cambiar_estado(tarea.id, TareaEstado.EnProgreso, actor_docente, has_gestionar=False)
    assert tarea.estado == TareaEstado.EnProgreso

    await _cleanup_tarea(svc_session, tid, tarea.id)
    await svc_session.commit()


@pytest.mark.asyncio(loop_scope="session")
async def test_comentar_sin_permiso_tercero_returns_403(svc_session):
    """5.7 RED: without tareas:gestionar, comentar on foreign tarea → 403."""
    from app.schemas.tarea import TareaCreate, ComentarioTareaCreate

    tid = uuid.uuid4()
    await _create_tenant(svc_session, tid, f"SvcCom1_{tid.hex[:4]}")
    docente = await _create_usuario(svc_session, tid, "com_doc1")
    coord = await _create_usuario(svc_session, tid, "com_coord1")
    tercero = await _create_usuario(svc_session, tid, "com_tercero1")
    await svc_session.commit()

    actor = _actor(tid, coord.id)
    svc = _make_service(svc_session, tid)

    req = TareaCreate(asignado_a=docente.id, descripcion="Para comentar")
    tarea = await svc.publicar(req, actor)

    actor_tercero = _actor_docente(tid, tercero.id)
    with pytest.raises(HTTPException) as exc_info:
        await svc.comentar(tarea.id, ComentarioTareaCreate(cuerpo="Comentario"), actor_tercero, has_gestionar=False)
    assert exc_info.value.status_code == 403

    await _cleanup_tarea(svc_session, tid, tarea.id)
    await svc_session.commit()


@pytest.mark.asyncio(loop_scope="session")
async def test_listar_mias_svc(svc_session):
    """5.8 GREEN: listar_mias via service returns only caller's tareas."""
    from app.schemas.tarea import TareaCreate

    tid = uuid.uuid4()
    await _create_tenant(svc_session, tid, f"SvcMias_{tid.hex[:4]}")
    docente = await _create_usuario(svc_session, tid, "svc_mias_doc")
    otro = await _create_usuario(svc_session, tid, "svc_mias_otro")
    coord = await _create_usuario(svc_session, tid, "svc_mias_coord")
    await svc_session.commit()

    actor = _actor(tid, coord.id)
    svc = _make_service(svc_session, tid)

    t1 = await svc.publicar(TareaCreate(asignado_a=docente.id, descripcion="Mía"), actor)
    t2 = await svc.publicar(TareaCreate(asignado_a=otro.id, descripcion="Ajena"), actor)

    actor_docente = _actor_docente(tid, docente.id)
    mias = await svc.listar_mias(actor_docente)
    mias_ids = {t.id for t in mias}
    assert t1.id in mias_ids
    assert t2.id not in mias_ids

    for t_id in [t1.id, t2.id]:
        await _cleanup_tarea(svc_session, tid, t_id)
    await svc_session.commit()


# ---------------------------------------------------------------------------
# 5.9 TRIANGULATE — edge cases
# ---------------------------------------------------------------------------

@pytest.mark.asyncio(loop_scope="session")
async def test_delegar_otro_tenant_returns_404(svc_session):
    """5.9 TRIANGULATE: delegate a tarea from another tenant → 404."""
    tid_a = uuid.uuid4()
    tid_b = uuid.uuid4()
    await _create_tenant(svc_session, tid_a, f"SvcDelTA_{tid_a.hex[:4]}")
    await _create_tenant(svc_session, tid_b, f"SvcDelTB_{tid_b.hex[:4]}")
    doc_a = await _create_usuario(svc_session, tid_a, "del_cross_a")
    coord_a = await _create_usuario(svc_session, tid_a, "del_cross_coord_a")
    doc_b = await _create_usuario(svc_session, tid_b, "del_cross_b")
    coord_b = await _create_usuario(svc_session, tid_b, "del_cross_coord_b")
    await svc_session.commit()

    actor_a = _actor(tid_a, coord_a.id)
    svc_a = _make_service(svc_session, tid_a)

    from app.schemas.tarea import TareaCreate
    tarea_a = await svc_a.publicar(TareaCreate(asignado_a=doc_a.id, descripcion="Tarea en A"), actor_a)

    # Tenant B tries to delegate Tenant A's tarea
    actor_b = _actor(tid_b, coord_b.id)
    svc_b = _make_service(svc_session, tid_b)
    with pytest.raises(HTTPException) as exc_info:
        await svc_b.delegar(tarea_a.id, doc_b.id, actor_b)
    assert exc_info.value.status_code == 404

    await _cleanup_tarea(svc_session, tid_a, tarea_a.id)
    await svc_session.commit()


@pytest.mark.asyncio(loop_scope="session")
async def test_comentar_foreign_tarea_returns_403(svc_session):
    """5.9 TRIANGULATE: comment on foreign tarea (not asignado) without gestionar → 403."""
    from app.schemas.tarea import TareaCreate, ComentarioTareaCreate

    tid = uuid.uuid4()
    await _create_tenant(svc_session, tid, f"SvcComFor_{tid.hex[:4]}")
    docente = await _create_usuario(svc_session, tid, "com_for_doc")
    foraneo = await _create_usuario(svc_session, tid, "com_for_foraneo")
    coord = await _create_usuario(svc_session, tid, "com_for_coord")
    await svc_session.commit()

    actor = _actor(tid, coord.id)
    svc = _make_service(svc_session, tid)

    tarea = await svc.publicar(TareaCreate(asignado_a=docente.id, descripcion="Comentario foráneo"), actor)

    actor_foraneo = _actor_docente(tid, foraneo.id)
    with pytest.raises(HTTPException) as exc_info:
        await svc.comentar(tarea.id, ComentarioTareaCreate(cuerpo="Intruso"), actor_foraneo, has_gestionar=False)
    assert exc_info.value.status_code == 403

    await _cleanup_tarea(svc_session, tid, tarea.id)
    await svc_session.commit()
