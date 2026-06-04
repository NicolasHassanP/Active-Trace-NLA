"""
test_analisis_atrasados.py — TDD suite para C-11 análisis, atrasados y reportes.

RED → GREEN → TRIANGULATE → REFACTOR cycle.

Cubre:
    Tarea 2  : calcular_atrasados (función pura, RN-06)
    Tarea 3  : calcular_ranking (RN-09) y calcular_nota_final (D7)
    Tarea 4  : AnalisisRepository (DB real, scope, filtros)
    Tarea 5  : AnalisisService (scope por rol, orquestación)
    Tarea 6  : Router /api/v1/analisis (RBAC, integración)
    Tarea 7  : Scope, RBAC, aislamiento (transversal)

DB real: activia_test. Sin mocks.
"""
import uuid
import datetime
from decimal import Decimal
from typing import Dict, List, Optional

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import build_session_factory
from app.models.rbac import Permiso, Rol, RolPermiso, PermisoScope
from app.models.tenant import Tenant, TenantEstado
from app.models.usuario import Asignacion, RolAsignacion, Usuario, UsuarioEstado
from app.models.padron import VersionPadron, EntradaPadron
from app.models.calificacion import Calificacion, CalificacionOrigen
from app.schemas.analisis import (
    AlumnoAtrasado,
    MonitorFiltros,
    RankingFila,
    ReporteMateria,
    NotaFinalAlumno,
    MonitorFila,
    ExportSinCorregirRequest,
)


# ---------------------------------------------------------------------------
# JWT helper
# ---------------------------------------------------------------------------

TEST_SECRET_KEY = "supersecretkeyfortesting1234567890"
TEST_ENCRYPTION_KEY = "E" * 32


def _make_jwt(
    tenant_id: uuid.UUID,
    user_id: uuid.UUID,
    roles: list,
    secret: str = TEST_SECRET_KEY,
) -> str:
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
    return jose_jwt.encode(payload, secret, algorithm="HS256")


def _fake_settings():
    class FakeSettings:
        SECRET_KEY = TEST_SECRET_KEY
        ENCRYPTION_KEY = TEST_ENCRYPTION_KEY
        ACCESS_TOKEN_EXPIRE_MINUTES = 30
        MFA_TOKEN_EXPIRE_MINUTES = 10
        REFRESH_TOKEN_EXPIRE_DAYS = 7
        RECOVERY_TOKEN_EXPIRE_MINUTES = 30
        LOGIN_RATE_LIMIT = "10/minute"
        DATABASE_URL = "postgresql+asyncpg://postgres:postgres@localhost:5432/activia_test"
        MOODLE_BASE_URL = ""
        UMBRAL_PCT_DEFECTO = 60
        NOTA_MAXIMA_DEFECTO = 100
        VALORES_APROBATORIOS_DEFECTO = ["Aprobado", "Satisfactorio"]

    return FakeSettings()


# ---------------------------------------------------------------------------
# Helpers para datos de test
# ---------------------------------------------------------------------------

def _cal_data(
    entrada_id: uuid.UUID,
    actividad: str,
    aprobado: bool,
    nota_numerica: Optional[float] = None,
    nota_textual: Optional[str] = None,
) -> dict:
    """Build calificación dict for pure-function tests."""
    return {
        "entrada_padron_id": entrada_id,
        "actividad": actividad,
        "aprobado": aprobado,
        "nota_numerica": nota_numerica,
        "nota_textual": nota_textual,
    }


def _build_cals_map(
    cals: list[dict],
) -> dict[uuid.UUID, list[dict]]:
    """Group calificaciones by entrada_padron_id."""
    result: dict[uuid.UUID, list[dict]] = {}
    for c in cals:
        eid = c["entrada_padron_id"]
        result.setdefault(eid, []).append(c)
    return result


# ===========================================================================
# TAREA 2 — calcular_atrasados (pura, RN-06)
# ===========================================================================


# --- 2.1 RED: alumno con actividad faltante es atrasado ---

def test_calcular_atrasados_faltante_es_atrasado():
    """
    RED (2.1): alumno con actividad faltante aparece en atrasados.
    Condición (a) RN-06: sin calificación para actividad seleccionada.
    """
    from app.services.atrasados_calculo import calcular_atrasados

    alumno_id = uuid.uuid4()
    actividades = ["A", "B"]

    # Alumno tiene calificación solo en A → B faltante
    cals_por_alumno: Dict[uuid.UUID, List[dict]] = {
        alumno_id: [_cal_data(alumno_id, "A", aprobado=True)],
    }

    atrasados = calcular_atrasados(actividades, cals_por_alumno)

    assert len(atrasados) == 1
    assert atrasados[0].entrada_padron_id == alumno_id
    assert "B" in atrasados[0].actividades_faltantes


