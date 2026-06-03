"""
test_estructura_academica.py — TDD suite para C-06 estructura académica.

Cubre tasks 1–11 del tasks.md siguiendo el ciclo RED → GREEN → TRIANGULATE → REFACTOR.

Estructura de tests:
  Task 1–4  : Modelos (EstadoEstructura, Carrera, Materia, Cohorte)
  Task 5    : Migración 005 (upgrade/downgrade)
  Task 6    : Índices únicos parciales (unicidad DB)
  Task 7    : Repositories tenant-scoped
  Task 8    : EstructuraService — unicidad y regla carrera-inactiva
  Task 9    : Schemas Pydantic v2
  Task 10   : Endpoints ABM (HTTP 403/201/409/404/204)

DB real: activia_trace_test. Sin mocks.
Settings parcheados con monkeypatch (patrón C-05).
"""
import datetime
import uuid
from datetime import date

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.exc import IntegrityError

from app.core.database import build_session_factory
from app.models.estructura import Carrera, Cohorte, EstadoEstructura, Materia
from app.models.rbac import Permiso, Rol, RolPermiso, PermisoScope
from app.models.tenant import Tenant, TenantEstado
from app.repositories.estructura_repository import (
    CarreraRepository,
    CohorteRepository,
    MateriaRepository,
)
from app.schemas.estructura import (
    CarreraCreate,
    CarreraRead,
    CarreraUpdate,
    CohorteCreate,
    CohorteRead,
    CohorteUpdate,
    MateriaCreate,
    MateriaRead,
    MateriaUpdate,
)
from app.services.estructura_service import (
    CarreraConCohorteAbiertas,
    CarreraInactiva,
    CarreraNoEncontrada,
    ConflictoUnicidad,
    EstructuraService,
    _es_cohorte_abierta,
)


# ---------------------------------------------------------------------------
# JWT / settings helper (mismo patrón que test_auditoria_router.py)
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

    return FakeSettings()


# ---------------------------------------------------------------------------
# Shared fixtures — TENANT setup para todas las pruebas del módulo
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture(scope="module")
async def estructura_setup(test_engine, create_tables):
    """
    Crea dos tenants con RBAC catalog para tests de estructura académica.
      tenant_a: user_admin_a → ADMIN con estructura:gestionar (global)
      tenant_b: user_b      → ADMIN con estructura:gestionar (global)
    """
    factory = build_session_factory(test_engine)
    session = factory()

    tid_a = uuid.uuid4()
    tid_b = uuid.uuid4()
    session.add(Tenant(id=tid_a, nombre="Estructura Tenant A", estado=TenantEstado.ACTIVO))
    session.add(Tenant(id=tid_b, nombre="Estructura Tenant B", estado=TenantEstado.ACTIVO))
    await session.flush()

    user_admin_a = uuid.uuid4()
    user_b = uuid.uuid4()

    # Roles
    rol_admin_a = Rol(tenant_id=tid_a, nombre="EST_ADMIN_A")
    rol_b = Rol(tenant_id=tid_b, nombre="EST_ADMIN_B")
    session.add_all([rol_admin_a, rol_b])
    await session.flush()

    # Permiso estructura:gestionar para tenant A
    perm_a = Permiso(
        tenant_id=tid_a,
        codigo="estructura:gestionar",
        modulo="estructura",
        accion="gestionar",
    )
    perm_b = Permiso(
        tenant_id=tid_b,
        codigo="estructura:gestionar",
        modulo="estructura",
        accion="gestionar",
    )
    session.add_all([perm_a, perm_b])
    await session.flush()

    # Grants
    session.add(
        RolPermiso(
            tenant_id=tid_a,
            rol_id=rol_admin_a.id,
            permiso_id=perm_a.id,
            scope=PermisoScope.global_,
        )
    )
    session.add(
        RolPermiso(
            tenant_id=tid_b,
            rol_id=rol_b.id,
            permiso_id=perm_b.id,
            scope=PermisoScope.global_,
        )
    )
    await session.commit()
    await session.close()

    return {
        "tid_a": tid_a,
        "tid_b": tid_b,
        "user_admin_a": user_admin_a,
        "user_b": user_b,
        "rol_admin_a": "EST_ADMIN_A",
        "rol_b": "EST_ADMIN_B",
    }


@pytest_asyncio.fixture(scope="module")
def estructura_app(test_engine, estructura_setup):
    """FastAPI app con test engine para tests de estructura."""
    from app.main import create_app

    app = create_app()
    session_factory = build_session_factory(test_engine)
    app.state.session_factory = session_factory
    return app


# ===========================================================================
# Task 1 — EstadoEstructura enum (RED → GREEN → TRIANGULATE)
# ===========================================================================


class TestEstadoEstructura:
    """Task 1: enum compartido EstadoEstructura."""

    def test_enum_contains_activa_e_inactiva(self):
        """Task 1.1 RED: el enum contiene activa e inactiva."""
        assert EstadoEstructura.activa.value == "activa"
        assert EstadoEstructura.inactiva.value == "inactiva"

    def test_enum_rechaza_valor_arbitrario(self):
        """Task 1.1 RED: valor fuera del enum lanza ValueError."""
        with pytest.raises(ValueError):
            EstadoEstructura("borrado")

    def test_enum_hereda_str(self):
        """Task 1.3 TRIANGULATE: el enum es str (útil para Pydantic/SQLAlchemy)."""
        assert isinstance(EstadoEstructura.activa, str)
        assert EstadoEstructura.activa == "activa"

    def test_enum_es_constante_del_sistema(self):
        """Task 1.3 TRIANGULATE: mismos valores sin importar el tenant (constante)."""
        valores = {e.value for e in EstadoEstructura}
        assert valores == {"activa", "inactiva"}


# ===========================================================================
# Task 2 — Modelo Carrera (RED → GREEN → TRIANGULATE)
# ===========================================================================


class TestCarreraModel:
    """Task 2: modelo Carrera tiene los campos requeridos."""

    def test_carrera_tiene_columnas_requeridas(self):
        """Task 2.1 RED: Carrera tiene id, tenant_id, codigo, nombre, estado, timestamps, deleted_at."""
        cols = {c.key for c in Carrera.__mapper__.columns}
        assert "id" in cols
        assert "tenant_id" in cols
        assert "codigo" in cols
        assert "nombre" in cols
        assert "estado" in cols
        assert "created_at" in cols
        assert "updated_at" in cols
        assert "deleted_at" in cols

    def test_carrera_estado_default_activa(self):
        """Task 2.3 TRIANGULATE: estado 'activa' es el valor semántico por defecto
        (el service siempre crea con estado=activa; el DB default es 'activa')."""
        # La creación explícita con estado activa funciona
        c = Carrera(tenant_id=uuid.uuid4(), codigo="TI", nombre="Tecnología",
                    estado=EstadoEstructura.activa)
        assert c.estado == EstadoEstructura.activa

    def test_carrera_deleted_at_default_nulo(self):
        """Task 2.3 TRIANGULATE: deleted_at arranca nulo."""
        c = Carrera(tenant_id=uuid.uuid4(), codigo="TI", nombre="Tecnología")
        assert c.deleted_at is None

    def test_carrera_tablename(self):
        """Task 2.2 GREEN: __tablename__ == 'carrera'."""
        assert Carrera.__tablename__ == "carrera"


