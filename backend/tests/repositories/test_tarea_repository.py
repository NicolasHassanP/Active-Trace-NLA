"""
test_tarea_repository.py — TDD tests for C-16 TareaRepository + ComentarioTareaRepository.

Tasks 4.1–4.6:
    4.1 RED: CRUD scoped to tenant; cross-tenant returns nothing.
    4.2 GREEN: TareaRepository implemented.
    4.3 RED: listar_mias + admin filter query with all branches + combinations + tenant boundary.
    4.4 GREEN: listar_mias and admin filter query implemented.
    4.5 RED+GREEN: ComentarioTareaRepository — add + list thread.
    4.6 TRIANGULATE: boundary cases (empty results, ILIKE no-match).

DB real: activia_trace_test. Sin mocks.
"""
import asyncio
import uuid
from datetime import date

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
# Module-scoped fixtures
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
    """Ensure all tables + enums exist and return a module-scoped session."""
    import app.models  # noqa: F401

    async with repo_engine.begin() as conn:
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

async def _create_tenant(session, tid, name):
    from app.models.tenant import Tenant, TenantEstado
    t = Tenant(id=tid, nombre=name, estado=TenantEstado.ACTIVO)
    session.add(t)
    await session.flush()
    return t


async def _create_materia(session, tid, suffix=""):
    from app.models.estructura import Materia, EstadoEstructura
    m = Materia(
        tenant_id=tid,
        codigo=f"M_{uuid.uuid4().hex[:6]}",
        nombre=f"Materia{suffix}",
        estado=EstadoEstructura.activa,
    )
    session.add(m)
    await session.flush()
    return m


async def _create_usuario(session, tid, suffix=""):
    from app.models.usuario import Usuario, UsuarioEstado
    from app.core.security.passwords import email_lookup_hash as _hash
    email = f"tarea_repo_{suffix}_{uuid.uuid4().hex[:6]}@test.com"
    u = Usuario(
        tenant_id=tid, email_encrypted=email, email_hash=_hash(email),
        nombre="Test", apellidos=suffix, estado=UsuarioEstado.activo,
    )
    session.add(u)
    await session.flush()
    return u


def _make_tarea_repo(session, tid):
    from app.repositories.tarea_repository import TareaRepository
    return TareaRepository(session=session, tenant_id=tid)


def _make_comentario_repo(session, tid):
    from app.repositories.tarea_repository import ComentarioTareaRepository
    return ComentarioTareaRepository(session=session, tenant_id=tid)


def _new_tarea(tid, asignado_a, asignado_por, descripcion="Tarea test", **kwargs):
    from app.models.tarea import Tarea, TareaEstado
    return Tarea(
        tenant_id=tid,
        asignado_a=asignado_a,
        asignado_por=asignado_por,
        descripcion=descripcion,
        estado=kwargs.pop("estado", TareaEstado.Pendiente),
        **kwargs,
    )


# ---------------------------------------------------------------------------
# Task 4.1 / 4.2 — CRUD scoped to tenant
# ---------------------------------------------------------------------------

@pytest.mark.asyncio(loop_scope="session")
async def test_crear_tarea_y_recuperar(repo_session):
    """4.1 RED: create tarea → same tenant can retrieve it."""
    tid = uuid.uuid4()
    await _create_tenant(repo_session, tid, f"TarCRUD_{tid.hex[:4]}")
    u1 = await _create_usuario(repo_session, tid, "asig")
    u2 = await _create_usuario(repo_session, tid, "por")
    await repo_session.commit()

    tarea = _new_tarea(tid, u1.id, u2.id, "Descripción de prueba")
    repo = _make_tarea_repo(repo_session, tid)
    tarea = await repo.add(tarea)

    fetched = await repo.get_by_id(tarea.id)
    assert fetched is not None
    assert fetched.id == tarea.id
    assert fetched.tenant_id == tid
    assert fetched.asignado_a == u1.id
    assert fetched.asignado_por == u2.id

    await repo.delete(fetched)
    await repo_session.commit()


@pytest.mark.asyncio(loop_scope="session")
async def test_tarea_cross_tenant_returns_nothing(repo_session):
    """4.1 TRIANGULATE: tarea from tenant A is invisible to tenant B."""
    tid_a = uuid.uuid4()
    tid_b = uuid.uuid4()
    await _create_tenant(repo_session, tid_a, f"TarCrossA_{tid_a.hex[:4]}")
    await _create_tenant(repo_session, tid_b, f"TarCrossB_{tid_b.hex[:4]}")
    u_a = await _create_usuario(repo_session, tid_a, "cross_a")
    await repo_session.commit()

    tarea = _new_tarea(tid_a, u_a.id, u_a.id)
    repo_a = _make_tarea_repo(repo_session, tid_a)
    tarea = await repo_a.add(tarea)

    repo_b = _make_tarea_repo(repo_session, tid_b)
    fetched = await repo_b.get_by_id(tarea.id)
    assert fetched is None

    await repo_a.delete(tarea)
    await repo_session.commit()