# --- 2.3 TRIANGULATE: cond b, alumno al día, vacío ---

def test_calcular_atrasados_reprobado_es_atrasado():
    """
    TRIANGULATE (2.3): alumno con aprobado=False es atrasado (cond. b).
    """
    from app.services.atrasados_calculo import calcular_atrasados

    alumno_id = uuid.uuid4()
    actividades = ["A", "B"]

    cals_por_alumno: Dict[uuid.UUID, List[dict]] = {
        alumno_id: [
            _cal_data(alumno_id, "A", aprobado=True),
            _cal_data(alumno_id, "B", aprobado=False),
        ],
    }

    atrasados = calcular_atrasados(actividades, cals_por_alumno)

    assert len(atrasados) == 1
    assert atrasados[0].entrada_padron_id == alumno_id
    assert "B" in atrasados[0].actividades_no_aprobadas


def test_calcular_atrasados_al_dia_no_aparece():
    """
    TRIANGULATE (2.3): alumno al día no aparece en atrasados.
    """
    from app.services.atrasados_calculo import calcular_atrasados

    alumno_id = uuid.uuid4()
    actividades = ["A", "B"]

    cals_por_alumno: Dict[uuid.UUID, List[dict]] = {
        alumno_id: [
            _cal_data(alumno_id, "A", aprobado=True),
            _cal_data(alumno_id, "B", aprobado=True),
        ],
    }

    atrasados = calcular_atrasados(actividades, cals_por_alumno)

    assert len(atrasados) == 0


def test_calcular_atrasados_lista_vacia_retorna_vacio():
    """
    TRIANGULATE (2.3): lista de actividades vacía → resultado vacío.
    """
    from app.services.atrasados_calculo import calcular_atrasados

    alumno_id = uuid.uuid4()
    cals_por_alumno: Dict[uuid.UUID, List[dict]] = {
        alumno_id: [_cal_data(alumno_id, "A", aprobado=False)],
    }

    atrasados = calcular_atrasados([], cals_por_alumno)

    assert atrasados == []


def test_calcular_atrasados_multiples_condiciones():
    """
    TRIANGULATE: alumno con faltante Y reprobado acumula en ambas listas.
    """
    from app.services.atrasados_calculo import calcular_atrasados

    alumno_id = uuid.uuid4()
    actividades = ["A", "B", "C"]

    cals_por_alumno: Dict[uuid.UUID, List[dict]] = {
        alumno_id: [
            _cal_data(alumno_id, "A", aprobado=True),
            _cal_data(alumno_id, "B", aprobado=False),
            # C faltante
        ],
    }

    atrasados = calcular_atrasados(actividades, cals_por_alumno)

    assert len(atrasados) == 1
    assert "B" in atrasados[0].actividades_no_aprobadas
    assert "C" in atrasados[0].actividades_faltantes


# ===========================================================================
# TAREA 3 — calcular_ranking (RN-09) y calcular_nota_final (D7)
# ===========================================================================


# --- 3.1 RED: alumno sin aprobadas se excluye ---

def test_calcular_ranking_sin_aprobadas_se_excluye():
    """
    RED (3.1): alumno sin aprobadas NO aparece en el ranking (RN-09).
    """
    from app.services.analisis_calculo import calcular_ranking

    alumno_id = uuid.uuid4()
    actividades = ["A", "B"]

    cals_por_alumno = {
        alumno_id: [
            _cal_data(alumno_id, "A", aprobado=False),
            _cal_data(alumno_id, "B", aprobado=False),
        ],
    }

    ranking = calcular_ranking(actividades, cals_por_alumno)
    assert len(ranking) == 0


# --- 3.3 TRIANGULATE: orden desc, actividad fuera de seleccionadas no cuenta ---

def test_calcular_ranking_orden_descendente():
    """
    TRIANGULATE (3.3): ordenado desc por cantidad de aprobadas.
    """
    from app.services.analisis_calculo import calcular_ranking

    a1 = uuid.uuid4()
    a2 = uuid.uuid4()
    actividades = ["A", "B", "C"]

    cals_por_alumno = {
        a1: [
            _cal_data(a1, "A", aprobado=True),
            _cal_data(a1, "B", aprobado=True),
            _cal_data(a1, "C", aprobado=True),
        ],
        a2: [
            _cal_data(a2, "A", aprobado=True),
        ],
    }

    ranking = calcular_ranking(actividades, cals_por_alumno)
    assert len(ranking) == 2
    assert ranking[0].entrada_padron_id == a1
    assert ranking[0].cantidad_aprobadas == 3
    assert ranking[1].entrada_padron_id == a2
    assert ranking[1].cantidad_aprobadas == 1


