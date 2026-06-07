"""
test_alumno_repository.py — TDD task 2.4.

Tests de integración de AlumnoRepository contra DB real.
Sin mocks de DB (regla dura #4).

Casos:
    get_entradas_padron_activas:
        - alumno con entradas en versión activa → se retornan
        - alumno sin usuario_id reconciliado → no aparece en la lista
        - aislamiento por tenant: datos de otro tenant no se devuelven

    get_calificaciones_por_entradas:
        - calificaciones de entradas dadas
        - lista vacía de entrada_ids → lista vacía

    get_reservas_activas:
        - reservas Activa del alumno con contexto de materia
        - reservas Cancelada excluidas del resultado
"""
import uuid
from datetime import date
from decimal import Decimal

import pytest
import pytest_asyncio

from app.core.database import build_session_factory
from app.models.calificacion import Calificacion, CalificacionOrigen
from app.models.estructura import Carrera, Cohorte, EstadoEstructura, Materia
from app.models.evaluacion import (
    Evaluacion,
    EvaluacionTipo,
    ReservaEstado,
    ReservaEvaluacion,
    TurnoEvaluacion,
)
from app.models.padron import EntradaPadron, VersionPadron
from app.models.tenant import Tenant, TenantEstado
from app.models.usuario import Usuario, UsuarioEstado
from app.repositories.alumno_repository import AlumnoRepository