@pytest.mark.asyncio(loop_scope="session")
async def test_soft_delete_hides_tarea(repo_session):
    """4.2 GREEN: soft-deleted tarea not returned in normal queries."""
    tid = uuid.uuid4()
    await _create_tenant(repo_session, tid, f"TarDel_{tid.hex[:4]}")
    u = await _create_usuario(repo_session, tid, "del_u")
    await repo_session.commit()

    tarea = _new_tarea(tid, u.id, u.id)
    repo = _make_tarea_repo(repo_session, tid)
    tarea = await repo.add(tarea)
    tarea_id = tarea.id

    await repo.delete(tarea)
    fetched = await repo.get_by_id(tarea_id)
    assert fetched is None
    await repo_session.commit()


@pytest.mark.asyncio(loop_scope="session")
async def test_update_estado_tarea(repo_session):
    """4.2 GREEN: update tarea estado using update_estado."""
    from app.models.tarea import TareaEstado
    tid = uuid.uuid4()
    await _create_tenant(repo_session, tid, f"TarUpd_{tid.hex[:4]}")
    u = await _create_usuario(repo_session, tid, "upd_u")
    await repo_session.commit()

    tarea = _new_tarea(tid, u.id, u.id, estado=TareaEstado.Pendiente)
    repo = _make_tarea_repo(repo_session, tid)
    tarea = await repo.add(tarea)

    updated = await repo.update_estado(tarea, TareaEstado.EnProgreso)
    assert updated.estado == TareaEstado.EnProgreso

    await repo.delete(updated)
    await repo_session.commit()


# ---------------------------------------------------------------------------
# Task 4.3 / 4.4 — listar_mias + admin filter query
# ---------------------------------------------------------------------------

@pytest.mark.asyncio(loop_scope="session")
async def test_listar_mias_returns_only_assigned(repo_session):
    """4.3 RED: listar_mias returns only tareas where asignado_a == caller."""
    from app.models.tarea import TareaEstado
    tid = uuid.uuid4()
    await _create_tenant(repo_session, tid, f"TarMias_{tid.hex[:4]}")
    u1 = await _create_usuario(repo_session, tid, "mias_u1")
    u2 = await _create_usuario(repo_session, tid, "mias_u2")
    await repo_session.commit()

    # u1 has 2 tareas, u2 has 1
    repo = _make_tarea_repo(repo_session, tid)
    t1 = await repo.add(_new_tarea(tid, u1.id, u2.id, "Tarea de u1 #1"))
    t2 = await repo.add(_new_tarea(tid, u1.id, u2.id, "Tarea de u1 #2"))
    t3 = await repo.add(_new_tarea(tid, u2.id, u1.id, "Tarea de u2"))

    mias = await repo.listar_mias(u1.id)
    mias_ids = {t.id for t in mias}
    assert t1.id in mias_ids
    assert t2.id in mias_ids
    assert t3.id not in mias_ids

    for t in [t1, t2, t3]:
        await repo.delete(t)
    await repo_session.commit()


@pytest.mark.asyncio(loop_scope="session")
async def test_listar_mias_excludes_soft_deleted(repo_session):
    """4.3 RED: listar_mias excludes soft-deleted tareas."""
    tid = uuid.uuid4()
    await _create_tenant(repo_session, tid, f"TarMiasDel_{tid.hex[:4]}")
    u = await _create_usuario(repo_session, tid, "mias_del_u")
    await repo_session.commit()

    repo = _make_tarea_repo(repo_session, tid)
    t1 = await repo.add(_new_tarea(tid, u.id, u.id, "Activa"))
    t2 = await repo.add(_new_tarea(tid, u.id, u.id, "Soft-deleted"))
    await repo.delete(t2)

    mias = await repo.listar_mias(u.id)
    mias_ids = {t.id for t in mias}
    assert t1.id in mias_ids
    assert t2.id not in mias_ids

    await repo.delete(t1)
    await repo_session.commit()