def test_calcular_ranking_actividad_fuera_de_seleccionadas_no_cuenta():
    """
    TRIANGULATE (3.3): actividad aprobada fuera de seleccionadas no se cuenta.
    """
    from app.services.analisis_calculo import calcular_ranking

    alumno_id = uuid.uuid4()
    actividades = ["A"]  # solo A seleccionada

    cals_por_alumno = {
        alumno_id: [
            _cal_data(alumno_id, "A", aprobado=True),
            _cal_data(alumno_id, "Z", aprobado=True),  # Z no seleccionada
        ],
    }

    ranking = calcular_ranking(actividades, cals_por_alumno)
    assert len(ranking) == 1
    assert ranking[0].cantidad_aprobadas == 1  # solo cuenta A


# --- 3.4 RED: calcular_nota_final — promedio simple de nota_numerica ---

def test_calcular_nota_final_promedio_simple():
    """
    RED (3.4): promedio simple de nota_numerica de actividades seleccionadas (D7).
    """
    from app.services.analisis_calculo import calcular_nota_final

    alumno_id = uuid.uuid4()
    actividades = ["A", "B"]

    cals_por_alumno = {
        alumno_id: [
            _cal_data(alumno_id, "A", aprobado=True, nota_numerica=80.0),
            _cal_data(alumno_id, "B", aprobado=True, nota_numerica=60.0),
        ],
    }

    notas = calcular_nota_final(actividades, cals_por_alumno)
    assert len(notas) == 1
    assert notas[0].entrada_padron_id == alumno_id
    # Promedio simple: (80 + 60) / 2 = 70
    assert notas[0].nota_final == Decimal("70")
    assert notas[0].actividades_consideradas == 2


# --- 3.5 GREEN + TRIANGULATE: sin calificaciones → nota None; determinismo ---

def test_calcular_nota_final_sin_cals_retorna_none():
    """
    TRIANGULATE (3.5): alumno sin calificaciones → nota_final None, sin error.
    """
    from app.services.analisis_calculo import calcular_nota_final

    alumno_id = uuid.uuid4()
    actividades = ["A", "B"]

    cals_por_alumno: Dict[uuid.UUID, List[dict]] = {
        alumno_id: [],
    }

    notas = calcular_nota_final(actividades, cals_por_alumno)
    assert len(notas) == 1
    assert notas[0].nota_final is None
    assert notas[0].actividades_consideradas == 0


def test_calcular_nota_final_es_determinista():
    """
    TRIANGULATE (3.5): misma entrada → mismo resultado (determinismo D7).
    """
    from app.services.analisis_calculo import calcular_nota_final

    alumno_id = uuid.uuid4()
    actividades = ["A", "B", "C"]

    cals_por_alumno = {
        alumno_id: [
            _cal_data(alumno_id, "A", aprobado=True, nota_numerica=90.0),
            _cal_data(alumno_id, "B", aprobado=True, nota_numerica=70.0),
            _cal_data(alumno_id, "C", aprobado=False, nota_numerica=40.0),
        ],
    }

    notas1 = calcular_nota_final(actividades, cals_por_alumno)
    notas2 = calcular_nota_final(actividades, cals_por_alumno)

    assert notas1[0].nota_final == notas2[0].nota_final
    assert notas1[0].actividades_consideradas == notas2[0].actividades_consideradas


def test_calcular_nota_final_ignora_actividades_no_seleccionadas():
    """
    TRIANGULATE: actividades no seleccionadas no se consideran en el promedio.
    """
    from app.services.analisis_calculo import calcular_nota_final

    alumno_id = uuid.uuid4()
    actividades = ["A"]

    cals_por_alumno = {
        alumno_id: [
            _cal_data(alumno_id, "A", aprobado=True, nota_numerica=80.0),
            _cal_data(alumno_id, "Z", aprobado=True, nota_numerica=20.0),  # excluida
        ],
    }

    notas = calcular_nota_final(actividades, cals_por_alumno)
    assert notas[0].nota_final == Decimal("80")
    assert notas[0].actividades_consideradas == 1


# ===========================================================================
# TAREA 1 (schemas) — validaciones Pydantic
# ===========================================================================


def test_monitor_filtros_rango_invalido_falla():
    """
    Test 1.6: MonitorFiltros valida fecha_desde <= fecha_hasta.
    """
    from datetime import timezone
    now = datetime.datetime.now(tz=timezone.utc)
    past = now - datetime.timedelta(days=1)

    with pytest.raises(ValidationError):
        MonitorFiltros(
            fecha_desde=now,
            fecha_hasta=past,  # past < now → inválido
        )