# ===========================================================================
# Task 3 — Modelo Materia (RED → GREEN → TRIANGULATE)
# ===========================================================================


class TestMateriaModel:
    """Task 3: modelo Materia tiene los campos requeridos, SIN carrera_id."""

    def test_materia_tiene_columnas_requeridas(self):
        """Task 3.1 RED: Materia tiene los campos esperados."""
        cols = {c.key for c in Materia.__mapper__.columns}
        assert "id" in cols
        assert "tenant_id" in cols
        assert "codigo" in cols
        assert "nombre" in cols
        assert "estado" in cols
        assert "created_at" in cols
        assert "updated_at" in cols
        assert "deleted_at" in cols

    def test_materia_no_tiene_carrera_id(self):
        """Task 3.1 RED: Materia NO tiene carrera_id (catálogo plano, ADR-006)."""
        cols = {c.key for c in Materia.__mapper__.columns}
        assert "carrera_id" not in cols

    def test_materia_estado_default_activa(self):
        """Task 3.3 TRIANGULATE: estado 'activa' es el valor semántico por defecto."""
        m = Materia(tenant_id=uuid.uuid4(), codigo="PROG_I", nombre="Prog I",
                    estado=EstadoEstructura.activa)
        assert m.estado == EstadoEstructura.activa

    def test_materia_deleted_at_nulo(self):
        """Task 3.3 TRIANGULATE: deleted_at arranca nulo."""
        m = Materia(tenant_id=uuid.uuid4(), codigo="PROG_I", nombre="Prog I")
        assert m.deleted_at is None


# ===========================================================================
# Task 4 — Modelo Cohorte (RED → GREEN → TRIANGULATE)
# ===========================================================================


class TestCohorteModel:
    """Task 4: modelo Cohorte tiene campos requeridos y FK obligatoria."""

    def test_cohorte_tiene_columnas_requeridas(self):
        """Task 4.1 RED: Cohorte tiene id, tenant_id, carrera_id, nombre, anio, vig_desde, vig_hasta, estado, timestamps, deleted_at."""
        cols = {c.key for c in Cohorte.__mapper__.columns}
        assert "id" in cols
        assert "tenant_id" in cols
        assert "carrera_id" in cols
        assert "nombre" in cols
        assert "anio" in cols
        assert "vig_desde" in cols
        assert "vig_hasta" in cols
        assert "estado" in cols
        assert "created_at" in cols
        assert "updated_at" in cols
        assert "deleted_at" in cols

    def test_cohorte_vig_hasta_admite_nulo(self):
        """Task 4.3 TRIANGULATE: vig_hasta nullable (cohorte abierta)."""
        tid = uuid.uuid4()
        cid = uuid.uuid4()
        c = Cohorte(
            tenant_id=tid,
            carrera_id=cid,
            nombre="AGO-2025",
            anio=2025,
            vig_desde=date(2025, 8, 1),
            vig_hasta=None,
        )
        assert c.vig_hasta is None

    def test_cohorte_estado_default_activa(self):
        """Task 4.3 TRIANGULATE: estado 'activa' es el valor semántico por defecto."""
        tid = uuid.uuid4()
        cid = uuid.uuid4()
        c = Cohorte(
            tenant_id=tid,
            carrera_id=cid,
            nombre="AGO-2025",
            anio=2025,
            vig_desde=date(2025, 8, 1),
            estado=EstadoEstructura.activa,
        )
        assert c.estado == EstadoEstructura.activa

    def test_cohorte_tablename(self):
        """Task 4.2 GREEN: __tablename__ == 'cohorte'."""
        assert Cohorte.__tablename__ == "cohorte"


# ===========================================================================
# Task 5 — Migración 005 (upgrade/downgrade verificados contra DB de test)
# ===========================================================================


@pytest.mark.asyncio(loop_scope="function")
async def test_migracion_005_tablas_existen(test_engine, create_tables):
    """Task 5.8: tras upgrade, las tablas carrera, materia, cohorte existen."""
    from sqlalchemy import text

    async with test_engine.connect() as conn:
        for tabla in ("carrera", "materia", "cohorte"):
            result = await conn.execute(
                text(
                    "SELECT 1 FROM information_schema.tables "
                    "WHERE table_schema='public' AND table_name=:t"
                ),
                {"t": tabla},
            )
            assert result.scalar() == 1, f"Tabla '{tabla}' no encontrada después del upgrade"


@pytest.mark.asyncio(loop_scope="function")
async def test_migracion_005_enum_estado_estructura_existe(test_engine, create_tables):
    """Task 5.2: el enum estado_estructura existe en la DB."""
    from sqlalchemy import text

    async with test_engine.connect() as conn:
        result = await conn.execute(
            text("SELECT 1 FROM pg_type WHERE typname = 'estado_estructura'")
        )
        assert result.scalar() == 1, "Enum estado_estructura no encontrado"


# ===========================================================================
# Task 6 — Índices únicos parciales (unicidad DB)
# ===========================================================================


@pytest.mark.asyncio(loop_scope="function")
async def test_unicidad_carrera_mismo_codigo_mismo_tenant(test_engine, create_tables):
    """
    Task 6.1/6.4 RED->GREEN: la unicidad (tenant_id, codigo) para carreras es garantizada
    a nivel service (ConflictoUnicidad antes del INSERT).
    El indice parcial ux_carrera_tenant_codigo en DB es la defensa en profundidad.
    """
    from app.core.dependencies import CurrentUser

    factory = build_session_factory(test_engine)
    session = factory()
    tid = uuid.uuid4()
    session.add(Tenant(id=tid, nombre="Ux Carrera Svc Tenant", estado=TenantEstado.ACTIVO))
    await session.commit()

    svc = EstructuraService(
        carrera_repo=CarreraRepository(session=session, tenant_id=tid),
        cohorte_repo=CohorteRepository(session=session, tenant_id=tid),
        materia_repo=MateriaRepository(session=session, tenant_id=tid),
    )
    actor = CurrentUser(user_id=uuid.uuid4(), tenant_id=tid, roles=["ADMIN"])
    await svc.crear_carrera(actor, "TUPAD_UX", "Tecnicatura 1")

    with pytest.raises(ConflictoUnicidad):
        await svc.crear_carrera(actor, "TUPAD_UX", "Tecnicatura 2")
    await session.close()