@pytest.mark.asyncio(loop_scope="session")
async def test_listar_mias_tenant_boundary(repo_session):
    """4.3 RED: listar_mias does not return tareas from other tenants for same user UUID."""
    tid_a = uuid.uuid4()
    tid_b = uuid.uuid4()
    await _create_tenant(repo_session, tid_a, f"MiasTA_{tid_a.hex[:4]}")
    await _create_tenant(repo_session, tid_b, f"MiasTB_{tid_b.hex[:4]}")
    u_a = await _create_usuario(repo_session, tid_a, "mias_bnd_a")
    await repo_session.commit()

    repo_a = _make_tarea_repo(repo_session, tid_a)
    repo_b = _make_tarea_repo(repo_session, tid_b)

    t_a = await repo_a.add(_new_tarea(tid_a, u_a.id, u_a.id, "Tarea en A"))

    # Tenant B sees nothing for same user UUID
    mias_b = await repo_b.listar_mias(u_a.id)
    assert len(mias_b) == 0

    await repo_a.delete(t_a)
    await repo_session.commit()


@pytest.mark.asyncio(loop_scope="session")
async def test_listar_admin_filter_asignado_a(repo_session):
    """4.3 RED: listar_admin filter by asignado_a."""
    tid = uuid.uuid4()
    await _create_tenant(repo_session, tid, f"TarAdmA_{tid.hex[:4]}")
    u1 = await _create_usuario(repo_session, tid, "adm_a1")
    u2 = await _create_usuario(repo_session, tid, "adm_a2")
    await repo_session.commit()

    repo = _make_tarea_repo(repo_session, tid)
    t1 = await repo.add(_new_tarea(tid, u1.id, u2.id, "Asignada a u1"))
    t2 = await repo.add(_new_tarea(tid, u2.id, u1.id, "Asignada a u2"))

    results = await repo.listar_admin(asignado_a=u1.id)
    ids = {t.id for t in results}
    assert t1.id in ids
    assert t2.id not in ids

    for t in [t1, t2]:
        await repo.delete(t)
    await repo_session.commit()


@pytest.mark.asyncio(loop_scope="session")
async def test_listar_admin_filter_estado(repo_session):
    """4.3 RED: listar_admin filter by estado."""
    from app.models.tarea import TareaEstado
    tid = uuid.uuid4()
    await _create_tenant(repo_session, tid, f"TarAdmE_{tid.hex[:4]}")
    u = await _create_usuario(repo_session, tid, "adm_e")
    await repo_session.commit()

    repo = _make_tarea_repo(repo_session, tid)
    t1 = await repo.add(_new_tarea(tid, u.id, u.id, "Pendiente", estado=TareaEstado.Pendiente))
    t2 = await repo.add(_new_tarea(tid, u.id, u.id, "Resuelta", estado=TareaEstado.Resuelta))

    results = await repo.listar_admin(estado=TareaEstado.Pendiente)
    ids = {t.id for t in results}
    assert t1.id in ids
    assert t2.id not in ids

    for t in [t1, t2]:
        await repo.delete(t)
    await repo_session.commit()


@pytest.mark.asyncio(loop_scope="session")
async def test_listar_admin_filter_materia(repo_session):
    """4.3 RED: listar_admin filter by materia_id."""
    tid = uuid.uuid4()
    await _create_tenant(repo_session, tid, f"TarAdmM_{tid.hex[:4]}")
    u = await _create_usuario(repo_session, tid, "adm_m")
    m1 = await _create_materia(repo_session, tid, "Mat1")
    m2 = await _create_materia(repo_session, tid, "Mat2")
    await repo_session.commit()

    repo = _make_tarea_repo(repo_session, tid)
    t1 = await repo.add(_new_tarea(tid, u.id, u.id, "Con materia 1", materia_id=m1.id))
    t2 = await repo.add(_new_tarea(tid, u.id, u.id, "Con materia 2", materia_id=m2.id))

    results = await repo.listar_admin(materia_id=m1.id)
    ids = {t.id for t in results}
    assert t1.id in ids
    assert t2.id not in ids

    for t in [t1, t2]:
        await repo.delete(t)
    await repo_session.commit()


@pytest.mark.asyncio(loop_scope="session")
async def test_listar_admin_filter_q_ilike(repo_session):
    """4.3 RED: listar_admin filter by q (ILIKE on descripcion)."""
    tid = uuid.uuid4()
    await _create_tenant(repo_session, tid, f"TarAdmQ_{tid.hex[:4]}")
    u = await _create_usuario(repo_session, tid, "adm_q")
    await repo_session.commit()

    repo = _make_tarea_repo(repo_session, tid)
    t1 = await repo.add(_new_tarea(tid, u.id, u.id, "Revisar informe mensual"))
    t2 = await repo.add(_new_tarea(tid, u.id, u.id, "Cargar notas del parcial"))

    results = await repo.listar_admin(q="informe")
    ids = {t.id for t in results}
    assert t1.id in ids
    assert t2.id not in ids

    # Case insensitive
    results2 = await repo.listar_admin(q="INFORME")
    ids2 = {t.id for t in results2}
    assert t1.id in ids2

    for t in [t1, t2]:
        await repo.delete(t)
    await repo_session.commit()