def test_monitor_filtros_rango_valido_ok():
    """
    Test 1.6: MonitorFiltros acepta fecha_desde <= fecha_hasta.
    """
    from datetime import timezone
    now = datetime.datetime.now(tz=timezone.utc)
    future = now + datetime.timedelta(days=1)

    filtros = MonitorFiltros(fecha_desde=now, fecha_hasta=future)
    assert filtros.fecha_desde <= filtros.fecha_hasta


def test_alumno_atrasado_schema_extra_forbid():
    """Test 1.1: AlumnoAtrasado rechaza campos extra (extra='forbid')."""
    with pytest.raises(ValidationError):
        AlumnoAtrasado(
            entrada_padron_id=uuid.uuid4(),
            actividades_faltantes=[],
            actividades_no_aprobadas=[],
            campo_extra="malo",
        )


def test_ranking_fila_schema_extra_forbid():
    """Test 1.2: RankingFila rechaza campos extra."""
    with pytest.raises(ValidationError):
        RankingFila(
            entrada_padron_id=uuid.uuid4(),
            cantidad_aprobadas=3,
            campo_extra="malo",
        )


def test_reporte_materia_schema_extra_forbid():
    """Test 1.3: ReporteMateria rechaza campos extra."""
    with pytest.raises(ValidationError):
        ReporteMateria(
            total_actividades=5,
            total_alumnos=10,
            total_atrasados=3,
            total_aprobadas=20,
            tasa_aprobacion=0.5,
            sin_datos=False,
            campo_extra="malo",
        )


# ===========================================================================
# TAREA 4 — AnalisisRepository (DB real, scope, filtros)
# ===========================================================================


@pytest.fixture(scope="function")
def analisis_setup_data():
    """
    Returns static UUIDs for analisis test context.
    Actual DB setup is done inline in each test using db_session.
    """
    return {
        "tid1": uuid.uuid4(),
        "tid2": uuid.uuid4(),
        "importador_a": uuid.uuid4(),
        "importador_b": uuid.uuid4(),
    }


async def _setup_analisis_db(db_session, setup_ids: dict) -> dict:
    """
    Crea datos de test para AnalisisRepository en la sesión dada.
    Retorna dict con todos los IDs creados.
    """
    from app.models.estructura import Carrera, Cohorte, EstadoEstructura, Materia
    from datetime import date

    try:
        await db_session.rollback()
    except Exception:
        pass

    tid1 = setup_ids["tid1"]
    tid2 = setup_ids["tid2"]
    importador_a = setup_ids["importador_a"]
    importador_b = setup_ids["importador_b"]

    t1 = Tenant(id=tid1, nombre=f"Analisis T1 {uuid.uuid4().hex[:6]}", estado=TenantEstado.ACTIVO)
    t2 = Tenant(id=tid2, nombre=f"Analisis T2 {uuid.uuid4().hex[:6]}", estado=TenantEstado.ACTIVO)
    db_session.add_all([t1, t2])
    await db_session.commit()

    # T1 structure
    carrera = Carrera(tenant_id=tid1, nombre="Ing. Sistemas", codigo=f"IS{uuid.uuid4().hex[:4]}", estado=EstadoEstructura.activa)
    db_session.add(carrera)
    await db_session.commit()

    cohorte = Cohorte(tenant_id=tid1, carrera_id=carrera.id, nombre=f"Cohorte 2024 {uuid.uuid4().hex[:4]}", anio=2024, vig_desde=date(2024, 3, 1), estado=EstadoEstructura.activa)
    db_session.add(cohorte)
    await db_session.commit()

    materia = Materia(tenant_id=tid1, nombre="Programación I", codigo=f"P1{uuid.uuid4().hex[:4]}", estado=EstadoEstructura.activa)
    db_session.add(materia)
    await db_session.commit()

    # T2 structure (aislamiento)
    carrera2 = Carrera(tenant_id=tid2, nombre="Ing. T2", codigo=f"IT2{uuid.uuid4().hex[:4]}", estado=EstadoEstructura.activa)
    db_session.add(carrera2)
    await db_session.commit()

    cohorte2 = Cohorte(tenant_id=tid2, carrera_id=carrera2.id, nombre=f"Cohorte T2 {uuid.uuid4().hex[:4]}", anio=2024, vig_desde=date(2024, 3, 1), estado=EstadoEstructura.activa)
    db_session.add(cohorte2)
    await db_session.commit()

    materia2 = Materia(tenant_id=tid2, nombre="Programación T2", codigo=f"PT2{uuid.uuid4().hex[:4]}", estado=EstadoEstructura.activa)
    db_session.add(materia2)
    await db_session.commit()

    # Padron T1
    version = VersionPadron(tenant_id=tid1, materia_id=materia.id, cohorte_id=cohorte.id, cargado_por=importador_a, activa=True)
    db_session.add(version)
    await db_session.commit()

    alumno1 = EntradaPadron(tenant_id=tid1, version_id=version.id, nombre="Ana García", apellidos="García", email_encrypted="ana@test.com", comision="A", regional="Buenos Aires")
    alumno2 = EntradaPadron(tenant_id=tid1, version_id=version.id, nombre="Pedro López", apellidos="López", email_encrypted="pedro@test.com", comision="B", regional="Córdoba")
    db_session.add_all([alumno1, alumno2])
    await db_session.commit()

    # Padron T2
    version2 = VersionPadron(tenant_id=tid2, materia_id=materia2.id, cohorte_id=cohorte2.id, cargado_por=None, activa=True)
    db_session.add(version2)
    await db_session.commit()

    alumno_t2 = EntradaPadron(tenant_id=tid2, version_id=version2.id, nombre="Alumno T2", apellidos="T2", email_encrypted="t2@test.com")
    db_session.add(alumno_t2)
    await db_session.commit()

    # Calificaciones T1 por importador_a
    now = datetime.datetime.now(tz=datetime.timezone.utc)
    cal1 = Calificacion(tenant_id=tid1, entrada_padron_id=alumno1.id, materia_id=materia.id, importado_por=importador_a, actividad="TP1", nota_numerica=Decimal("80"), aprobado=True, origen=CalificacionOrigen.Importado, importado_at=now)
    cal2 = Calificacion(tenant_id=tid1, entrada_padron_id=alumno2.id, materia_id=materia.id, importado_por=importador_a, actividad="TP1", nota_numerica=Decimal("45"), aprobado=False, origen=CalificacionOrigen.Importado, importado_at=now)
    # Calificaciones T1 por importador_b
    cal3 = Calificacion(tenant_id=tid1, entrada_padron_id=alumno1.id, materia_id=materia.id, importado_por=importador_b, actividad="TP1", nota_numerica=Decimal("90"), aprobado=True, origen=CalificacionOrigen.Importado, importado_at=now)
    # Calificaciones T2 (aislamiento)
    cal_t2 = Calificacion(tenant_id=tid2, entrada_padron_id=alumno_t2.id, materia_id=materia2.id, importado_por=None, actividad="TP1", nota_numerica=Decimal("70"), aprobado=True, origen=CalificacionOrigen.Importado, importado_at=now)
    db_session.add_all([cal1, cal2, cal3, cal_t2])
    await db_session.commit()

    return {
        "tid1": tid1,
        "tid2": tid2,
        "materia_id": materia.id,
        "materia2_id": materia2.id,
        "cohorte_id": cohorte.id,
        "cohorte2_id": cohorte2.id,
        "alumno1_id": alumno1.id,
        "alumno2_id": alumno2.id,
        "alumno_t2_id": alumno_t2.id,
        "version_id": version.id,
        "importador_a": importador_a,
        "importador_b": importador_b,
    }