@pytest.mark.asyncio(loop_scope="function")
async def test_unicidad_materia_mismo_codigo_mismo_tenant(test_engine, create_tables):
    """
    Task 6.2/6.4 RED->GREEN: la unicidad (tenant_id, codigo) para materias es garantizada
    a nivel service (ConflictoUnicidad) y por ux_materia_tenant_codigo en DB.
    """
    from app.core.dependencies import CurrentUser

    factory = build_session_factory(test_engine)
    session = factory()
    tid = uuid.uuid4()
    session.add(Tenant(id=tid, nombre="Ux Materia Svc Tenant", estado=TenantEstado.ACTIVO))
    await session.commit()

    svc = EstructuraService(
        carrera_repo=CarreraRepository(session=session, tenant_id=tid),
        cohorte_repo=CohorteRepository(session=session, tenant_id=tid),
        materia_repo=MateriaRepository(session=session, tenant_id=tid),
    )
    actor = CurrentUser(user_id=uuid.uuid4(), tenant_id=tid, roles=["ADMIN"])
    await svc.crear_materia(actor, "PROG_I_UX", "Prog I")

    with pytest.raises(ConflictoUnicidad):
        await svc.crear_materia(actor, "PROG_I_UX", "Prog I dup")
    await session.close()


@pytest.mark.asyncio(loop_scope="function")
async def test_unicidad_cohorte_mismo_carrera_nombre(test_engine, create_tables):
    """
    Task 6.3/6.4 RED->GREEN: la unicidad (tenant_id, carrera_id, nombre) para cohortes
    es garantizada a nivel service y por ux_cohorte_tenant_carrera_nombre en DB.
    """
    from app.core.dependencies import CurrentUser

    factory = build_session_factory(test_engine)
    session = factory()
    tid = uuid.uuid4()
    session.add(Tenant(id=tid, nombre="Ux Coh Svc Tenant", estado=TenantEstado.ACTIVO))
    await session.commit()

    svc = EstructuraService(
        carrera_repo=CarreraRepository(session=session, tenant_id=tid),
        cohorte_repo=CohorteRepository(session=session, tenant_id=tid),
        materia_repo=MateriaRepository(session=session, tenant_id=tid),
    )
    actor = CurrentUser(user_id=uuid.uuid4(), tenant_id=tid, roles=["ADMIN"])
    carrera = await svc.crear_carrera(actor, "CAR_COH_UX2", "Carrera Ux")
    await svc.crear_cohorte(actor, carrera.id, "AGO-2025", 2025, date(2025, 8, 1), None)

    with pytest.raises(ConflictoUnicidad):
        await svc.crear_cohorte(actor, carrera.id, "AGO-2025", 2025, date(2025, 8, 1), None)
    await session.close()


@pytest.mark.asyncio(loop_scope="function")
async def test_reutilizacion_codigo_tras_baja_logica(test_engine, create_tables):
    """
    Task 6.5 TRIANGULATE: tras baja logica de carrera, se puede crear otra con el mismo codigo.
    El service busca solo filas no borradas (deleted_at IS NULL).
    """
    from app.core.dependencies import CurrentUser

    factory = build_session_factory(test_engine)
    session = factory()
    tid = uuid.uuid4()
    session.add(Tenant(id=tid, nombre="Ux Reuse Svc Tenant", estado=TenantEstado.ACTIVO))
    await session.commit()

    svc = EstructuraService(
        carrera_repo=CarreraRepository(session=session, tenant_id=tid),
        cohorte_repo=CohorteRepository(session=session, tenant_id=tid),
        materia_repo=MateriaRepository(session=session, tenant_id=tid),
    )
    actor = CurrentUser(user_id=uuid.uuid4(), tenant_id=tid, roles=["ADMIN"])

    # Crear y dar de baja
    c1 = await svc.crear_carrera(actor, "REUSE_SVC", "Carrera Reuse 1")
    await svc.dar_baja_carrera(c1.id)

    # Ahora se puede crear otra con el mismo codigo (baja logica libera el codigo)
    c2 = await svc.crear_carrera(actor, "REUSE_SVC", "Carrera Reuse 2")
    assert c2.id is not None
    assert c2.codigo == "REUSE_SVC"
    await session.close()


# ===========================================================================
# Task 7 — Repositories tenant-scoped
# ===========================================================================


@pytest.mark.asyncio(loop_scope="function")
async def test_carrera_repo_add_fuerza_tenant_id(test_engine, create_tables):
    """
    Task 7.1 RED→GREEN: CarreraRepository.add fuerza tenant_id del scope.
    """
    factory = build_session_factory(test_engine)
    session = factory()

    tid = uuid.uuid4()
    session.add(Tenant(id=tid, nombre="Repo Test Tenant 1", estado=TenantEstado.ACTIVO))
    await session.commit()

    repo = CarreraRepository(session=session, tenant_id=tid)
    # Intentamos con tenant_id diferente — el repo debe sobreescribir
    wrong_tid = uuid.uuid4()
    c = Carrera(tenant_id=wrong_tid, codigo="FORCE_TID", nombre="Force TenantId")
    saved = await repo.add(c)
    assert saved.tenant_id == tid, "Repository debe forzar tenant_id del scope"
    await session.close()


@pytest.mark.asyncio(loop_scope="function")
async def test_carrera_repo_list_filtra_por_tenant(test_engine, create_tables):
    """
    Task 7.1 RED→GREEN: list() filtra por tenant y deleted_at IS NULL.
    """
    factory = build_session_factory(test_engine)
    session = factory()

    tid = uuid.uuid4()
    session.add(Tenant(id=tid, nombre="Repo List Tenant", estado=TenantEstado.ACTIVO))
    await session.commit()

    repo = CarreraRepository(session=session, tenant_id=tid)
    c = Carrera(tenant_id=tid, codigo="LIST_TEST", nombre="List Test")
    await repo.add(c)

    all_carreras = await repo.list()
    assert any(x.codigo == "LIST_TEST" for x in all_carreras)
    await session.close()


@pytest.mark.asyncio(loop_scope="function")
async def test_aislamiento_tenant_carrera(test_engine, create_tables):
    """
    Task 7.2 RED: list() del tenant A nunca devuelve registros del tenant B.
    """
    factory = build_session_factory(test_engine)
    session = factory()

    tid_a = uuid.uuid4()
    tid_b = uuid.uuid4()
    session.add(Tenant(id=tid_a, nombre="Isolation A", estado=TenantEstado.ACTIVO))
    session.add(Tenant(id=tid_b, nombre="Isolation B", estado=TenantEstado.ACTIVO))
    await session.commit()

    repo_a = CarreraRepository(session=session, tenant_id=tid_a)
    repo_b = CarreraRepository(session=session, tenant_id=tid_b)

    c_b = Carrera(tenant_id=tid_b, codigo="ONLY_B", nombre="Solo B")
    await repo_b.add(c_b)

    carreras_a = await repo_a.list()
    codigos_a = {c.codigo for c in carreras_a}
    assert "ONLY_B" not in codigos_a, "Tenant A no debe ver registros del tenant B"
    await session.close()