# ---------------------------------------------------------------------------
# Fixture — datos base para todos los tests de este módulo
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture(scope="module")
async def alumno_repo_data(test_engine, create_tables):
    """
    Crea un tenant con:
      - un alumno (usuario_id reconciliado)
      - una materia, cohorte, carrera
      - una versión de padrón activa con entrada vinculada al alumno
      - calificaciones sobre esa entrada
      - una reserva Activa y una Cancelada

    También crea un segundo tenant para probar aislamiento.
    """
    from app.core.security.passwords import email_lookup_hash

    factory = build_session_factory(test_engine)
    session = factory()

    # --- Tenant principal ---
    tid = uuid.uuid4()
    session.add(Tenant(id=tid, nombre=f"AlumnoRepo {tid}", estado=TenantEstado.ACTIVO))
    await session.flush()

    # --- Tenant aislado ---
    tid_otro = uuid.uuid4()
    session.add(Tenant(id=tid_otro, nombre=f"OtroTenant {tid_otro}", estado=TenantEstado.ACTIVO))
    await session.flush()

    # --- Alumno principal ---
    uid_alumno = uuid.uuid4()
    session.add(Usuario(
        id=uid_alumno, tenant_id=tid,
        email_encrypted=f"alumno_{tid}@test.com",
        email_hash=email_lookup_hash(f"alumno_{tid}@test.com"),
        nombre="Alumno", apellidos="Test", estado=UsuarioEstado.activo,
    ))

    # --- Alumno sin reconciliar (sin usuario_id en entrada) ---
    uid_sin_reconciliar = None  # usado sólo para marcar el concepto

    # --- Estructura académica ---
    carrera = Carrera(tenant_id=tid, codigo="ING01", nombre="Ingeniería Test")
    session.add(carrera)
    await session.flush()

    cohorte = Cohorte(
        tenant_id=tid, carrera_id=carrera.id,
        nombre="Cohorte 2024", anio=2024,
        vig_desde=date(2024, 3, 1), estado=EstadoEstructura.activa,
    )
    session.add(cohorte)
    materia = Materia(tenant_id=tid, codigo="MAT01", nombre="Matemáticas")
    session.add(materia)
    await session.flush()

    # --- VersionPadron activa ---
    version = VersionPadron(
        tenant_id=tid,
        materia_id=materia.id,
        cohorte_id=cohorte.id,
        activa=True,
    )
    session.add(version)
    await session.flush()

    # --- EntradaPadron vinculada al alumno ---
    entrada_alumno = EntradaPadron(
        tenant_id=tid,
        version_id=version.id,
        usuario_id=uid_alumno,
        nombre="Alumno",
        apellidos="Test",
        email_encrypted="enc:alumno@test.com",
    )
    session.add(entrada_alumno)

    # --- EntradaPadron SIN usuario_id reconciliado ---
    entrada_sin_uid = EntradaPadron(
        tenant_id=tid,
        version_id=version.id,
        usuario_id=None,  # no reconciliada
        nombre="Sin Cuenta",
        apellidos="Test",
        email_encrypted="enc:sincuenta@test.com",
    )
    session.add(entrada_sin_uid)
    await session.flush()

    # --- Calificaciones ---
    cal_aprobada = Calificacion(
        tenant_id=tid,
        entrada_padron_id=entrada_alumno.id,
        materia_id=materia.id,
        actividad="TP1",
        nota_numerica=Decimal("8.0"),
        aprobado=True,
        origen=CalificacionOrigen.Importado,
    )
    cal_sin_entrega = Calificacion(
        tenant_id=tid,
        entrada_padron_id=entrada_alumno.id,
        materia_id=materia.id,
        actividad="TP2",
        nota_numerica=None,
        nota_textual=None,
        aprobado=False,
        origen=CalificacionOrigen.Importado,
    )
    session.add_all([cal_aprobada, cal_sin_entrega])
    await session.flush()

    # --- Evaluacion + Turno + Reserva Activa ---
    evaluacion = Evaluacion(
        tenant_id=tid,
        materia_id=materia.id,
        cohorte_id=cohorte.id,
        tipo=EvaluacionTipo.Coloquio,
        instancia="1",
        dias_disponibles=7,
        cerrada=False,
    )
    session.add(evaluacion)
    await session.flush()

    turno = TurnoEvaluacion(
        tenant_id=tid,
        evaluacion_id=evaluacion.id,
        fecha=date(2026, 7, 15),
        cupo_total=20,
        franja="Mañana",
    )
    session.add(turno)
    await session.flush()

    reserva_activa = ReservaEvaluacion(
        tenant_id=tid,
        turno_id=turno.id,
        evaluacion_id=evaluacion.id,
        alumno_id=uid_alumno,
        estado=ReservaEstado.Activa,
    )
    reserva_cancelada = ReservaEvaluacion(
        tenant_id=tid,
        turno_id=turno.id,
        evaluacion_id=evaluacion.id,
        alumno_id=uid_alumno,
        estado=ReservaEstado.Cancelada,
    )
    session.add_all([reserva_activa, reserva_cancelada])
    await session.commit()

    yield {
        "tid": tid,
        "tid_otro": tid_otro,
        "uid_alumno": uid_alumno,
        "entrada_alumno_id": entrada_alumno.id,
        "cal_aprobada_id": cal_aprobada.id,
        "cal_sin_entrega_id": cal_sin_entrega.id,
        "materia_id": materia.id,
        "materia_nombre": "Matemáticas",
        "evaluacion_id": evaluacion.id,
        "reserva_activa_id": reserva_activa.id,
    }

    # Cleanup en orden de FKs
    from sqlalchemy import delete
    await session.execute(delete(ReservaEvaluacion).where(ReservaEvaluacion.tenant_id == tid))
    await session.execute(delete(TurnoEvaluacion).where(TurnoEvaluacion.tenant_id == tid))
    await session.execute(delete(Evaluacion).where(Evaluacion.tenant_id == tid))
    await session.execute(delete(Calificacion).where(Calificacion.tenant_id == tid))
    await session.execute(delete(EntradaPadron).where(EntradaPadron.tenant_id == tid))
    await session.execute(delete(VersionPadron).where(VersionPadron.tenant_id == tid))
    await session.execute(delete(Materia).where(Materia.tenant_id == tid))
    await session.execute(delete(Cohorte).where(Cohorte.tenant_id == tid))
    await session.execute(delete(Carrera).where(Carrera.tenant_id == tid))
    await session.execute(delete(Usuario).where(Usuario.tenant_id == tid))
    await session.execute(delete(Tenant).where(Tenant.id.in_([tid, tid_otro])))
    await session.commit()
    await session.close()


# ---------------------------------------------------------------------------
# get_entradas_padron_activas
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_entradas_padron_activas_retorna_entrada_del_alumno(
    test_engine, alumno_repo_data
):
    """Alumno con entrada en versión activa → se retorna con nombre de materia."""
    data = alumno_repo_data
    factory = build_session_factory(test_engine)
    session = factory()

    repo = AlumnoRepository(session=session, tenant_id=data["tid"])
    rows = await repo.get_entradas_padron_activas(data["uid_alumno"])
    await session.close()

    assert len(rows) == 1
    entrada, materia = rows[0]
    assert entrada.id == data["entrada_alumno_id"]
    assert materia.id == data["materia_id"]
    assert materia.nombre == data["materia_nombre"]