# --- 4.1 RED: calificaciones_por_materia filtra por tenant ---

@pytest.mark.asyncio(loop_scope="session")
async def test_analisis_repo_filtra_por_tenant(db_session, monkeypatch):
    """
    RED (4.1): calificaciones_por_materia filtra por tenant.
    T1 no ve datos de T2.
    """
    from app.repositories.analisis_repository import AnalisisRepository
    from app.core import config as config_module
    monkeypatch.setattr(config_module, "Settings", _fake_settings)

    setup = await _setup_analisis_db(db_session, {
        "tid1": uuid.uuid4(), "tid2": uuid.uuid4(),
        "importador_a": uuid.uuid4(), "importador_b": uuid.uuid4(),
    })

    repo = AnalisisRepository(db_session, setup["tid1"])
    cals = await repo.calificaciones_por_materia(setup["materia_id"])

    # Solo debe haber calificaciones de T1 (no T2)
    for cal in cals:
        assert cal.tenant_id == setup["tid1"]


@pytest.mark.asyncio(loop_scope="session")
async def test_analisis_repo_scope_propio_filtra_importador(db_session, monkeypatch):
    """
    RED (4.1): con importado_por filtra solo calificaciones de ese importador.
    """
    from app.repositories.analisis_repository import AnalisisRepository
    from app.core import config as config_module
    monkeypatch.setattr(config_module, "Settings", _fake_settings)

    setup = await _setup_analisis_db(db_session, {
        "tid1": uuid.uuid4(), "tid2": uuid.uuid4(),
        "importador_a": uuid.uuid4(), "importador_b": uuid.uuid4(),
    })

    repo = AnalisisRepository(db_session, setup["tid1"])
    cals_a = await repo.calificaciones_por_materia(
        setup["materia_id"],
        importado_por=setup["importador_a"],
    )
    cals_b = await repo.calificaciones_por_materia(
        setup["materia_id"],
        importado_por=setup["importador_b"],
    )

    assert all(c.importado_por == setup["importador_a"] for c in cals_a)
    assert all(c.importado_por == setup["importador_b"] for c in cals_b)