@pytest.mark.asyncio(loop_scope="function")
async def test_aislamiento_tenant_materia(test_engine, create_tables):
    """
    Task 7.2 RED: list() de materia del tenant A no devuelve registros del tenant B.
    """
    factory = build_session_factory(test_engine)
    session = factory()

    tid_a = uuid.uuid4()
    tid_b = uuid.uuid4()
    session.add(Tenant(id=tid_a, nombre="Mat Isolation A", estado=TenantEstado.ACTIVO))
    session.add(Tenant(id=tid_b, nombre="Mat Isolation B", estado=TenantEstado.ACTIVO))
    await session.commit()

    repo_a = MateriaRepository(session=session, tenant_id=tid_a)
    repo_b = MateriaRepository(session=session, tenant_id=tid_b)

    m_b = Materia(tenant_id=tid_b, codigo="MAT_ONLY_B", nombre="Solo B")
    await repo_b.add(m_b)

    materias_a = await repo_a.list()
    codigos_a = {m.codigo for m in materias_a}
    assert "MAT_ONLY_B" not in codigos_a
    await session.close()


@pytest.mark.asyncio(loop_scope="function")
async def test_cohorte_repo_list_por_carrera(test_engine, create_tables):
    """
    Task 7.5 TRIANGULATE: CohorteRepository.list(carrera_id=...) filtra por carrera.
    """
    factory = build_session_factory(test_engine)
    session = factory()

    tid = uuid.uuid4()
    session.add(Tenant(id=tid, nombre="Coh Repo Tenant", estado=TenantEstado.ACTIVO))
    await session.commit()

    c_repo = CarreraRepository(session=session, tenant_id=tid)
    coh_repo = CohorteRepository(session=session, tenant_id=tid)

    car1 = await c_repo.add(Carrera(tenant_id=tid, codigo="CAR_LIST_1", nombre="Car 1"))
    car2 = await c_repo.add(Carrera(tenant_id=tid, codigo="CAR_LIST_2", nombre="Car 2"))

    await coh_repo.add(Cohorte(
        tenant_id=tid, carrera_id=car1.id, nombre="COH_A",
        anio=2025, vig_desde=date(2025, 1, 1),
    ))
    await coh_repo.add(Cohorte(
        tenant_id=tid, carrera_id=car2.id, nombre="COH_B",
        anio=2025, vig_desde=date(2025, 1, 1),
    ))

    cohortes_car1 = await coh_repo.list(carrera_id=car1.id)
    nombres = {c.nombre for c in cohortes_car1}
    assert "COH_A" in nombres
    assert "COH_B" not in nombres
    await session.close()


@pytest.mark.asyncio(loop_scope="function")
async def test_soft_delete_no_borra_fisicamente(test_engine, create_tables):
    """
    Task 7.5 TRIANGULATE: soft_delete marca deleted_at sin borrar físicamente.
    """
    factory = build_session_factory(test_engine)
    session = factory()

    tid = uuid.uuid4()
    session.add(Tenant(id=tid, nombre="SoftDel Tenant", estado=TenantEstado.ACTIVO))
    await session.commit()

    repo = CarreraRepository(session=session, tenant_id=tid)
    c = await repo.add(Carrera(tenant_id=tid, codigo="SOFT_DEL", nombre="Soft Del"))

    await repo.delete(c)
    assert c.deleted_at is not None, "deleted_at debe setearse en soft delete"

    # list() no lo devuelve
    activas = await repo.list()
    codigos = {x.codigo for x in activas}
    assert "SOFT_DEL" not in codigos

    # get_by_id con include_deleted lo devuelve
    found = await repo.get_by_id(c.id, include_deleted=True)
    assert found is not None
    assert found.deleted_at is not None
    await session.close()


# ===========================================================================
# Task 8 — EstructuraService
# ===========================================================================


@pytest.mark.asyncio(loop_scope="function")
async def test_service_crear_carrera_exitoso(test_engine, create_tables):
    """Task 8: crear carrera sin conflicto."""
    from app.core.dependencies import CurrentUser

    factory = build_session_factory(test_engine)
    session = factory()
    tid = uuid.uuid4()
    session.add(Tenant(id=tid, nombre="Svc Tenant 1", estado=TenantEstado.ACTIVO))
    await session.commit()

    svc = EstructuraService(
        carrera_repo=CarreraRepository(session=session, tenant_id=tid),
        cohorte_repo=CohorteRepository(session=session, tenant_id=tid),
        materia_repo=MateriaRepository(session=session, tenant_id=tid),
    )
    actor = CurrentUser(user_id=uuid.uuid4(), tenant_id=tid, roles=["ADMIN"])
    carrera = await svc.crear_carrera(actor, "ING_INF", "Ingeniería Informática")
    assert carrera.codigo == "ING_INF"
    assert carrera.tenant_id == tid
    assert carrera.estado == EstadoEstructura.activa
    await session.close()


@pytest.mark.asyncio(loop_scope="function")
async def test_service_crear_carrera_codigo_duplicado_lanza_conflicto(test_engine, create_tables):
    """
    Task 8.1 RED: crear dos carreras con mismo código → ConflictoUnicidad.
    """
    from app.core.dependencies import CurrentUser

    factory = build_session_factory(test_engine)
    session = factory()
    tid = uuid.uuid4()
    session.add(Tenant(id=tid, nombre="Svc Dup Tenant", estado=TenantEstado.ACTIVO))
    await session.commit()

    svc = EstructuraService(
        carrera_repo=CarreraRepository(session=session, tenant_id=tid),
        cohorte_repo=CohorteRepository(session=session, tenant_id=tid),
        materia_repo=MateriaRepository(session=session, tenant_id=tid),
    )
    actor = CurrentUser(user_id=uuid.uuid4(), tenant_id=tid, roles=["ADMIN"])
    await svc.crear_carrera(actor, "DUP_COD", "Carrera Dup 1")

    with pytest.raises(ConflictoUnicidad):
        await svc.crear_carrera(actor, "DUP_COD", "Carrera Dup 2")
    await session.close()


@pytest.mark.asyncio(loop_scope="function")
async def test_service_crear_materia_codigo_duplicado_lanza_conflicto(test_engine, create_tables):
    """
    Task 8.1 RED: crear dos materias con mismo código → ConflictoUnicidad.
    """
    from app.core.dependencies import CurrentUser

    factory = build_session_factory(test_engine)
    session = factory()
    tid = uuid.uuid4()
    session.add(Tenant(id=tid, nombre="Svc Mat Dup Tenant", estado=TenantEstado.ACTIVO))
    await session.commit()

    svc = EstructuraService(
        carrera_repo=CarreraRepository(session=session, tenant_id=tid),
        cohorte_repo=CohorteRepository(session=session, tenant_id=tid),
        materia_repo=MateriaRepository(session=session, tenant_id=tid),
    )
    actor = CurrentUser(user_id=uuid.uuid4(), tenant_id=tid, roles=["ADMIN"])
    await svc.crear_materia(actor, "PROG_DUP", "Prog Dup 1")

    with pytest.raises(ConflictoUnicidad):
        await svc.crear_materia(actor, "PROG_DUP", "Prog Dup 2")
    await session.close()


