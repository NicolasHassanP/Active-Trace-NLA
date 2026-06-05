"""
test_programa_repository.py — TDD RED/GREEN tests for C-17 ProgramaMateriaRepository.

Tasks 3.1–3.2:
    3.1 RED: alta tenant-scoped; get_by_id de otro tenant devuelve None; list excluye soft-deleted.
    3.2 GREEN: ProgramaMateriaRepository implementado con listar() y chequeo de duplicado activo.

DB real: activia_trace_test. Sin mocks.
"""
import asyncio
import os
import uuid
from datetime import date

import pytest
import pytest_asyncio
from dotenv import load_dotenv
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import NullPool

from app.core.database import build_session_factory

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
async def repo_engine():
    engine = create_async_engine(TEST_DATABASE_URL, poolclass=NullPool, echo=False)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture(scope="module")
async def repo_session(repo_engine):
    """Ensure schema + enums exist and return a module-scoped session."""
    import app.models  # noqa: F401

    async with repo_engine.begin() as conn:
        for stmt in [
            "DO $$ BEGIN CREATE TYPE tenant_estado AS ENUM ('activo', 'inactivo'); EXCEPTION WHEN duplicate_object THEN NULL; END $$;",
            "DO $$ BEGIN CREATE TYPE permiso_scope AS ENUM ('global', 'propio'); EXCEPTION WHEN duplicate_object THEN NULL; END $$;",
            "DO $$ BEGIN CREATE TYPE audit_action AS ENUM ('IMPERSONACION_INICIO', 'IMPERSONACION_FIN', 'AUDITORIA_CONSULTA'); EXCEPTION WHEN duplicate_object THEN NULL; END $$;",
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
            "PROGRAMA_GESTIONAR", "FECHA_ACADEMICA_GESTIONAR",
        ]:
            await conn.execute(text(
                f"DO $$ BEGIN ALTER TYPE audit_action ADD VALUE '{action}'; "
                "EXCEPTION WHEN duplicate_object THEN NULL; END $$;"
            ))

        from app.core.database import Base
        await conn.run_sync(Base.metadata.create_all, checkfirst=True)

        await conn.execute(text(
            "CREATE UNIQUE INDEX IF NOT EXISTS uq_reserva_activa_por_convocatoria "
            "ON reserva_evaluacion (tenant_id, evaluacion_id, alumno_id) "
            "WHERE estado = 'Activa' AND deleted_at IS NULL"
        ))
        await conn.execute(text(
            "CREATE UNIQUE INDEX IF NOT EXISTS ux_programa_materia_tenant_combo "
            "ON programa_materia (tenant_id, materia_id, carrera_id, cohorte_id) "
            "WHERE deleted_at IS NULL"
        ))
        await conn.execute(text(
            "CREATE UNIQUE INDEX IF NOT EXISTS ux_fecha_academica_tenant_combo "
            "ON fecha_academica (tenant_id, materia_id, cohorte_id, tipo, numero, periodo) "
            "WHERE deleted_at IS NULL"
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
# Helper functions
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
        codigo=f"PM_{uuid.uuid4().hex[:6]}",
        nombre=f"MatProg{suffix}",
        estado=EstadoEstructura.activa,
    )
    session.add(m)
    await session.flush()
    return m


async def _create_carrera(session, tid, suffix=""):
    from app.models.estructura import Carrera, EstadoEstructura
    c = Carrera(
        tenant_id=tid,
        codigo=f"CR_{uuid.uuid4().hex[:6]}",
        nombre=f"CarreraProg{suffix}",
        estado=EstadoEstructura.activa,
    )
    session.add(c)
    await session.flush()
    return c


async def _create_cohorte(session, tid, carrera_id, suffix=""):
    from app.models.estructura import Cohorte, EstadoEstructura
    from datetime import date
    c = Cohorte(
        tenant_id=tid,
        carrera_id=carrera_id,
        nombre=f"Coh{suffix}2026",
        anio=2026,
        vig_desde=date(2026, 3, 1),
        estado=EstadoEstructura.activa,
    )
    session.add(c)
    await session.flush()
    return c


def _make_repo(session, tid):
    from app.repositories.programa_repository import ProgramaMateriaRepository
    return ProgramaMateriaRepository(session=session, tenant_id=tid)


def _new_programa(tid, materia_id, carrera_id, cohorte_id, titulo="Prog Test", ref="blob://test"):
    from app.models.academico import ProgramaMateria
    return ProgramaMateria(
        tenant_id=tid,
        materia_id=materia_id,
        carrera_id=carrera_id,
        cohorte_id=cohorte_id,
        titulo=titulo,
        referencia_archivo=ref,
    )


# ---------------------------------------------------------------------------
# Task 3.1 RED — alta tenant-scoped
# ---------------------------------------------------------------------------

@pytest.mark.asyncio(loop_scope="session")
async def test_crear_programa_y_recuperar(repo_session):
    """3.1 RED: create programa → same tenant can retrieve it."""
    tid = uuid.uuid4()
    await _create_tenant(repo_session, tid, f"ProgCRUD_{tid.hex[:4]}")
    m = await _create_materia(repo_session, tid, "Crud")
    car = await _create_carrera(repo_session, tid, "Crud")
    coh = await _create_cohorte(repo_session, tid, car.id, "Crud")
    await repo_session.commit()

    repo = _make_repo(repo_session, tid)
    prog = _new_programa(tid, m.id, car.id, coh.id, "Programa TDD", "blob://tdd/1")
    prog = await repo.add(prog)

    fetched = await repo.get_by_id(prog.id)
    assert fetched is not None
    assert fetched.id == prog.id
    assert fetched.tenant_id == tid
    assert fetched.materia_id == m.id
    assert fetched.referencia_archivo == "blob://tdd/1"

    await repo.delete(fetched)
    await repo_session.commit()


@pytest.mark.asyncio(loop_scope="session")
async def test_get_by_id_cross_tenant_returns_none(repo_session):
    """3.1 RED: get_by_id from another tenant returns None."""
    tid_a = uuid.uuid4()
    tid_b = uuid.uuid4()
    await _create_tenant(repo_session, tid_a, f"ProgA_{tid_a.hex[:4]}")
    await _create_tenant(repo_session, tid_b, f"ProgB_{tid_b.hex[:4]}")
    m = await _create_materia(repo_session, tid_a, "Cross")
    car = await _create_carrera(repo_session, tid_a, "Cross")
    coh = await _create_cohorte(repo_session, tid_a, car.id, "Cross")
    await repo_session.commit()

    repo_a = _make_repo(repo_session, tid_a)
    prog = await repo_a.add(_new_programa(tid_a, m.id, car.id, coh.id))

    repo_b = _make_repo(repo_session, tid_b)
    fetched = await repo_b.get_by_id(prog.id)
    assert fetched is None

    await repo_a.delete(prog)
    await repo_session.commit()


@pytest.mark.asyncio(loop_scope="session")
async def test_list_excludes_soft_deleted(repo_session):
    """3.1 RED: list excludes soft-deleted programas."""
    tid = uuid.uuid4()
    await _create_tenant(repo_session, tid, f"ProgDel_{tid.hex[:4]}")
    m = await _create_materia(repo_session, tid, "Del")
    car = await _create_carrera(repo_session, tid, "Del")
    coh = await _create_cohorte(repo_session, tid, car.id, "Del")
    await repo_session.commit()

    repo = _make_repo(repo_session, tid)
    prog = await repo.add(_new_programa(tid, m.id, car.id, coh.id, "Para borrar"))
    prog_id = prog.id

    await repo.delete(prog)
    fetched = await repo.get_by_id(prog_id)
    assert fetched is None

    lista = await repo.list()
    ids = {p.id for p in lista}
    assert prog_id not in ids
    await repo_session.commit()


# ---------------------------------------------------------------------------
# Task 3.2 GREEN — listar con filtros y chequeo de duplicado
# ---------------------------------------------------------------------------

@pytest.mark.asyncio(loop_scope="session")
async def test_listar_filter_by_materia(repo_session):
    """3.2 GREEN: listar() filters by materia_id."""
    tid = uuid.uuid4()
    await _create_tenant(repo_session, tid, f"ProgListM_{tid.hex[:4]}")
    m1 = await _create_materia(repo_session, tid, "M1")
    m2 = await _create_materia(repo_session, tid, "M2")
    car = await _create_carrera(repo_session, tid, "ListM")
    coh = await _create_cohorte(repo_session, tid, car.id, "ListM")
    await repo_session.commit()

    repo = _make_repo(repo_session, tid)
    p1 = await repo.add(_new_programa(tid, m1.id, car.id, coh.id, "Prog M1"))
    p2 = await repo.add(_new_programa(tid, m2.id, car.id, coh.id, "Prog M2"))

    results = await repo.listar(materia_id=m1.id)
    ids = {p.id for p in results}
    assert p1.id in ids
    assert p2.id not in ids

    await repo.delete(p1)
    await repo.delete(p2)
    await repo_session.commit()


@pytest.mark.asyncio(loop_scope="session")
async def test_listar_filter_by_cohorte(repo_session):
    """3.2 GREEN: listar() filters by cohorte_id."""
    tid = uuid.uuid4()
    await _create_tenant(repo_session, tid, f"ProgListC_{tid.hex[:4]}")
    m = await _create_materia(repo_session, tid, "ListC")
    car = await _create_carrera(repo_session, tid, "ListC")
    coh1 = await _create_cohorte(repo_session, tid, car.id, "1")
    coh2 = await _create_cohorte(repo_session, tid, car.id, "2")
    await repo_session.commit()

    repo = _make_repo(repo_session, tid)

    # For coh2, we need a different carrera to avoid unique index violation on (tenant, materia, carrera, cohorte)
    car2 = await _create_carrera(repo_session, tid, "ListC2")
    await repo_session.commit()
    p1 = await repo.add(_new_programa(tid, m.id, car.id, coh1.id, "Prog C1"))
    p2 = await repo.add(_new_programa(tid, m.id, car2.id, coh2.id, "Prog C2"))

    results = await repo.listar(cohorte_id=coh1.id)
    ids = {p.id for p in results}
    assert p1.id in ids
    assert p2.id not in ids

    await repo.delete(p1)
    await repo.delete(p2)
    await repo_session.commit()


@pytest.mark.asyncio(loop_scope="session")
async def test_existe_activo_para_combo(repo_session):
    """3.2 GREEN: existe_activo_para_combo returns True when active programa exists."""
    tid = uuid.uuid4()
    await _create_tenant(repo_session, tid, f"ProgCombo_{tid.hex[:4]}")
    m = await _create_materia(repo_session, tid, "Combo")
    car = await _create_carrera(repo_session, tid, "Combo")
    coh = await _create_cohorte(repo_session, tid, car.id, "Combo")
    await repo_session.commit()

    repo = _make_repo(repo_session, tid)
    assert not await repo.existe_activo_para_combo(m.id, car.id, coh.id)

    prog = await repo.add(_new_programa(tid, m.id, car.id, coh.id))
    assert await repo.existe_activo_para_combo(m.id, car.id, coh.id)

    await repo.delete(prog)
    assert not await repo.existe_activo_para_combo(m.id, car.id, coh.id)
    await repo_session.commit()


# ---------------------------------------------------------------------------
# Task 3.5 TRIANGULATE — edge cases
# ---------------------------------------------------------------------------

@pytest.mark.asyncio(loop_scope="session")
async def test_listar_empty_tenant(repo_session):
    """3.5 TRIANGULATE: listar() returns empty list for new tenant."""
    tid = uuid.uuid4()
    await _create_tenant(repo_session, tid, f"ProgEmpty_{tid.hex[:4]}")
    await repo_session.commit()

    repo = _make_repo(repo_session, tid)
    results = await repo.listar()
    assert results == []


@pytest.mark.asyncio(loop_scope="session")
async def test_listar_tenant_isolation(repo_session):
    """3.5 TRIANGULATE: listar() never returns programas from other tenants."""
    tid_a = uuid.uuid4()
    tid_b = uuid.uuid4()
    await _create_tenant(repo_session, tid_a, f"IsolA_{tid_a.hex[:4]}")
    await _create_tenant(repo_session, tid_b, f"IsolB_{tid_b.hex[:4]}")
    m = await _create_materia(repo_session, tid_a, "Isol")
    car = await _create_carrera(repo_session, tid_a, "Isol")
    coh = await _create_cohorte(repo_session, tid_a, car.id, "Isol")
    await repo_session.commit()

    repo_a = _make_repo(repo_session, tid_a)
    prog = await repo_a.add(_new_programa(tid_a, m.id, car.id, coh.id, "En A"))

    repo_b = _make_repo(repo_session, tid_b)
    results_b = await repo_b.listar()
    ids_b = {p.id for p in results_b}
    assert prog.id not in ids_b

    await repo_a.delete(prog)
    await repo_session.commit()