@pytest.mark.asyncio(loop_scope="session")
async def test_listar_admin_combined_filters(repo_session):
    """4.4 GREEN: listar_admin with multiple filters applied simultaneously."""
    from app.models.tarea import TareaEstado
    tid = uuid.uuid4()
    await _create_tenant(repo_session, tid, f"TarAdmComb_{tid.hex[:4]}")
    u1 = await _create_usuario(repo_session, tid, "comb_u1")
    u2 = await _create_usuario(repo_session, tid, "comb_u2")
    m = await _create_materia(repo_session, tid, "CombMat")
    await repo_session.commit()

    repo = _make_tarea_repo(repo_session, tid)
    # This tarea matches both asignado_a=u1 and estado=Pendiente
    t_match = await repo.add(_new_tarea(
        tid, u1.id, u2.id, "Coincide",
        estado=TareaEstado.Pendiente, materia_id=m.id
    ))
    # This matches asignado_a=u1 but NOT estado=Pendiente
    t_no_estado = await repo.add(_new_tarea(
        tid, u1.id, u2.id, "No estado",
        estado=TareaEstado.Resuelta, materia_id=m.id
    ))

    results = await repo.listar_admin(
        asignado_a=u1.id, estado=TareaEstado.Pendiente, materia_id=m.id
    )
    ids = {t.id for t in results}
    assert t_match.id in ids
    assert t_no_estado.id not in ids

    for t in [t_match, t_no_estado]:
        await repo.delete(t)
    await repo_session.commit()


@pytest.mark.asyncio(loop_scope="session")
async def test_listar_admin_tenant_boundary(repo_session):
    """4.4 GREEN: listar_admin does not cross tenant boundary."""
    tid_a = uuid.uuid4()
    tid_b = uuid.uuid4()
    await _create_tenant(repo_session, tid_a, f"AdmBndA_{tid_a.hex[:4]}")
    await _create_tenant(repo_session, tid_b, f"AdmBndB_{tid_b.hex[:4]}")
    u_a = await _create_usuario(repo_session, tid_a, "bnd_u_a")
    await repo_session.commit()

    repo_a = _make_tarea_repo(repo_session, tid_a)
    repo_b = _make_tarea_repo(repo_session, tid_b)

    t_a = await repo_a.add(_new_tarea(tid_a, u_a.id, u_a.id, "En tenant A"))

    results_b = await repo_b.listar_admin()
    ids_b = {t.id for t in results_b}
    assert t_a.id not in ids_b

    await repo_a.delete(t_a)
    await repo_session.commit()


# ---------------------------------------------------------------------------
# Task 4.5 — ComentarioTareaRepository
# ---------------------------------------------------------------------------

@pytest.mark.asyncio(loop_scope="session")
async def test_agregar_comentario_y_listar_hilo(repo_session):
    """4.5 RED+GREEN: add comment + list thread ordered by created_at."""
    tid = uuid.uuid4()
    await _create_tenant(repo_session, tid, f"ComHilo_{tid.hex[:4]}")
    u = await _create_usuario(repo_session, tid, "hilo_u")
    await repo_session.commit()

    tarea_repo = _make_tarea_repo(repo_session, tid)
    tarea = await tarea_repo.add(_new_tarea(tid, u.id, u.id, "Tarea con hilo"))

    comentario_repo = _make_comentario_repo(repo_session, tid)
    c1 = await comentario_repo.add_comentario(tarea.id, u.id, "Primer comentario")
    c2 = await comentario_repo.add_comentario(tarea.id, u.id, "Segundo comentario")

    hilo = await comentario_repo.listar_hilo(tarea.id)
    assert len(hilo) >= 2
    ids = [c.id for c in hilo]
    assert c1.id in ids
    assert c2.id in ids

    # Verify ordering by created_at (ascending)
    idx_c1 = ids.index(c1.id)
    idx_c2 = ids.index(c2.id)
    assert idx_c1 < idx_c2

    await tarea_repo.delete(tarea)
    await repo_session.commit()