@pytest.mark.asyncio(loop_scope="function")
async def test_service_crear_cohorte_nombre_duplicado_lanza_conflicto(test_engine, create_tables):
    """
    Task 8.2 RED: crear dos cohortes con mismo (carrera_id, nombre) → ConflictoUnicidad.
    """
    from app.core.dependencies import CurrentUser

    factory = build_session_factory(test_engine)
    session = factory()
    tid = uuid.uuid4()
    session.add(Tenant(id=tid, nombre="Svc Coh Dup Tenant", estado=TenantEstado.ACTIVO))
    await session.commit()

    svc = EstructuraService(
        carrera_repo=CarreraRepository(session=session, tenant_id=tid),
        cohorte_repo=CohorteRepository(session=session, tenant_id=tid),
        materia_repo=MateriaRepository(session=session, tenant_id=tid),
    )
    actor = CurrentUser(user_id=uuid.uuid4(), tenant_id=tid, roles=["ADMIN"])
    carrera = await svc.crear_carrera(actor, "CAR_COH_DUP", "Carrera para Dup Cohorte")

    await svc.crear_cohorte(
        actor, carrera.id, "AGO-2025", 2025, date(2025, 8, 1), None
    )
    with pytest.raises(ConflictoUnicidad):
        await svc.crear_cohorte(
            actor, carrera.id, "AGO-2025", 2025, date(2025, 8, 1), None
        )
    await session.close()


@pytest.mark.asyncio(loop_scope="function")
async def test_service_crear_cohorte_carrera_otro_tenant_rechazado(test_engine, create_tables):
    """
    Task 8.3 RED: cohorte referenciando carrera de otro tenant → CarreraNoEncontrada.
    """
    from app.core.dependencies import CurrentUser

    factory = build_session_factory(test_engine)
    session = factory()

    tid_a = uuid.uuid4()
    tid_b = uuid.uuid4()
    session.add(Tenant(id=tid_a, nombre="Isolation Svc A", estado=TenantEstado.ACTIVO))
    session.add(Tenant(id=tid_b, nombre="Isolation Svc B", estado=TenantEstado.ACTIVO))
    await session.commit()

    # Carrera en tenant B
    repo_b = CarreraRepository(session=session, tenant_id=tid_b)
    actor_b = CurrentUser(user_id=uuid.uuid4(), tenant_id=tid_b, roles=["ADMIN"])
    carrera_b = await repo_b.add(
        Carrera(tenant_id=tid_b, codigo="CAR_B_ISOLATION", nombre="Carrera B")
    )

    # Service del tenant A intenta crear cohorte con carrera de B
    svc_a = EstructuraService(
        carrera_repo=CarreraRepository(session=session, tenant_id=tid_a),
        cohorte_repo=CohorteRepository(session=session, tenant_id=tid_a),
        materia_repo=MateriaRepository(session=session, tenant_id=tid_a),
    )
    actor_a = CurrentUser(user_id=uuid.uuid4(), tenant_id=tid_a, roles=["ADMIN"])

    with pytest.raises(CarreraNoEncontrada):
        await svc_a.crear_cohorte(
            actor_a, carrera_b.id, "COH_X", 2025, date(2025, 1, 1), None
        )
    await session.close()


@pytest.mark.asyncio(loop_scope="function")
async def test_service_cohorte_abierta_bajo_carrera_inactiva_rechazado(
    test_engine, create_tables
):
    """
    Task 8.4 RED: cohorte abierta (vig_hasta=None) bajo carrera Inactiva → CarreraInactiva.
    """
    from app.core.dependencies import CurrentUser

    factory = build_session_factory(test_engine)
    session = factory()
    tid = uuid.uuid4()
    session.add(Tenant(id=tid, nombre="Inactiva Test Tenant", estado=TenantEstado.ACTIVO))
    await session.commit()

    svc = EstructuraService(
        carrera_repo=CarreraRepository(session=session, tenant_id=tid),
        cohorte_repo=CohorteRepository(session=session, tenant_id=tid),
        materia_repo=MateriaRepository(session=session, tenant_id=tid),
    )
    actor = CurrentUser(user_id=uuid.uuid4(), tenant_id=tid, roles=["ADMIN"])
    carrera = await svc.crear_carrera(actor, "CAR_INACT", "Carrera Inactiva Test")
    # Desactivar la carrera (sin cohortes, debe funcionar)
    await svc.editar_carrera(carrera.id, estado=EstadoEstructura.inactiva)

    with pytest.raises(CarreraInactiva):
        await svc.crear_cohorte(
            actor, carrera.id, "COH_OPEN", 2025, date(2025, 1, 1), None
        )
    await session.close()


@pytest.mark.asyncio(loop_scope="function")
async def test_service_cohorte_abierta_bajo_carrera_activa_aceptado(
    test_engine, create_tables
):
    """
    Task 8.4 TRIANGULATE: cohorte abierta bajo carrera Activa → aceptado.
    """
    from app.core.dependencies import CurrentUser

    factory = build_session_factory(test_engine)
    session = factory()
    tid = uuid.uuid4()
    session.add(Tenant(id=tid, nombre="Activa Test Tenant", estado=TenantEstado.ACTIVO))
    await session.commit()

    svc = EstructuraService(
        carrera_repo=CarreraRepository(session=session, tenant_id=tid),
        cohorte_repo=CohorteRepository(session=session, tenant_id=tid),
        materia_repo=MateriaRepository(session=session, tenant_id=tid),
    )
    actor = CurrentUser(user_id=uuid.uuid4(), tenant_id=tid, roles=["ADMIN"])
    carrera = await svc.crear_carrera(actor, "CAR_ACTIVA_OK", "Carrera Activa")

    cohorte = await svc.crear_cohorte(
        actor, carrera.id, "COH_OPEN_OK", 2025, date(2025, 1, 1), None
    )
    assert cohorte.vig_hasta is None
    assert cohorte.estado == EstadoEstructura.activa
    await session.close()


@pytest.mark.asyncio(loop_scope="function")
async def test_service_desactivar_carrera_con_cohortes_abiertas_bloqueado(
    test_engine, create_tables
):
    """
    Task 8.5 RED: desactivar carrera con cohorte abierta → CarreraConCohorteAbiertas (409).
    """
    from app.core.dependencies import CurrentUser

    factory = build_session_factory(test_engine)
    session = factory()
    tid = uuid.uuid4()
    session.add(Tenant(id=tid, nombre="Block Desact Tenant", estado=TenantEstado.ACTIVO))
    await session.commit()

    svc = EstructuraService(
        carrera_repo=CarreraRepository(session=session, tenant_id=tid),
        cohorte_repo=CohorteRepository(session=session, tenant_id=tid),
        materia_repo=MateriaRepository(session=session, tenant_id=tid),
    )
    actor = CurrentUser(user_id=uuid.uuid4(), tenant_id=tid, roles=["ADMIN"])
    carrera = await svc.crear_carrera(actor, "CAR_BLOCK", "Carrera con Cohorte")
    await svc.crear_cohorte(actor, carrera.id, "COH_OPEN_BLOCK", 2025, date(2025, 1, 1), None)

    with pytest.raises(CarreraConCohorteAbiertas):
        await svc.editar_carrera(carrera.id, estado=EstadoEstructura.inactiva)

    # La carrera debe seguir activa
    carrera_after = await svc.obtener_carrera(carrera.id)
    assert carrera_after.estado == EstadoEstructura.activa
    await session.close()