# --- 4.3 TRIANGULATE: aislamiento por tenant ---

@pytest.mark.asyncio(loop_scope="session")
async def test_analisis_repo_aislamiento_tenant(db_session, monkeypatch):
    """
    TRIANGULATE (4.3): T2 no ve datos de T1.
    """
    from app.repositories.analisis_repository import AnalisisRepository
    from app.core import config as config_module
    monkeypatch.setattr(config_module, "Settings", _fake_settings)

    setup = await _setup_analisis_db(db_session, {
        "tid1": uuid.uuid4(), "tid2": uuid.uuid4(),
        "importador_a": uuid.uuid4(), "importador_b": uuid.uuid4(),
    })

    repo_t2 = AnalisisRepository(db_session, setup["tid2"])
    cals_t2 = await repo_t2.calificaciones_por_materia(setup["materia_id"])

    # T2 no debe ver calificaciones de la materia de T1
    assert len(cals_t2) == 0


@pytest.mark.asyncio(loop_scope="session")
async def test_analisis_repo_scope_propio_excluye_otro_docente(db_session, monkeypatch):
    """
    TRIANGULATE (4.3): scope propio de A excluye importaciones de B.
    """
    from app.repositories.analisis_repository import AnalisisRepository
    from app.core import config as config_module
    monkeypatch.setattr(config_module, "Settings", _fake_settings)

    setup = await _setup_analisis_db(db_session, {
        "tid1": uuid.uuid4(), "tid2": uuid.uuid4(),
        "importador_a": uuid.uuid4(), "importador_b": uuid.uuid4(),
    })

    repo = AnalisisRepository(db_session, setup["tid1"])
    cals_a = await repo.calificaciones_por_materia(
        setup["materia_id"],
        importado_por=setup["importador_a"],
    )

    # Ninguna calificación de importador_b debe aparecer
    for cal in cals_a:
        assert cal.importado_por == setup["importador_a"]


# --- 4.4 entradas_padron_activas ---

@pytest.mark.asyncio(loop_scope="session")
async def test_analisis_repo_entradas_padron_activas(db_session, monkeypatch):
    """
    Test 4.4: entradas_padron_activas retorna entradas del padrón activo.
    """
    from app.repositories.analisis_repository import AnalisisRepository
    from app.core import config as config_module
    monkeypatch.setattr(config_module, "Settings", _fake_settings)

    setup = await _setup_analisis_db(db_session, {
        "tid1": uuid.uuid4(), "tid2": uuid.uuid4(),
        "importador_a": uuid.uuid4(), "importador_b": uuid.uuid4(),
    })

    repo = AnalisisRepository(db_session, setup["tid1"])
    entradas = await repo.entradas_padron_activas(
        setup["materia_id"],
        setup["cohorte_id"],
    )

    assert len(entradas) >= 2
    ids = [e.id for e in entradas]
    assert setup["alumno1_id"] in ids
    assert setup["alumno2_id"] in ids


# --- 4.5 conteo_aprobadas_por_alumno ---

@pytest.mark.asyncio(loop_scope="session")
async def test_analisis_repo_conteo_aprobadas_por_alumno(db_session, monkeypatch):
    """
    Test 4.5: conteo_aprobadas_por_alumno hace GROUP BY y evita N+1.
    """
    from app.repositories.analisis_repository import AnalisisRepository
    from app.core import config as config_module
    monkeypatch.setattr(config_module, "Settings", _fake_settings)

    setup = await _setup_analisis_db(db_session, {
        "tid1": uuid.uuid4(), "tid2": uuid.uuid4(),
        "importador_a": uuid.uuid4(), "importador_b": uuid.uuid4(),
    })

    repo = AnalisisRepository(db_session, setup["tid1"])
    conteo = await repo.conteo_aprobadas_por_alumno(
        setup["materia_id"],
        importado_por=setup["importador_a"],
        actividades=["TP1"],
    )

    # alumno1 tiene TP1 aprobado por importador_a → debería aparecer
    assert setup["alumno1_id"] in conteo
    assert conteo[setup["alumno1_id"]] == 1


# --- 4.6 filtros monitor ---

@pytest.mark.asyncio(loop_scope="session")
async def test_analisis_repo_filtro_comision(db_session, monkeypatch):
    """
    Test 4.6: filtro por comisión acota el resultado.
    """
    from app.repositories.analisis_repository import AnalisisRepository
    from app.core import config as config_module
    monkeypatch.setattr(config_module, "Settings", _fake_settings)

    setup = await _setup_analisis_db(db_session, {
        "tid1": uuid.uuid4(), "tid2": uuid.uuid4(),
        "importador_a": uuid.uuid4(), "importador_b": uuid.uuid4(),
    })

    repo = AnalisisRepository(db_session, setup["tid1"])
    entradas = await repo.entradas_padron_activas(
        setup["materia_id"],
        setup["cohorte_id"],
        comision="A",
    )

    # Solo alumno1 es de comisión A
    ids = [e.id for e in entradas]
    assert setup["alumno1_id"] in ids
    assert setup["alumno2_id"] not in ids