@pytest.mark.asyncio
async def test_get_entradas_padron_activas_excluye_sin_usuario_id(
    test_engine, alumno_repo_data
):
    """Entradas sin usuario_id reconciliado no deben aparecer para ningún alumno."""
    data = alumno_repo_data
    factory = build_session_factory(test_engine)
    session = factory()

    # Consulta con un uuid que no corresponde a ninguna entrada con usuario_id
    uid_no_existe = uuid.uuid4()
    repo = AlumnoRepository(session=session, tenant_id=data["tid"])
    rows = await repo.get_entradas_padron_activas(uid_no_existe)
    await session.close()

    assert rows == []


@pytest.mark.asyncio
async def test_get_entradas_padron_activas_aislamiento_por_tenant(
    test_engine, alumno_repo_data
):
    """Alumno del tenant principal no ve nada en otro tenant (aislamiento row-level)."""
    data = alumno_repo_data
    factory = build_session_factory(test_engine)
    session = factory()

    # Consulta con el uid_alumno pero en el tenant aislado → debe retornar vacío
    repo = AlumnoRepository(session=session, tenant_id=data["tid_otro"])
    rows = await repo.get_entradas_padron_activas(data["uid_alumno"])
    await session.close()

    assert rows == []


# ---------------------------------------------------------------------------
# get_calificaciones_por_entradas
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_calificaciones_por_entradas_retorna_calificaciones(
    test_engine, alumno_repo_data
):
    """Lista de entrada_ids con calificaciones → retorna las calificaciones correctas."""
    data = alumno_repo_data
    factory = build_session_factory(test_engine)
    session = factory()

    repo = AlumnoRepository(session=session, tenant_id=data["tid"])
    cals = await repo.get_calificaciones_por_entradas([data["entrada_alumno_id"]])
    await session.close()

    assert len(cals) == 2
    ids = {c.id for c in cals}
    assert data["cal_aprobada_id"] in ids
    assert data["cal_sin_entrega_id"] in ids


@pytest.mark.asyncio
async def test_get_calificaciones_por_entradas_lista_vacia(
    test_engine, alumno_repo_data
):
    """Lista vacía de entrada_ids → retorna lista vacía sin error."""
    data = alumno_repo_data
    factory = build_session_factory(test_engine)
    session = factory()

    repo = AlumnoRepository(session=session, tenant_id=data["tid"])
    cals = await repo.get_calificaciones_por_entradas([])
    await session.close()

    assert cals == []


# ---------------------------------------------------------------------------
# get_reservas_activas
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_reservas_activas_retorna_reserva_activa(
    test_engine, alumno_repo_data
):
    """Reservas Activa del alumno → se retornan con datos de evaluacion y materia."""
    data = alumno_repo_data
    factory = build_session_factory(test_engine)
    session = factory()

    repo = AlumnoRepository(session=session, tenant_id=data["tid"])
    rows = await repo.get_reservas_activas(data["uid_alumno"])
    await session.close()

    assert len(rows) == 1
    reserva, turno, evaluacion, materia = rows[0]
    assert reserva.id == data["reserva_activa_id"]
    assert turno.fecha == date(2026, 7, 15)
    assert turno.franja == "Mañana"
    assert evaluacion.id == data["evaluacion_id"]
    assert materia.nombre == data["materia_nombre"]


@pytest.mark.asyncio
async def test_get_reservas_activas_excluye_reservas_canceladas(
    test_engine, alumno_repo_data
):
    """Reservas Cancelada no deben aparecer en get_reservas_activas."""
    data = alumno_repo_data
    factory = build_session_factory(test_engine)
    session = factory()

    repo = AlumnoRepository(session=session, tenant_id=data["tid"])
    rows = await repo.get_reservas_activas(data["uid_alumno"])
    await session.close()

    # Solo 1 reserva Activa (la cancelada queda excluida)
    assert len(rows) == 1
    for reserva, *_ in rows:
        assert reserva.estado == ReservaEstado.Activa