@pytest.mark.asyncio(loop_scope="function")
async def test_service_desactivar_carrera_sin_cohortes_abiertas_ok(
    test_engine, create_tables
):
    """
    Task 8.6 RED: desactivar carrera sin cohortes abiertas → éxito.
    """
    from app.core.dependencies import CurrentUser

    factory = build_session_factory(test_engine)
    session = factory()
    tid = uuid.uuid4()
    session.add(Tenant(id=tid, nombre="Desact Ok Tenant", estado=TenantEstado.ACTIVO))
    await session.commit()

    svc = EstructuraService(
        carrera_repo=CarreraRepository(session=session, tenant_id=tid),
        cohorte_repo=CohorteRepository(session=session, tenant_id=tid),
        materia_repo=MateriaRepository(session=session, tenant_id=tid),
    )
    actor = CurrentUser(user_id=uuid.uuid4(), tenant_id=tid, roles=["ADMIN"])
    carrera = await svc.crear_carrera(actor, "CAR_DESACT_OK", "Sin Cohortes")

    carrera_inact = await svc.editar_carrera(carrera.id, estado=EstadoEstructura.inactiva)
    assert carrera_inact.estado == EstadoEstructura.inactiva
    await session.close()


@pytest.mark.asyncio(loop_scope="function")
async def test_service_editar_cohorte_abierta_bajo_carrera_inactiva_rechazado(
    test_engine, create_tables
):
    """
    Task 8.8 TRIANGULATE: editar cohorte para que quede abierta bajo carrera inactiva → CarreraInactiva.
    """
    from app.core.dependencies import CurrentUser

    factory = build_session_factory(test_engine)
    session = factory()
    tid = uuid.uuid4()
    session.add(Tenant(id=tid, nombre="Edit Coh Inact Tenant", estado=TenantEstado.ACTIVO))
    await session.commit()

    svc = EstructuraService(
        carrera_repo=CarreraRepository(session=session, tenant_id=tid),
        cohorte_repo=CohorteRepository(session=session, tenant_id=tid),
        materia_repo=MateriaRepository(session=session, tenant_id=tid),
    )
    actor = CurrentUser(user_id=uuid.uuid4(), tenant_id=tid, roles=["ADMIN"])
    carrera = await svc.crear_carrera(actor, "CAR_EDIT_INACT", "Car Edit Inact")

    # Crear cohorte CERRADA (vig_hasta != None)
    cohorte = await svc.crear_cohorte(
        actor, carrera.id, "COH_CERRADA", 2025, date(2025, 1, 1), date(2025, 12, 31)
    )

    # Inactivar la carrera (sin cohortes abiertas, debe funcionar)
    await svc.editar_carrera(carrera.id, estado=EstadoEstructura.inactiva)

    # Intentar editar la cohorte para que quede abierta (vig_hasta=None)
    with pytest.raises(CarreraInactiva):
        await svc.editar_cohorte(
            cohorte.id, vig_hasta=None, _vig_hasta_provided=True
        )
    await session.close()


def test_helper_es_cohorte_abierta():
    """
    Task 8.9 REFACTOR: el helper _es_cohorte_abierta es claro y reutilizable.
    """
    assert _es_cohorte_abierta(EstadoEstructura.activa, None) is True
    assert _es_cohorte_abierta(EstadoEstructura.activa, date(2025, 12, 31)) is False
    assert _es_cohorte_abierta(EstadoEstructura.inactiva, None) is False
    assert _es_cohorte_abierta(EstadoEstructura.inactiva, date(2025, 12, 31)) is False


# ===========================================================================
# Task 9 — Schemas Pydantic v2
# ===========================================================================


class TestSchemas:
    """Task 9: schemas con extra='forbid' y validación correcta."""

    def test_carrera_create_valida_bien(self):
        """Task 9.1 RED: CarreraCreate acepta campos correctos."""
        s = CarreraCreate(codigo="ING_INF", nombre="Ingeniería Informática")
        assert s.codigo == "ING_INF"

    def test_carrera_create_rechaza_campo_extra(self):
        """Task 9.1 RED: extra='forbid' rechaza campos no declarados."""
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            CarreraCreate(codigo="X", nombre="Y", tenant_id=str(uuid.uuid4()))

    def test_cohorte_create_exige_anio_y_vig_desde(self):
        """Task 9.2 RED: CohorteCreate exige anio y vig_desde, acepta vig_hasta nulo."""
        from pydantic import ValidationError

        # Falta anio
        with pytest.raises(ValidationError):
            CohorteCreate(
                carrera_id=uuid.uuid4(), nombre="AGO-2025", vig_desde=date(2025, 8, 1)
            )

        # Falta vig_desde
        with pytest.raises(ValidationError):
            CohorteCreate(carrera_id=uuid.uuid4(), nombre="AGO-2025", anio=2025)

        # Correcto con vig_hasta nulo
        s = CohorteCreate(
            carrera_id=uuid.uuid4(),
            nombre="AGO-2025",
            anio=2025,
            vig_desde=date(2025, 8, 1),
        )
        assert s.vig_hasta is None

    def test_cohorte_create_rechaza_campo_extra(self):
        """Task 9.2 RED: extra='forbid' en CohorteCreate."""
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            CohorteCreate(
                carrera_id=uuid.uuid4(),
                nombre="X",
                anio=2025,
                vig_desde=date(2025, 1, 1),
                tenant_id=str(uuid.uuid4()),
            )

    def test_carrera_read_from_orm(self):
        """Task 9.4 TRIANGULATE: CarreraRead.from_attributes funciona desde orm obj."""
        c = Carrera(
            tenant_id=uuid.uuid4(), codigo="READ_TEST", nombre="Read Test",
            estado=EstadoEstructura.activa,
        )
        c.id = uuid.uuid4()
        import datetime as _dt
        c.created_at = _dt.datetime.now(tz=_dt.timezone.utc)
        c.updated_at = _dt.datetime.now(tz=_dt.timezone.utc)

        r = CarreraRead.model_validate(c)
        assert r.codigo == "READ_TEST"
        assert r.estado == EstadoEstructura.activa

    def test_carrera_read_no_expone_tenant_id(self):
        """Task 9.4 TRIANGULATE: CarreraRead no tiene tenant_id como campo editable."""
        fields = set(CarreraRead.model_fields.keys())
        assert "tenant_id" not in fields

    def test_materia_create_rechaza_campo_extra(self):
        """Task 9.1 RED (materia): extra='forbid'."""
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            MateriaCreate(codigo="X", nombre="Y", tenant_id=str(uuid.uuid4()))

    def test_cohorte_read_expone_carrera_id(self):
        """Task 9.4 TRIANGULATE: CohorteRead expone carrera_id (relación explícita)."""
        fields = set(CohorteRead.model_fields.keys())
        assert "carrera_id" in fields
        assert "tenant_id" not in fields