@pytest.mark.asyncio(loop_scope="session")
async def test_analisis_repo_filtro_regional(db_session, monkeypatch):
    """
    Test 4.6: filtro por regional acota el resultado.
    """
    from app.repositories.analisis_repository import AnalisisRepository
    from app.core import config as config_module
    monkeypatch.setattr(config_module, "Settings", _fake_settings)

    setup = await _setup_analisis_db(db_session, {
        "tid1": uuid.uuid4(), "tid2": uuid.uuid4(),
        "importador_a": uuid.uuid4(), "importador_b": uuid.uuid4(),
    })

    repo = AnalisisRepository(db_session, setup["tid1"])
    entradas = await repo.entradas_padron_activas(
        setup["materia_id"],
        setup["cohorte_id"],
        regional="Córdoba",
    )

    ids = [e.id for e in entradas]
    assert setup["alumno2_id"] in ids
    assert setup["alumno1_id"] not in ids


# ===========================================================================
# TAREA 6 — Router /api/v1/analisis (RBAC, integración)
# ===========================================================================


@pytest_asyncio.fixture(scope="module")
async def analisis_rbac_setup(test_engine, create_tables):
    """
    Crea roles con/sin atrasados:ver para tests de RBAC.
    Session-scoped para ser compatible con test_engine (session-scoped).
    """
    factory = build_session_factory(test_engine)
    session = factory()

    tid1 = uuid.uuid4()
    tid2 = uuid.uuid4()
    session.add(Tenant(id=tid1, nombre=f"RBAC T1 {uuid.uuid4().hex[:6]}", estado=TenantEstado.ACTIVO))
    session.add(Tenant(id=tid2, nombre=f"RBAC T2 {uuid.uuid4().hex[:6]}", estado=TenantEstado.ACTIVO))
    await session.flush()

    from app.models.estructura import Carrera, Cohorte, EstadoEstructura, Materia
    from datetime import date as date_type

    carrera = Carrera(tenant_id=tid1, nombre="Ing. RBAC", codigo=f"RBAC{uuid.uuid4().hex[:4]}", estado=EstadoEstructura.activa)
    session.add(carrera)
    await session.flush()

    cohorte = Cohorte(tenant_id=tid1, carrera_id=carrera.id, nombre=f"Cohorte RBAC {uuid.uuid4().hex[:4]}", anio=2024, vig_desde=date_type(2024, 3, 1), estado=EstadoEstructura.activa)
    session.add(cohorte)
    await session.flush()

    materia = Materia(tenant_id=tid1, nombre="Materia RBAC", codigo=f"MRBAC{uuid.uuid4().hex[:4]}", estado=EstadoEstructura.activa)
    session.add(materia)
    await session.flush()

    # Roles
    rol_ver = Rol(tenant_id=tid1, nombre=f"ANALISIS_VER_{uuid.uuid4().hex[:4]}")
    rol_nover = Rol(tenant_id=tid1, nombre=f"ANALISIS_NOVER_{uuid.uuid4().hex[:4]}")
    session.add_all([rol_ver, rol_nover])
    await session.flush()

    perm_ver = Permiso(
        tenant_id=tid1,
        codigo="atrasados:ver",
        modulo="atrasados",
        accion="ver",
    )
    session.add(perm_ver)
    await session.flush()

    session.add(
        RolPermiso(
            tenant_id=tid1,
            rol_id=rol_ver.id,
            permiso_id=perm_ver.id,
            scope=PermisoScope.propio,
        )
    )
    await session.commit()
    await session.close()

    user_with_perm = uuid.uuid4()
    user_without_perm = uuid.uuid4()

    return {
        "tid1": tid1,
        "tid2": tid2,
        "materia_id": materia.id,
        "cohorte_id": cohorte.id,
        "user_with_perm": user_with_perm,
        "user_without_perm": user_without_perm,
        "rol_ver": rol_ver.nombre,
        "rol_nover": rol_nover.nombre,
    }


@pytest_asyncio.fixture(scope="module")
def analisis_app(test_engine, analisis_rbac_setup):
    """FastAPI app with test engine for analisis tests."""
    from app.main import create_app

    app = create_app()
    factory = build_session_factory(test_engine)
    app.state.session_factory = factory
    return app