@pytest.mark.asyncio(loop_scope="session")
async def test_comentario_soft_deleted_excluded_from_hilo(repo_session):
    """4.5 GREEN: soft-deleted comments are excluded from the thread."""
    tid = uuid.uuid4()
    await _create_tenant(repo_session, tid, f"ComDel_{tid.hex[:4]}")
    u = await _create_usuario(repo_session, tid, "com_del_u")
    await repo_session.commit()

    tarea_repo = _make_tarea_repo(repo_session, tid)
    tarea = await tarea_repo.add(_new_tarea(tid, u.id, u.id, "Tarea con comentario"))

    comentario_repo = _make_comentario_repo(repo_session, tid)
    c_active = await comentario_repo.add_comentario(tarea.id, u.id, "Activo")
    c_deleted = await comentario_repo.add_comentario(tarea.id, u.id, "Borrado")

    # Soft delete the second comment
    await comentario_repo.delete(c_deleted)

    hilo = await comentario_repo.listar_hilo(tarea.id)
    ids = [c.id for c in hilo]
    assert c_active.id in ids
    assert c_deleted.id not in ids

    await tarea_repo.delete(tarea)
    await repo_session.commit()


@pytest.mark.asyncio(loop_scope="session")
async def test_comentario_tenant_scoped(repo_session):
    """4.5 TRIANGULATE: comentarios from another tenant not visible."""
    tid_a = uuid.uuid4()
    tid_b = uuid.uuid4()
    await _create_tenant(repo_session, tid_a, f"ComTenA_{tid_a.hex[:4]}")
    await _create_tenant(repo_session, tid_b, f"ComTenB_{tid_b.hex[:4]}")
    u_a = await _create_usuario(repo_session, tid_a, "com_ten_a")
    await repo_session.commit()

    repo_a = _make_tarea_repo(repo_session, tid_a)
    tarea_a = await repo_a.add(_new_tarea(tid_a, u_a.id, u_a.id, "Tarea en A"))

    com_repo_a = _make_comentario_repo(repo_session, tid_a)
    await com_repo_a.add_comentario(tarea_a.id, u_a.id, "Comentario en A")

    # Tenant B tries to list the thread
    com_repo_b = _make_comentario_repo(repo_session, tid_b)
    hilo_b = await com_repo_b.listar_hilo(tarea_a.id)
    assert len(hilo_b) == 0

    await repo_a.delete(tarea_a)
    await repo_session.commit()


# ---------------------------------------------------------------------------
# Task 4.6 — TRIANGULATE: boundary cases
# ---------------------------------------------------------------------------

@pytest.mark.asyncio(loop_scope="session")
async def test_listar_mias_empty_when_no_tareas(repo_session):
    """4.6 TRIANGULATE: listar_mias returns empty list when no tareas assigned."""
    tid = uuid.uuid4()
    await _create_tenant(repo_session, tid, f"TarEmpty_{tid.hex[:4]}")
    u = await _create_usuario(repo_session, tid, "empty_u")
    await repo_session.commit()

    repo = _make_tarea_repo(repo_session, tid)
    mias = await repo.listar_mias(u.id)
    assert mias == []


@pytest.mark.asyncio(loop_scope="session")
async def test_listar_admin_ilike_no_match(repo_session):
    """4.6 TRIANGULATE: listar_admin q with no match returns empty list."""
    tid = uuid.uuid4()
    await _create_tenant(repo_session, tid, f"TarNoMatch_{tid.hex[:4]}")
    u = await _create_usuario(repo_session, tid, "no_match_u")
    await repo_session.commit()

    repo = _make_tarea_repo(repo_session, tid)
    t = await repo.add(_new_tarea(tid, u.id, u.id, "Tarea con descripcion normal"))

    results = await repo.listar_admin(q="xyzzyQQQzzz_no_existe")
    assert len(results) == 0

    await repo.delete(t)
    await repo_session.commit()


@pytest.mark.asyncio(loop_scope="session")
async def test_listar_admin_no_filters_returns_all_active(repo_session):
    """4.6 TRIANGULATE: listar_admin without filters returns all non-deleted tareas for tenant."""
    tid = uuid.uuid4()
    await _create_tenant(repo_session, tid, f"TarAll_{tid.hex[:4]}")
    u = await _create_usuario(repo_session, tid, "all_u")
    await repo_session.commit()

    repo = _make_tarea_repo(repo_session, tid)
    t1 = await repo.add(_new_tarea(tid, u.id, u.id, "Primera"))
    t2 = await repo.add(_new_tarea(tid, u.id, u.id, "Segunda"))
    t_del = await repo.add(_new_tarea(tid, u.id, u.id, "Borrada"))
    await repo.delete(t_del)

    results = await repo.listar_admin()
    ids = {t.id for t in results}
    assert t1.id in ids
    assert t2.id in ids
    assert t_del.id not in ids

    for t in [t1, t2]:
        await repo.delete(t)
    await repo_session.commit()