# ===========================================================================
# Task 10 — Endpoints ABM HTTP
# ===========================================================================


@pytest.mark.asyncio(loop_scope="function")
async def test_endpoint_sin_permiso_retorna_403(monkeypatch, estructura_app, estructura_setup):
    """
    Task 10.1 RED: sin permiso estructura:gestionar → 403 en POST /api/v1/admin/carreras.
    """
    monkeypatch.setattr("app.core.security.tokens._settings", _fake_settings)
    s = estructura_setup

    token = _make_jwt(
        tenant_id=s["tid_a"],
        user_id=uuid.uuid4(),
        roles=["NO_PERM_ROLE"],
    )

    async with AsyncClient(
        transport=ASGITransport(app=estructura_app), base_url="http://test"
    ) as client:
        resp = await client.post(
            "/api/v1/admin/carreras",
            json={"codigo": "TEST", "nombre": "Test"},
            headers={"Authorization": f"Bearer {token}"},
        )

    assert resp.status_code == 403, f"Expected 403, got {resp.status_code}: {resp.text}"


@pytest.mark.asyncio(loop_scope="function")
async def test_endpoint_sin_permiso_cohorte_retorna_403(
    monkeypatch, estructura_app, estructura_setup
):
    """
    Task 10.1 RED: sin permiso → 403 en POST /api/v1/admin/cohortes.
    """
    monkeypatch.setattr("app.core.security.tokens._settings", _fake_settings)
    s = estructura_setup

    token = _make_jwt(
        tenant_id=s["tid_a"],
        user_id=uuid.uuid4(),
        roles=["NO_PERM_ROLE"],
    )

    async with AsyncClient(
        transport=ASGITransport(app=estructura_app), base_url="http://test"
    ) as client:
        resp = await client.post(
            "/api/v1/admin/cohortes",
            json={
                "carrera_id": str(uuid.uuid4()),
                "nombre": "X",
                "anio": 2025,
                "vig_desde": "2025-01-01",
            },
            headers={"Authorization": f"Bearer {token}"},
        )

    assert resp.status_code == 403


@pytest.mark.asyncio(loop_scope="function")
async def test_endpoint_sin_permiso_materia_retorna_403(
    monkeypatch, estructura_app, estructura_setup
):
    """
    Task 10.1 RED: sin permiso → 403 en POST /api/v1/admin/materias.
    """
    monkeypatch.setattr("app.core.security.tokens._settings", _fake_settings)
    s = estructura_setup

    token = _make_jwt(
        tenant_id=s["tid_a"],
        user_id=uuid.uuid4(),
        roles=["NO_PERM_ROLE"],
    )

    async with AsyncClient(
        transport=ASGITransport(app=estructura_app), base_url="http://test"
    ) as client:
        resp = await client.post(
            "/api/v1/admin/materias",
            json={"codigo": "X", "nombre": "Y"},
            headers={"Authorization": f"Bearer {token}"},
        )

    assert resp.status_code == 403


@pytest.mark.asyncio(loop_scope="function")
async def test_endpoint_crear_carrera_con_permiso(
    monkeypatch, estructura_app, estructura_setup
):
    """
    Task 10.2 RED→GREEN: con permiso, POST /api/v1/admin/carreras crea carrera → 201.
    """
    monkeypatch.setattr("app.core.security.tokens._settings", _fake_settings)
    s = estructura_setup

    token = _make_jwt(
        tenant_id=s["tid_a"],
        user_id=s["user_admin_a"],
        roles=[s["rol_admin_a"]],
    )

    async with AsyncClient(
        transport=ASGITransport(app=estructura_app), base_url="http://test"
    ) as client:
        resp = await client.post(
            "/api/v1/admin/carreras",
            json={"codigo": "HTTP_CAR_TEST", "nombre": "Carrera HTTP Test"},
            headers={"Authorization": f"Bearer {token}"},
        )

    assert resp.status_code == 201, f"Expected 201, got {resp.status_code}: {resp.text}"
    data = resp.json()
    assert data["codigo"] == "HTTP_CAR_TEST"
    assert data["estado"] == "activa"
    assert "tenant_id" not in data