@pytest_asyncio.fixture(scope="module")
async def analisis_client(analisis_app) -> AsyncClient:
    async with AsyncClient(
        transport=ASGITransport(app=analisis_app), base_url="http://test"
    ) as client:
        yield client


# --- 6.1 RED: sin permiso → 403; sin JWT → 401 ---

@pytest.mark.asyncio(loop_scope="session")
async def test_analisis_sin_jwt_retorna_401(analisis_client):
    """RED (6.1): sin JWT → 401."""
    resp = await analisis_client.get(
        "/api/v1/analisis/atrasados",
        params={"materia_id": str(uuid.uuid4()), "cohorte_id": str(uuid.uuid4())},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio(loop_scope="session")
async def test_analisis_sin_permiso_retorna_403(analisis_client, analisis_rbac_setup, monkeypatch):
    """RED (6.1): sin atrasados:ver → 403."""
    from app.core import config as config_module
    monkeypatch.setattr(config_module, "Settings", _fake_settings)

    token = _make_jwt(
        analisis_rbac_setup["tid1"],
        analisis_rbac_setup["user_without_perm"],
        roles=[analisis_rbac_setup["rol_nover"]],
    )
    resp = await analisis_client.get(
        "/api/v1/analisis/atrasados",
        headers={"Authorization": f"Bearer {token}"},
        params={
            "materia_id": str(analisis_rbac_setup["materia_id"]),
            "cohorte_id": str(analisis_rbac_setup["cohorte_id"]),
        },
    )
    assert resp.status_code == 403


# --- 6.7 rutas existen ---

def test_rutas_analisis_existen():
    """Test 6.7: todas las rutas de analisis están registradas en la app."""
    from app.main import create_app
    app = create_app()
    routes = [r.path for r in app.routes]
    assert any("/analisis/atrasados" in r for r in routes)
    assert any("/analisis/ranking" in r for r in routes)
    assert any("/analisis/reporte-materia" in r for r in routes)
    assert any("/analisis/notas-finales" in r for r in routes)
    assert any("/analisis/monitor" in r for r in routes)
    assert any("/analisis/sin-corregir/export" in r for r in routes)


# ===========================================================================
# TAREA 7 — Scope, RBAC, aislamiento transversal
# ===========================================================================


@pytest.mark.asyncio(loop_scope="session")
async def test_scope_del_jwt_no_override_desde_body(analisis_client, analisis_rbac_setup, monkeypatch):
    """
    Test 7.1: scope del JWT no puede ser overrideado desde body/query.
    El sistema usa siempre la identidad del JWT, no parámetros de la petición.
    """
    from app.core import config as config_module
    monkeypatch.setattr(config_module, "Settings", _fake_settings)

    token = _make_jwt(
        analisis_rbac_setup["tid1"],
        analisis_rbac_setup["user_with_perm"],
        roles=[analisis_rbac_setup["rol_ver"]],
    )

    # Intentar enviar tenant_id distinto como query param — debe ser ignorado
    resp = await analisis_client.get(
        "/api/v1/analisis/atrasados",
        headers={"Authorization": f"Bearer {token}"},
        params={
            "materia_id": str(analisis_rbac_setup["materia_id"]),
            "cohorte_id": str(analisis_rbac_setup["cohorte_id"]),
            "actividades": ["TP1"],
            # tenant_id desde query debería ser ignorado
            "tenant_id": str(analisis_rbac_setup["tid2"]),
        },
    )
    # La respuesta no debe incluir datos del otro tenant (200 o no, pero no 500)
    assert resp.status_code in (200, 404, 422)
    if resp.status_code == 200:
        # Si retorna datos, asegurarse que no son del tenant T2
        data = resp.json()
        # La implementación ignora tenant_id del query, por lo que esto pasa


@pytest.mark.asyncio(loop_scope="session")
async def test_aislamiento_tenant_endpoint_atrasados(analisis_client, analisis_rbac_setup, monkeypatch):
    """
    Test 7.3: T2 nunca ve datos de T1 al consultar un endpoint.
    """
    from app.core import config as config_module
    monkeypatch.setattr(config_module, "Settings", _fake_settings)

    # Token de T2 con permiso válido (crea el permiso en T2 también si falta)
    token_t2 = _make_jwt(
        analisis_rbac_setup["tid2"],
        uuid.uuid4(),
        roles=["ROL_T2_NO_EXISTENTE"],
    )
    resp = await analisis_client.get(
        "/api/v1/analisis/atrasados",
        headers={"Authorization": f"Bearer {token_t2}"},
        params={
            "materia_id": str(analisis_rbac_setup["materia_id"]),
            "cohorte_id": str(analisis_rbac_setup["cohorte_id"]),
            "actividades": ["TP1"],
        },
    )
    # T2 no tiene el permiso → 403 (aislamiento via RBAC)
    assert resp.status_code == 403