@pytest.mark.asyncio(loop_scope="function")
async def test_endpoint_listar_carreras_con_permiso(
    monkeypatch, estructura_app, estructura_setup
):
    """
    Task 10.2 RED→GREEN: con permiso, GET /api/v1/admin/carreras → 200.
    """
    monkeypatch.setattr("app.core.security.tokens._settings", _fake_settings)
    s = estructura_setup

    token = _make_jwt(
        tenant_id=s["tid_a"],
        user_id=s["user_admin_a"],
        roles=[s["rol_admin_a"]],
    )

    async with AsyncClient(
        transport=ASGITransport(app=estructura_app), base_url="http://test"
    ) as client:
        resp = await client.get(
            "/api/v1/admin/carreras",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert resp.status_code == 200


@pytest.mark.asyncio(loop_scope="function")
async def test_endpoint_crear_materia_con_permiso(
    monkeypatch, estructura_app, estructura_setup
):
    """
    Task 10.2 RED→GREEN: con permiso, POST /api/v1/admin/materias → 201.
    """
    monkeypatch.setattr("app.core.security.tokens._settings", _fake_settings)
    s = estructura_setup

    token = _make_jwt(
        tenant_id=s["tid_a"],
        user_id=s["user_admin_a"],
        roles=[s["rol_admin_a"]],
    )

    async with AsyncClient(
        transport=ASGITransport(app=estructura_app), base_url="http://test"
    ) as client:
        resp = await client.post(
            "/api/v1/admin/materias",
            json={"codigo": "HTTP_MAT_TEST", "nombre": "Materia HTTP Test"},
            headers={"Authorization": f"Bearer {token}"},
        )

    assert resp.status_code == 201, f"Expected 201, got {resp.status_code}: {resp.text}"
    data = resp.json()
    assert data["codigo"] == "HTTP_MAT_TEST"
    assert "tenant_id" not in data


@pytest.mark.asyncio(loop_scope="function")
async def test_endpoint_crear_cohorte_con_permiso(
    monkeypatch, test_engine, estructura_app, estructura_setup
):
    """
    Task 10.2 RED→GREEN: con permiso, POST /api/v1/admin/cohortes → 201.
    """
    monkeypatch.setattr("app.core.security.tokens._settings", _fake_settings)
    s = estructura_setup

    # Primero crear una carrera para la cohorte
    token = _make_jwt(
        tenant_id=s["tid_a"],
        user_id=s["user_admin_a"],
        roles=[s["rol_admin_a"]],
    )

    async with AsyncClient(
        transport=ASGITransport(app=estructura_app), base_url="http://test"
    ) as client:
        car_resp = await client.post(
            "/api/v1/admin/carreras",
            json={"codigo": "CAR_FOR_COH_HTTP", "nombre": "Carrera para Cohorte HTTP"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert car_resp.status_code == 201
        carrera_id = car_resp.json()["id"]

        coh_resp = await client.post(
            "/api/v1/admin/cohortes",
            json={
                "carrera_id": carrera_id,
                "nombre": "COH_HTTP_TEST",
                "anio": 2025,
                "vig_desde": "2025-08-01",
            },
            headers={"Authorization": f"Bearer {token}"},
        )

    assert coh_resp.status_code == 201, f"Expected 201, got {coh_resp.status_code}: {coh_resp.text}"
    data = coh_resp.json()
    assert data["nombre"] == "COH_HTTP_TEST"
    assert data["vig_hasta"] is None
    assert "tenant_id" not in data


@pytest.mark.asyncio(loop_scope="function")
async def test_endpoint_conflicto_codigo_retorna_409(
    monkeypatch, estructura_app, estructura_setup
):
    """
    Task 10.5 RED: conflicto de unicidad del service → 409 en el endpoint.
    """
    monkeypatch.setattr("app.core.security.tokens._settings", _fake_settings)
    s = estructura_setup

    token = _make_jwt(
        tenant_id=s["tid_a"],
        user_id=s["user_admin_a"],
        roles=[s["rol_admin_a"]],
    )

    async with AsyncClient(
        transport=ASGITransport(app=estructura_app), base_url="http://test"
    ) as client:
        # Primera creación
        r1 = await client.post(
            "/api/v1/admin/carreras",
            json={"codigo": "DUP_HTTP_409", "nombre": "Dup 1"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r1.status_code == 201

        # Segunda con el mismo código → 409
        r2 = await client.post(
            "/api/v1/admin/carreras",
            json={"codigo": "DUP_HTTP_409", "nombre": "Dup 2"},
            headers={"Authorization": f"Bearer {token}"},
        )

    assert r2.status_code == 409, f"Expected 409, got {r2.status_code}: {r2.text}"


@pytest.mark.asyncio(loop_scope="function")
async def test_endpoint_desactivar_carrera_con_cohortes_abiertas_retorna_409(
    monkeypatch, estructura_app, estructura_setup
):
    """
    Task 10.5 RED: intento de desactivar carrera con cohortes abiertas → 409 con mensaje instructivo.
    """
    monkeypatch.setattr("app.core.security.tokens._settings", _fake_settings)
    s = estructura_setup

    token = _make_jwt(
        tenant_id=s["tid_a"],
        user_id=s["user_admin_a"],
        roles=[s["rol_admin_a"]],
    )

    async with AsyncClient(
        transport=ASGITransport(app=estructura_app), base_url="http://test"
    ) as client:
        # Crear carrera
        car_r = await client.post(
            "/api/v1/admin/carreras",
            json={"codigo": "CAR_409_DEACT", "nombre": "Car Deact 409"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert car_r.status_code == 201
        car_id = car_r.json()["id"]

        # Crear cohorte abierta
        coh_r = await client.post(
            "/api/v1/admin/cohortes",
            json={
                "carrera_id": car_id,
                "nombre": "COH_BLOCK_409",
                "anio": 2025,
                "vig_desde": "2025-01-01",
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert coh_r.status_code == 201

        # Intentar desactivar la carrera → 409
        deact_r = await client.patch(
            f"/api/v1/admin/carreras/{car_id}",
            json={"estado": "inactiva"},
            headers={"Authorization": f"Bearer {token}"},
        )

    assert deact_r.status_code == 409, f"Expected 409, got {deact_r.status_code}: {deact_r.text}"
    # El mensaje debe ser instructivo
    detail = deact_r.json()["detail"]
    assert "cohorte" in detail.lower() or "cerrar" in detail.lower() or "inactivar" in detail.lower()


@pytest.mark.asyncio(loop_scope="function")
async def test_endpoint_baja_logica_carrera(
    monkeypatch, estructura_app, estructura_setup
):
    """
    Task 10.6 TRIANGULATE: DELETE /api/v1/admin/carreras/{id} → 204 (baja lógica).
    Después, no aparece en el listado.
    """
    monkeypatch.setattr("app.core.security.tokens._settings", _fake_settings)
    s = estructura_setup

    token = _make_jwt(
        tenant_id=s["tid_a"],
        user_id=s["user_admin_a"],
        roles=[s["rol_admin_a"]],
    )

    async with AsyncClient(
        transport=ASGITransport(app=estructura_app), base_url="http://test"
    ) as client:
        create_r = await client.post(
            "/api/v1/admin/carreras",
            json={"codigo": "CAR_DELETE_204", "nombre": "Delete Test"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert create_r.status_code == 201
        car_id = create_r.json()["id"]

        del_r = await client.delete(
            f"/api/v1/admin/carreras/{car_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert del_r.status_code == 204

        # Ya no aparece en el listado
        list_r = await client.get(
            "/api/v1/admin/carreras",
            headers={"Authorization": f"Bearer {token}"},
        )
        ids = {c["id"] for c in list_r.json()}
        assert car_id not in ids


@pytest.mark.asyncio(loop_scope="function")
async def test_endpoint_aislamiento_tenant_carreras(
    monkeypatch, test_engine, estructura_app, estructura_setup
):
    """
    Task 10.6 TRIANGULATE: usuario del tenant A no ve carreras del tenant B.
    """
    monkeypatch.setattr("app.core.security.tokens._settings", _fake_settings)
    s = estructura_setup

    # Crear carrera en tenant B directamente
    factory = build_session_factory(test_engine)
    session = factory()
    repo_b = CarreraRepository(session=session, tenant_id=s["tid_b"])
    car_b = await repo_b.add(
        Carrera(tenant_id=s["tid_b"], codigo="CAR_ONLY_B_HTTP", nombre="Solo B HTTP")
    )
    await session.close()

    # Listar como usuario de tenant A
    token_a = _make_jwt(
        tenant_id=s["tid_a"],
        user_id=s["user_admin_a"],
        roles=[s["rol_admin_a"]],
    )

    async with AsyncClient(
        transport=ASGITransport(app=estructura_app), base_url="http://test"
    ) as client:
        list_r = await client.get(
            "/api/v1/admin/carreras",
            headers={"Authorization": f"Bearer {token_a}"},
        )

    assert list_r.status_code == 200
    ids = {c["id"] for c in list_r.json()}
    assert str(car_b.id) not in ids, "Tenant A no debe ver carreras del tenant B"
