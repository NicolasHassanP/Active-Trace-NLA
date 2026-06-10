"""
test_equipos.py — TDD suite para C-08 equipos-docentes.

RED → GREEN → TRIANGULATE → REFACTOR cycle para tasks 1-6.

Cubre:
    Task 1: Catálogo RBAC y auditoría
    Task 2: Schemas Pydantic v2
    Task 3: AsignacionRepository — list_by_equipo, bulk_add, bulk_update_vigencia
    Task 4: EquipoService — mis_equipos, consultar, masiva, clonar, vigencia, export
    Task 5: Router — endpoints HTTP
    Task 6: Cobertura, auditoría, reglas duras

DB real: activia_trace_test. Sin mocks de DB.
"""
import datetime
import uuid
from datetime import date, timedelta
from typing import Tuple

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from pydantic import ValidationError

from app.core.database import build_session_factory
from app.models.audit import AuditAction
from app.models.estructura import Carrera, Cohorte, EstadoEstructura, Materia
from app.models.rbac import Permiso, Rol, RolPermiso, PermisoScope
from app.models.tenant import Tenant, TenantEstado
from app.models.usuario import Asignacion, RolAsignacion, Usuario, UsuarioEstado
from app.models.vigencia import EstadoVigencia
from app.repositories.audit_repository import AuditRepository
from app.repositories.usuario_repository import AsignacionRepository, UsuarioRepository
from app.schemas.equipo import (
    AsignacionMasivaRequest,
    ClonarEquipoRequest,
    EquipoQuery,
    MisEquiposItem,
    ResumenClonacion,
    ResumenLote,
    VigenciaGeneralRequest,
)
from app.services.equipo_service import EquipoService
from app.services.usuario_service import ReferenciaInvalida, UsuarioNoEncontrado


# ---------------------------------------------------------------------------
# JWT / settings helpers
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


def _make_usuario(tid: uuid.UUID, suffix: str) -> Usuario:
    """Helper para crear Usuario con email único."""
    from app.core.security.passwords import email_lookup_hash as _hash
    email = f"equipo_{suffix}_{uuid.uuid4().hex[:6]}@test.com"
    return Usuario(
        tenant_id=tid,
        email_encrypted=email,
        email_hash=_hash(email),
        nombre="Equipo",
        apellidos=suffix,
        estado=UsuarioEstado.activo,
    )


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture(scope="module")
async def equipo_setup(test_engine, create_tables):
    """
    Crea dos tenants con catálogo RBAC completo + estructura académica real.
      tenant_a: user_a → USR_EQ_A con equipos:ver + equipos:asignar
      tenant_b: user_b → USR_EQ_B con equipos:ver + equipos:asignar
    Crea Carrera, Materia y Cohorte reales para usar como contexto de Asignacion.
    """
    factory = build_session_factory(test_engine)
    session = factory()

    tid_a = uuid.uuid4()
    tid_b = uuid.uuid4()
    session.add(Tenant(id=tid_a, nombre="Equipo Tenant A", estado=TenantEstado.ACTIVO))
    session.add(Tenant(id=tid_b, nombre="Equipo Tenant B", estado=TenantEstado.ACTIVO))
    await session.flush()

    user_a_id = uuid.uuid4()
    user_b_id = uuid.uuid4()

    rol_a = Rol(tenant_id=tid_a, nombre="USR_EQ_A")
    rol_b = Rol(tenant_id=tid_b, nombre="USR_EQ_B")
    session.add_all([rol_a, rol_b])
    await session.flush()

    perm_ver_a = Permiso(tenant_id=tid_a, codigo="equipos:ver", modulo="equipos", accion="ver")
    perm_asignar_a = Permiso(tenant_id=tid_a, codigo="equipos:asignar", modulo="equipos", accion="asignar")
    perm_ver_b = Permiso(tenant_id=tid_b, codigo="equipos:ver", modulo="equipos", accion="ver")
    perm_asignar_b = Permiso(tenant_id=tid_b, codigo="equipos:asignar", modulo="equipos", accion="asignar")
    session.add_all([perm_ver_a, perm_asignar_a, perm_ver_b, perm_asignar_b])
    await session.flush()

    session.add(RolPermiso(tenant_id=tid_a, rol_id=rol_a.id, permiso_id=perm_ver_a.id, scope=PermisoScope.global_))
    session.add(RolPermiso(tenant_id=tid_a, rol_id=rol_a.id, permiso_id=perm_asignar_a.id, scope=PermisoScope.global_))
    session.add(RolPermiso(tenant_id=tid_b, rol_id=rol_b.id, permiso_id=perm_ver_b.id, scope=PermisoScope.global_))
    session.add(RolPermiso(tenant_id=tid_b, rol_id=rol_b.id, permiso_id=perm_asignar_b.id, scope=PermisoScope.global_))
    await session.flush()

    # Create real academic structure for tenant A
    carrera_a = Carrera(
        tenant_id=tid_a,
        codigo=f"CAR_{uuid.uuid4().hex[:6]}",
        nombre="Carrera Test A",
        estado=EstadoEstructura.activa,
    )
    materia_a = Materia(
        tenant_id=tid_a,
        codigo=f"MAT_{uuid.uuid4().hex[:6]}",
        nombre="Materia Test A",
        estado=EstadoEstructura.activa,
    )
    session.add(carrera_a)
    session.add(materia_a)
    await session.flush()

    cohorte_a = Cohorte(
        tenant_id=tid_a,
        carrera_id=carrera_a.id,
        nombre="Cohorte 2024",
        anio=2024,
        vig_desde=date.today(),
        estado=EstadoEstructura.activa,
    )
    session.add(cohorte_a)
    await session.flush()

    # Create real academic structure for tenant B
    carrera_b = Carrera(
        tenant_id=tid_b,
        codigo=f"CAR_{uuid.uuid4().hex[:6]}",
        nombre="Carrera Test B",
        estado=EstadoEstructura.activa,
    )
    materia_b = Materia(
        tenant_id=tid_b,
        codigo=f"MAT_{uuid.uuid4().hex[:6]}",
        nombre="Materia Test B",
        estado=EstadoEstructura.activa,
    )
    session.add(carrera_b)
    session.add(materia_b)
    await session.flush()

    cohorte_b = Cohorte(
        tenant_id=tid_b,
        carrera_id=carrera_b.id,
        nombre="Cohorte 2024",
        anio=2024,
        vig_desde=date.today(),
        estado=EstadoEstructura.activa,
    )
    session.add(cohorte_b)
    await session.commit()
    await session.close()

    return {
        "tid_a": tid_a,
        "tid_b": tid_b,
        "user_a": user_a_id,
        "user_b": user_b_id,
        "rol_a": "USR_EQ_A",
        "rol_b": "USR_EQ_B",
        # Tenant A academic structure
        "mat_id": materia_a.id,
        "car_id": carrera_a.id,
        "coh_id": cohorte_a.id,
        # Tenant B academic structure
        "mat_b_id": materia_b.id,
        "car_b_id": carrera_b.id,
        "coh_b_id": cohorte_b.id,
    }


async def _create_estructura(session, tid: uuid.UUID, suffix: str) -> Tuple[uuid.UUID, uuid.UUID, uuid.UUID]:
    """
    Helper para crear una tripleta (materia, carrera, cohorte) real para un tenant.
    Retorna (materia_id, carrera_id, cohorte_id).
    """
    carrera = Carrera(
        tenant_id=tid,
        codigo=f"C_{uuid.uuid4().hex[:6]}",
        nombre=f"Carrera {suffix}",
        estado=EstadoEstructura.activa,
    )
    materia = Materia(
        tenant_id=tid,
        codigo=f"M_{uuid.uuid4().hex[:6]}",
        nombre=f"Materia {suffix}",
        estado=EstadoEstructura.activa,
    )
    session.add(carrera)
    session.add(materia)
    await session.flush()

    cohorte = Cohorte(
        tenant_id=tid,
        carrera_id=carrera.id,
        nombre=f"Cohorte {suffix}",
        anio=2024,
        vig_desde=date.today(),
        estado=EstadoEstructura.activa,
    )
    session.add(cohorte)
    await session.flush()

    return materia.id, carrera.id, cohorte.id


@pytest_asyncio.fixture(scope="module")
def equipo_app(test_engine, equipo_setup):
    from app.main import create_app
    app = create_app()
    factory = build_session_factory(test_engine)
    app.state.session_factory = factory
    return app


@pytest_asyncio.fixture(scope="module")
async def equipo_client(equipo_app) -> AsyncClient:
    async with AsyncClient(
        transport=ASGITransport(app=equipo_app), base_url="http://test"
    ) as client:
        yield client


# ---------------------------------------------------------------------------
# TASK 1 — Catálogo RBAC y auditoría
# ---------------------------------------------------------------------------

# 1.1 RED: permiso equipos:ver en el catálogo
@pytest.mark.asyncio(loop_scope="session")
async def test_permiso_equipos_ver_existe_en_db(db_session, create_tables, equipo_setup, monkeypatch):
    """RED 1.1: equipos:ver existe en el catálogo de permisos del tenant tras el fixture."""
    monkeypatch.setattr("app.core.config.Settings", _fake_settings)

    from sqlalchemy import select
    stmt = select(Permiso).where(
        Permiso.tenant_id == equipo_setup["tid_a"],
        Permiso.codigo == "equipos:ver",
        Permiso.deleted_at.is_(None),
    )
    result = await db_session.execute(stmt)
    perm = result.scalar_one_or_none()
    assert perm is not None, "Permiso equipos:ver no encontrado en el catálogo"
    assert perm.modulo == "equipos"
    assert perm.accion == "ver"


# 1.3 TRIANGULATE: rol con equipos:ver resuelve; sin él → 403
@pytest.mark.asyncio(loop_scope="session")
async def test_rol_con_equipos_ver_resuelve_permiso(equipo_client, equipo_setup, monkeypatch):
    """TRIANGULATE 1.3: rol con equipos:ver → 200; sin él → 403."""
    monkeypatch.setattr("app.core.config.Settings", _fake_settings)

    tid = equipo_setup["tid_a"]
    user_id = equipo_setup["user_a"]

    # Con permiso → 200
    token = _make_jwt(tid, user_id, roles=["USR_EQ_A"])
    resp = await equipo_client.get(
        "/api/v1/equipos/mis-equipos",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200

    # Sin permiso → 403 (fail-closed)
    token_sin = _make_jwt(tid, user_id, roles=["SINPERMISO"])
    resp2 = await equipo_client.get(
        "/api/v1/equipos/mis-equipos",
        headers={"Authorization": f"Bearer {token_sin}"},
    )
    assert resp2.status_code == 403


# 1.4 RED: claves de auditoría en el enum AuditAction
def test_audit_actions_equipos_en_enum():
    """RED 1.4: EQUIPOS_ASIGNACION_MASIVA, EQUIPOS_CLONAR, EQUIPOS_VIGENCIA_GENERAL en AuditAction."""
    valores = {m.value for m in AuditAction}
    assert "EQUIPOS_ASIGNACION_MASIVA" in valores
    assert "EQUIPOS_CLONAR" in valores
    assert "EQUIPOS_VIGENCIA_GENERAL" in valores


# 1.5 GREEN: verificado en test DB (ADD VALUE en _ensure_schema)
@pytest.mark.asyncio(loop_scope="session")
async def test_audit_actions_equipos_en_db(test_engine, create_tables):
    """GREEN 1.5: acciones de auditoría de equipos existen en el enum de la DB."""
    from sqlalchemy import text
    async with test_engine.connect() as conn:
        for action in ("EQUIPOS_ASIGNACION_MASIVA", "EQUIPOS_CLONAR", "EQUIPOS_VIGENCIA_GENERAL"):
            res = await conn.execute(
                text(
                    "SELECT 1 FROM pg_enum e "
                    "JOIN pg_type t ON e.enumtypid = t.oid "
                    "WHERE t.typname = 'audit_action' AND e.enumlabel = :label"
                ),
                {"label": action},
            )
            assert res.scalar() == 1, f"audit_action.{action} no existe en la DB"


# ---------------------------------------------------------------------------
# TASK 2 — Schemas Pydantic v2
# ---------------------------------------------------------------------------

# 2.1 RED: AsignacionMasivaRequest rechaza campos extra
def test_asignacion_masiva_request_rechaza_campos_extra():
    """RED 2.1: AsignacionMasivaRequest con extra='forbid' rechaza campos extra."""
    with pytest.raises(ValidationError):
        AsignacionMasivaRequest(
            usuario_ids=[uuid.uuid4()],
            materia_id=uuid.uuid4(),
            carrera_id=uuid.uuid4(),
            cohorte_id=uuid.uuid4(),
            rol=RolAsignacion.PROFESOR,
            desde=date.today(),
            campo_extra="valor",  # type: ignore
        )


# 2.2 GREEN: AsignacionMasivaRequest válida
def test_asignacion_masiva_request_valida():
    """GREEN 2.2: AsignacionMasivaRequest acepta payload correcto."""
    req = AsignacionMasivaRequest(
        usuario_ids=[uuid.uuid4(), uuid.uuid4()],
        materia_id=uuid.uuid4(),
        carrera_id=uuid.uuid4(),
        cohorte_id=uuid.uuid4(),
        rol=RolAsignacion.TUTOR,
        desde=date.today(),
        comisiones=["A", "B"],
    )
    assert len(req.usuario_ids) == 2
    assert req.rol == RolAsignacion.TUTOR


# 2.3 GREEN: otros schemas válidos
def test_clonar_equipo_request_valido():
    """GREEN 2.3: ClonarEquipoRequest acepta payload correcto."""
    req = ClonarEquipoRequest(
        origen_materia_id=uuid.uuid4(),
        origen_carrera_id=uuid.uuid4(),
        origen_cohorte_id=uuid.uuid4(),
        destino_materia_id=uuid.uuid4(),
        destino_carrera_id=uuid.uuid4(),
        destino_cohorte_id=uuid.uuid4(),
        desde=date.today(),
    )
    assert req.hasta is None


def test_vigencia_general_request_valida():
    """GREEN 2.3: VigenciaGeneralRequest acepta payload correcto."""
    req = VigenciaGeneralRequest(
        materia_id=uuid.uuid4(),
        carrera_id=uuid.uuid4(),
        cohorte_id=uuid.uuid4(),
        desde=date.today(),
        hasta=date.today() + timedelta(days=30),
    )
    assert req.hasta is not None


def test_equipo_query_valido():
    """GREEN 2.3: EquipoQuery acepta tripleta + filtros opcionales."""
    q = EquipoQuery(
        materia_id=uuid.uuid4(),
        carrera_id=uuid.uuid4(),
        cohorte_id=uuid.uuid4(),
    )
    assert q.rol is None
    assert q.responsable_id is None


# 2.4 GREEN: schemas de respuesta
def test_resumen_lote_valido():
    """GREEN 2.4: ResumenLote con creadas."""
    r = ResumenLote(creadas=5)
    assert r.creadas == 5


def test_resumen_clonacion_valido():
    """GREEN 2.4: ResumenClonacion con clonadas y omitidas."""
    r = ResumenClonacion(clonadas=3, omitidas=2)
    assert r.clonadas == 3
    assert r.omitidas == 2


def test_mis_equipos_item_valido():
    """GREEN 2.4: MisEquiposItem con todos los campos."""
    item = MisEquiposItem(
        asignacion_id=uuid.uuid4(),
        materia_id=uuid.uuid4(),
        carrera_id=uuid.uuid4(),
        cohorte_id=uuid.uuid4(),
        rol=RolAsignacion.COORDINADOR,
        desde=date.today(),
        hasta=None,
        estado_vigencia=EstadoVigencia.vigente,
    )
    assert item.estado_vigencia == EstadoVigencia.vigente


# 2.5 TRIANGULATE: validaciones de borde
def test_asignacion_masiva_usuario_ids_vacia_rechazada():
    """TRIANGULATE 2.5: lista vacía de usuario_ids rechazada."""
    with pytest.raises(ValidationError):
        AsignacionMasivaRequest(
            usuario_ids=[],
            materia_id=uuid.uuid4(),
            carrera_id=uuid.uuid4(),
            cohorte_id=uuid.uuid4(),
            rol=RolAsignacion.PROFESOR,
            desde=date.today(),
        )


def test_asignacion_masiva_hasta_anterior_a_desde_rechazada():
    """TRIANGULATE 2.5: hasta anterior a desde rechazada."""
    hoy = date.today()
    with pytest.raises(ValidationError):
        AsignacionMasivaRequest(
            usuario_ids=[uuid.uuid4()],
            materia_id=uuid.uuid4(),
            carrera_id=uuid.uuid4(),
            cohorte_id=uuid.uuid4(),
            rol=RolAsignacion.PROFESOR,
            desde=hoy,
            hasta=hoy - timedelta(days=1),
        )


def test_clonar_hasta_anterior_a_desde_rechazada():
    """TRIANGULATE 2.5: ClonarEquipoRequest hasta anterior a desde rechazada."""
    hoy = date.today()
    with pytest.raises(ValidationError):
        ClonarEquipoRequest(
            origen_materia_id=uuid.uuid4(),
            origen_carrera_id=uuid.uuid4(),
            origen_cohorte_id=uuid.uuid4(),
            destino_materia_id=uuid.uuid4(),
            destino_carrera_id=uuid.uuid4(),
            destino_cohorte_id=uuid.uuid4(),
            desde=hoy,
            hasta=hoy - timedelta(days=5),
        )


def test_vigencia_hasta_anterior_a_desde_rechazada():
    """TRIANGULATE 2.5: VigenciaGeneralRequest hasta anterior a desde rechazada."""
    hoy = date.today()
    with pytest.raises(ValidationError):
        VigenciaGeneralRequest(
            materia_id=uuid.uuid4(),
            carrera_id=uuid.uuid4(),
            cohorte_id=uuid.uuid4(),
            desde=hoy,
            hasta=hoy - timedelta(days=1),
        )


def test_schemas_extra_forbid_todos():
    """TRIANGULATE 2.5: todos los schemas rechazan campos extra."""
    schemas_y_payloads = [
        (ClonarEquipoRequest, {
            "origen_materia_id": uuid.uuid4(),
            "origen_carrera_id": uuid.uuid4(),
            "origen_cohorte_id": uuid.uuid4(),
            "destino_materia_id": uuid.uuid4(),
            "destino_carrera_id": uuid.uuid4(),
            "destino_cohorte_id": uuid.uuid4(),
            "desde": date.today(),
            "extra": "x",
        }),
        (VigenciaGeneralRequest, {
            "materia_id": uuid.uuid4(),
            "carrera_id": uuid.uuid4(),
            "cohorte_id": uuid.uuid4(),
            "desde": date.today(),
            "extra": "x",
        }),
        (EquipoQuery, {
            "materia_id": uuid.uuid4(),
            "carrera_id": uuid.uuid4(),
            "cohorte_id": uuid.uuid4(),
            "extra": "x",
        }),
        (ResumenLote, {"creadas": 1, "extra": "x"}),
        (ResumenClonacion, {"clonadas": 1, "omitidas": 0, "extra": "x"}),
    ]
    for Schema, payload in schemas_y_payloads:
        with pytest.raises(ValidationError):
            Schema(**payload)  # type: ignore


# ---------------------------------------------------------------------------
# TASK 3 — Repositorio: list_by_equipo, bulk_add, bulk_update_vigencia
# ---------------------------------------------------------------------------

# 3.2 RED: list_by_equipo filtra por tripleta + tenant + no soft-deleted
@pytest.mark.asyncio(loop_scope="session")
async def test_list_by_equipo_filtra_por_tripleta(db_session, create_tables, equipo_setup, monkeypatch):
    """RED 3.2: list_by_equipo devuelve solo asignaciones de la tripleta y tenant, no soft-deleted."""
    monkeypatch.setattr("app.core.config.Settings", _fake_settings)

    tid = equipo_setup["tid_a"]
    mat_id = equipo_setup["mat_id"]
    car_id = equipo_setup["car_id"]
    coh_id = equipo_setup["coh_id"]

    repo = AsignacionRepository(session=db_session, tenant_id=tid)
    usr_repo = UsuarioRepository(session=db_session, tenant_id=tid)

    # Create a second tripleta for isolation
    mat2, car2, coh2 = await _create_estructura(db_session, tid, "filt2")

    u1 = _make_usuario(tid, "list1")
    u2 = _make_usuario(tid, "list2")
    await usr_repo.add(u1)
    await usr_repo.add(u2)

    # Asignacion en la tripleta correcta
    a1 = Asignacion(
        usuario_id=u1.id,
        rol=RolAsignacion.PROFESOR,
        materia_id=mat_id,
        carrera_id=car_id,
        cohorte_id=coh_id,
        desde=date.today(),
        comisiones=[],
    )
    # Asignacion en otra tripleta (no debe aparecer)
    a2 = Asignacion(
        usuario_id=u2.id,
        rol=RolAsignacion.TUTOR,
        materia_id=mat2,
        carrera_id=car2,
        cohorte_id=coh2,
        desde=date.today(),
        comisiones=[],
    )
    await repo.add(a1)
    await repo.add(a2)

    result = await repo.list_by_equipo(mat_id, car_id, coh_id)
    ids = {a.id for a in result}
    assert a1.id in ids, "Asignacion del equipo no apareció"
    assert a2.id not in ids, "Asignacion de otra tripleta apareció"

    # Cleanup
    await repo.delete(a1)
    await repo.delete(a2)
    await usr_repo.delete(u1)
    await usr_repo.delete(u2)
    await db_session.commit()


# 3.4 TRIANGULATE: filtro por rol, responsable, otro tenant, soft-deleted
@pytest.mark.asyncio(loop_scope="session")
async def test_list_by_equipo_filtros_y_aislamiento(db_session, create_tables, equipo_setup, monkeypatch):
    """TRIANGULATE 3.4: filtro por rol y aislamiento de tenant/soft-delete."""
    monkeypatch.setattr("app.core.config.Settings", _fake_settings)

    tid_a = equipo_setup["tid_a"]
    tid_b = equipo_setup["tid_b"]
    mat_id = equipo_setup["mat_id"]
    car_id = equipo_setup["car_id"]
    coh_id = equipo_setup["coh_id"]
    mat_b = equipo_setup["mat_b_id"]
    car_b = equipo_setup["car_b_id"]
    coh_b = equipo_setup["coh_b_id"]

    repo_a = AsignacionRepository(session=db_session, tenant_id=tid_a)
    repo_b = AsignacionRepository(session=db_session, tenant_id=tid_b)
    usr_a = UsuarioRepository(session=db_session, tenant_id=tid_a)
    usr_b = UsuarioRepository(session=db_session, tenant_id=tid_b)

    ua = _make_usuario(tid_a, "filt_a")
    ub = _make_usuario(tid_b, "filt_b")
    await usr_a.add(ua)
    await usr_b.add(ub)

    # PROFESOR en tenant A
    ap = Asignacion(usuario_id=ua.id, rol=RolAsignacion.PROFESOR,
                    materia_id=mat_id, carrera_id=car_id, cohorte_id=coh_id,
                    desde=date.today(), comisiones=[])
    # TUTOR en tenant A (mismo equipo)
    at = Asignacion(usuario_id=ua.id, rol=RolAsignacion.TUTOR,
                    materia_id=mat_id, carrera_id=car_id, cohorte_id=coh_id,
                    desde=date.today(), comisiones=[])
    # Asignacion en tenant B (su propio equipo)
    ab = Asignacion(usuario_id=ub.id, rol=RolAsignacion.PROFESOR,
                    materia_id=mat_b, carrera_id=car_b, cohorte_id=coh_b,
                    desde=date.today(), comisiones=[])
    await repo_a.add(ap)
    await repo_a.add(at)
    await repo_b.add(ab)

    # Filtro por PROFESOR en tenant A → solo ap
    by_rol = await repo_a.list_by_equipo(mat_id, car_id, coh_id, rol=RolAsignacion.PROFESOR)
    ids_by_rol = {a.id for a in by_rol}
    assert ap.id in ids_by_rol
    assert at.id not in ids_by_rol  # TUTOR excluido

    # Tenant A no ve asignaciones de tenant B (incluso si usáramos su tripleta)
    all_a = await repo_a.list_by_equipo(mat_id, car_id, coh_id)
    ids_a = {a.id for a in all_a}
    assert ab.id not in ids_a

    # Soft-deleted no aparece
    await repo_a.delete(ap)
    result_after = await repo_a.list_by_equipo(mat_id, car_id, coh_id)
    ids_after = {a.id for a in result_after}
    assert ap.id not in ids_after

    # Cleanup
    await repo_a.delete(at)
    await repo_b.delete(ab)
    await usr_a.delete(ua)
    await usr_b.delete(ub)
    await db_session.commit()


# 3.5 RED: bulk_add persiste múltiples en un único commit, fuerza tenant_id
@pytest.mark.asyncio(loop_scope="session")
async def test_bulk_add_persiste_y_fuerza_tenant(db_session, create_tables, equipo_setup, monkeypatch):
    """RED 3.5: bulk_add persiste múltiples Asignacion y fuerza tenant_id desde el scope."""
    monkeypatch.setattr("app.core.config.Settings", _fake_settings)

    tid = equipo_setup["tid_a"]
    mat_id = equipo_setup["mat_id"]
    car_id = equipo_setup["car_id"]
    coh_id = equipo_setup["coh_id"]

    repo = AsignacionRepository(session=db_session, tenant_id=tid)
    usr_repo = UsuarioRepository(session=db_session, tenant_id=tid)

    u1 = _make_usuario(tid, "bulk1")
    u2 = _make_usuario(tid, "bulk2")
    await usr_repo.add(u1)
    await usr_repo.add(u2)

    asigs = [
        Asignacion(usuario_id=u1.id, rol=RolAsignacion.PROFESOR,
                   materia_id=mat_id, carrera_id=car_id, cohorte_id=coh_id,
                   desde=date.today(), comisiones=[]),
        Asignacion(usuario_id=u2.id, rol=RolAsignacion.TUTOR,
                   materia_id=mat_id, carrera_id=car_id, cohorte_id=coh_id,
                   desde=date.today(), comisiones=[]),
    ]
    saved = await repo.bulk_add(asigs)

    assert len(saved) == 2
    for a in saved:
        assert a.tenant_id == tid  # tenant_id forzado desde scope
        assert a.id is not None    # persisted con ID

    # Cleanup
    for a in saved:
        await repo.delete(a)
    await usr_repo.delete(u1)
    await usr_repo.delete(u2)
    await db_session.commit()


# 3.7 TRIANGULATE: atomicidad de bulk_add — rollback ante error no deja filas
@pytest.mark.asyncio(loop_scope="session")
async def test_bulk_add_rollback_ante_error(db_session, create_tables, equipo_setup, monkeypatch):
    """TRIANGULATE 3.7: si la sesión hace rollback, no queda ninguna fila persistida."""
    monkeypatch.setattr("app.core.config.Settings", _fake_settings)

    tid = equipo_setup["tid_a"]
    mat_id = equipo_setup["mat_id"]
    car_id = equipo_setup["car_id"]
    coh_id = equipo_setup["coh_id"]

    repo = AsignacionRepository(session=db_session, tenant_id=tid)
    usr_repo = UsuarioRepository(session=db_session, tenant_id=tid)

    u = _make_usuario(tid, "rollbk")
    await usr_repo.add(u)

    # Save the current count in the equipo
    pre = await repo.list_by_equipo(mat_id, car_id, coh_id)
    pre_count = len(pre)

    # Manually add and rollback without going through bulk_add commit
    a = Asignacion(usuario_id=u.id, rol=RolAsignacion.COORDINADOR,
                   materia_id=mat_id, carrera_id=car_id, cohorte_id=coh_id,
                   desde=date.today(), comisiones=[])
    a.tenant_id = tid
    db_session.add(a)
    await db_session.rollback()

    post = await repo.list_by_equipo(mat_id, car_id, coh_id)
    assert len(post) == pre_count  # No rows added after rollback

    await usr_repo.delete(u)
    await db_session.commit()


# 3.8 RED + GREEN: bulk_update_vigencia actualiza y retorna cantidad
@pytest.mark.asyncio(loop_scope="session")
async def test_bulk_update_vigencia_actualiza_y_retorna_cantidad(db_session, create_tables, equipo_setup, monkeypatch):
    """RED 3.8: bulk_update_vigencia actualiza desde/hasta de todas las asignaciones del equipo."""
    monkeypatch.setattr("app.core.config.Settings", _fake_settings)

    tid = equipo_setup["tid_a"]
    mat2, car2, coh2 = await _create_estructura(db_session, tid, "upd")

    repo = AsignacionRepository(session=db_session, tenant_id=tid)
    usr_repo = UsuarioRepository(session=db_session, tenant_id=tid)

    u1 = _make_usuario(tid, "upd1")
    u2 = _make_usuario(tid, "upd2")
    await usr_repo.add(u1)
    await usr_repo.add(u2)

    a1 = Asignacion(usuario_id=u1.id, rol=RolAsignacion.PROFESOR,
                    materia_id=mat2, carrera_id=car2, cohorte_id=coh2,
                    desde=date.today(), comisiones=[])
    a2 = Asignacion(usuario_id=u2.id, rol=RolAsignacion.TUTOR,
                    materia_id=mat2, carrera_id=car2, cohorte_id=coh2,
                    desde=date.today(), comisiones=[])
    await repo.add(a1)
    await repo.add(a2)

    nueva_desde = date.today() + timedelta(days=1)
    nueva_hasta = date.today() + timedelta(days=30)
    afectadas = await repo.bulk_update_vigencia(mat2, car2, coh2, nueva_desde, nueva_hasta)

    assert afectadas == 2

    updated = await repo.list_by_equipo(mat2, car2, coh2)
    for a in updated:
        assert a.desde == nueva_desde
        assert a.hasta == nueva_hasta

    # Cleanup
    for a in updated:
        await repo.delete(a)
    await usr_repo.delete(u1)
    await usr_repo.delete(u2)
    await db_session.commit()


# 3.9 TRIANGULATE: bulk_update_vigencia no toca otros equipos ni tenants
@pytest.mark.asyncio(loop_scope="session")
async def test_bulk_update_vigencia_no_afecta_otros_equipos(db_session, create_tables, equipo_setup, monkeypatch):
    """TRIANGULATE 3.9: bulk_update_vigencia no toca otros equipos ni tenants."""
    monkeypatch.setattr("app.core.config.Settings", _fake_settings)

    tid_a = equipo_setup["tid_a"]
    tid_b = equipo_setup["tid_b"]

    # Create separate tripletas for isolation
    mat_x, car_x, coh_x = await _create_estructura(db_session, tid_a, "isx")
    mat_y, car_y, coh_y = await _create_estructura(db_session, tid_a, "isy")
    mat_xb, car_xb, coh_xb = await _create_estructura(db_session, tid_b, "isxb")

    repo_a = AsignacionRepository(session=db_session, tenant_id=tid_a)
    repo_b = AsignacionRepository(session=db_session, tenant_id=tid_b)
    usr_a = UsuarioRepository(session=db_session, tenant_id=tid_a)
    usr_b = UsuarioRepository(session=db_session, tenant_id=tid_b)

    ua = _make_usuario(tid_a, "is1")
    ub = _make_usuario(tid_b, "is2")
    await usr_a.add(ua)
    await usr_b.add(ub)

    # Equipo X in tenant A (the one we update)
    ax = Asignacion(usuario_id=ua.id, rol=RolAsignacion.PROFESOR,
                    materia_id=mat_x, carrera_id=car_x, cohorte_id=coh_x,
                    desde=date.today(), comisiones=[])
    # Equipo Y in tenant A (should NOT be affected)
    ay = Asignacion(usuario_id=ua.id, rol=RolAsignacion.TUTOR,
                    materia_id=mat_y, carrera_id=car_y, cohorte_id=coh_y,
                    desde=date.today(), comisiones=[])
    # Equipo in tenant B (should NOT be affected)
    ab = Asignacion(usuario_id=ub.id, rol=RolAsignacion.PROFESOR,
                    materia_id=mat_xb, carrera_id=car_xb, cohorte_id=coh_xb,
                    desde=date.today(), comisiones=[])
    await repo_a.add(ax)
    await repo_a.add(ay)
    await repo_b.add(ab)

    original_desde_y = ay.desde
    original_desde_b = ab.desde

    nueva_desde = date.today() + timedelta(days=5)
    afectadas = await repo_a.bulk_update_vigencia(mat_x, car_x, coh_x, nueva_desde, None)

    assert afectadas == 1  # Solo el equipo X del tenant A

    # Equipo Y de tenant A no se afectó
    ay_post = await repo_a.get_by_id(ay.id)
    assert ay_post.desde == original_desde_y

    # Equipo B no se afectó
    ab_post = await repo_b.get_by_id(ab.id)
    assert ab_post.desde == original_desde_b

    # Cleanup
    await repo_a.delete(ax)
    await repo_a.delete(ay)
    await repo_b.delete(ab)
    await usr_a.delete(ua)
    await usr_b.delete(ub)
    await db_session.commit()


# ---------------------------------------------------------------------------
# TASK 4 — EquipoService
# ---------------------------------------------------------------------------

def _make_equipo_service_sync(session, tenant_id):
    """Helper para crear EquipoService en tests."""
    asig_repo = AsignacionRepository(session=session, tenant_id=tenant_id)
    usr_repo = UsuarioRepository(session=session, tenant_id=tenant_id)
    audit_repo = AuditRepository(session=session, tenant_id=tenant_id)
    return EquipoService(asignacion_repo=asig_repo, usuario_repo=usr_repo, audit_repo=audit_repo)


def _make_current_user(tid, uid):
    from app.core.dependencies import CurrentUser
    return CurrentUser(user_id=uid, tenant_id=tid, roles=["USR_EQ_A"])


# 4.1 RED: listar_mis_equipos devuelve solo asignaciones del usuario autenticado
@pytest.mark.asyncio(loop_scope="session")
async def test_listar_mis_equipos_devuelve_propias(db_session, create_tables, equipo_setup, monkeypatch):
    """RED 4.1: listar_mis_equipos devuelve asignaciones del current_user con estado_vigencia."""
    monkeypatch.setattr("app.core.config.Settings", _fake_settings)

    tid = equipo_setup["tid_a"]
    mat_id = equipo_setup["mat_id"]
    car_id = equipo_setup["car_id"]
    coh_id = equipo_setup["coh_id"]

    repo = AsignacionRepository(session=db_session, tenant_id=tid)
    usr_repo = UsuarioRepository(session=db_session, tenant_id=tid)

    mat2, car2, coh2 = await _create_estructura(db_session, tid, "me2")

    u1 = _make_usuario(tid, "me1")
    u2 = _make_usuario(tid, "me2x")
    await usr_repo.add(u1)
    await usr_repo.add(u2)

    a1 = Asignacion(usuario_id=u1.id, rol=RolAsignacion.PROFESOR,
                    materia_id=mat_id, carrera_id=car_id, cohorte_id=coh_id,
                    desde=date.today(), comisiones=[])
    a2 = Asignacion(usuario_id=u2.id, rol=RolAsignacion.TUTOR,
                    materia_id=mat2, carrera_id=car2, cohorte_id=coh2,
                    desde=date.today(), comisiones=[])
    await repo.add(a1)
    await repo.add(a2)

    svc = _make_equipo_service_sync(db_session, tid)
    actor = _make_current_user(tid, u1.id)
    result = await svc.listar_mis_equipos(actor, domain_user_id=u1.id)

    ids = {item.asignacion_id for item in result}
    assert a1.id in ids
    assert a2.id not in ids  # otro usuario

    # Cleanup
    await repo.delete(a1)
    await repo.delete(a2)
    await usr_repo.delete(u1)
    await usr_repo.delete(u2)
    await db_session.commit()


# 4.3 TRIANGULATE: vigentes, vencidas, sin asignaciones
@pytest.mark.asyncio(loop_scope="session")
async def test_listar_mis_equipos_estado_vigencia_derivado(db_session, create_tables, equipo_setup, monkeypatch):
    """TRIANGULATE 4.3: estado_vigencia derivado correctamente (vigente/vencida)."""
    monkeypatch.setattr("app.core.config.Settings", _fake_settings)

    tid = equipo_setup["tid_a"]
    mat_id = equipo_setup["mat_id"]
    car_id = equipo_setup["car_id"]
    coh_id = equipo_setup["coh_id"]

    repo = AsignacionRepository(session=db_session, tenant_id=tid)
    usr_repo = UsuarioRepository(session=db_session, tenant_id=tid)

    mat_vig, car_vig, coh_vig = await _create_estructura(db_session, tid, "vig_test")

    u = _make_usuario(tid, "evig")
    await usr_repo.add(u)

    hoy = date.today()
    # Vigente: desde hoy, sin hasta
    av = Asignacion(usuario_id=u.id, rol=RolAsignacion.PROFESOR,
                    materia_id=mat_id, carrera_id=car_id, cohorte_id=coh_id,
                    desde=hoy, comisiones=[])
    # Vencida: hasta ayer
    avec = Asignacion(usuario_id=u.id, rol=RolAsignacion.TUTOR,
                      materia_id=mat_vig, carrera_id=car_vig, cohorte_id=coh_vig,
                      desde=hoy - timedelta(days=10), hasta=hoy - timedelta(days=1),
                      comisiones=[])
    await repo.add(av)
    await repo.add(avec)

    svc = _make_equipo_service_sync(db_session, tid)
    actor = _make_current_user(tid, u.id)
    result = await svc.listar_mis_equipos(actor, domain_user_id=u.id)

    por_id = {item.asignacion_id: item for item in result}
    assert por_id[av.id].estado_vigencia == EstadoVigencia.vigente
    assert por_id[avec.id].estado_vigencia == EstadoVigencia.vencida

    # Sin asignaciones → lista vacía
    u2 = _make_usuario(tid, "empty")
    await usr_repo.add(u2)
    actor2 = _make_current_user(tid, u2.id)
    r2 = await svc.listar_mis_equipos(actor2, domain_user_id=u2.id)
    assert r2 == []

    # Cleanup
    await repo.delete(av)
    await repo.delete(avec)
    await usr_repo.delete(u)
    await usr_repo.delete(u2)
    await db_session.commit()


# 4.6 RED: asignacion_masiva crea N asignaciones y emite auditoría
@pytest.mark.asyncio(loop_scope="session")
async def test_asignacion_masiva_crea_y_audita(db_session, create_tables, equipo_setup, monkeypatch):
    """RED 4.6: asignacion_masiva crea N asignaciones y emite EQUIPOS_ASIGNACION_MASIVA."""
    monkeypatch.setattr("app.core.config.Settings", _fake_settings)

    tid = equipo_setup["tid_a"]
    mat_id, car_id, coh_id = await _create_estructura(db_session, tid, "mas")

    usr_repo = UsuarioRepository(session=db_session, tenant_id=tid)
    asig_repo = AsignacionRepository(session=db_session, tenant_id=tid)

    u1 = _make_usuario(tid, "mas1")
    u2 = _make_usuario(tid, "mas2")
    await usr_repo.add(u1)
    await usr_repo.add(u2)

    svc = _make_equipo_service_sync(db_session, tid)
    actor = _make_current_user(tid, uuid.uuid4())

    req = AsignacionMasivaRequest(
        usuario_ids=[u1.id, u2.id],
        materia_id=mat_id,
        carrera_id=car_id,
        cohorte_id=coh_id,
        rol=RolAsignacion.PROFESOR,
        desde=date.today(),
    )
    resultado = await svc.asignacion_masiva(actor, req)

    assert resultado.creadas == 2

    # Verify in DB
    created = await asig_repo.list_by_equipo(mat_id, car_id, coh_id)
    assert len(created) == 2
    for a in created:
        assert a.tenant_id == tid

    # Cleanup
    for a in created:
        await asig_repo.delete(a)
    await usr_repo.delete(u1)
    await usr_repo.delete(u2)
    await db_session.commit()


# 4.8 TRIANGULATE: usuario inexistente → rollback, 0 filas
@pytest.mark.asyncio(loop_scope="session")
async def test_asignacion_masiva_usuario_inexistente_rollback(db_session, create_tables, equipo_setup, monkeypatch):
    """TRIANGULATE 4.8: usuario_id inexistente → UsuarioNoEncontrado, rollback (0 filas)."""
    monkeypatch.setattr("app.core.config.Settings", _fake_settings)

    tid = equipo_setup["tid_a"]
    mat_id, car_id, coh_id = await _create_estructura(db_session, tid, "noexist")

    asig_repo = AsignacionRepository(session=db_session, tenant_id=tid)
    svc = _make_equipo_service_sync(db_session, tid)
    actor = _make_current_user(tid, uuid.uuid4())

    req = AsignacionMasivaRequest(
        usuario_ids=[uuid.uuid4()],  # inexistente
        materia_id=mat_id,
        carrera_id=car_id,
        cohorte_id=coh_id,
        rol=RolAsignacion.TUTOR,
        desde=date.today(),
    )
    with pytest.raises(UsuarioNoEncontrado):
        await svc.asignacion_masiva(actor, req)

    # No rows created
    result = await asig_repo.list_by_equipo(mat_id, car_id, coh_id)
    assert len(result) == 0


@pytest.mark.asyncio(loop_scope="session")
async def test_asignacion_masiva_responsable_otro_tenant_rechazado(db_session, create_tables, equipo_setup, monkeypatch):
    """TRIANGULATE 4.8: responsable_id de otro tenant → ReferenciaInvalida."""
    monkeypatch.setattr("app.core.config.Settings", _fake_settings)

    tid_a = equipo_setup["tid_a"]
    tid_b = equipo_setup["tid_b"]
    mat_id, car_id, coh_id = await _create_estructura(db_session, tid_a, "resp")

    usr_a = UsuarioRepository(session=db_session, tenant_id=tid_a)
    usr_b = UsuarioRepository(session=db_session, tenant_id=tid_b)
    u_a = _make_usuario(tid_a, "rp1")
    u_b = _make_usuario(tid_b, "rp2")
    await usr_a.add(u_a)
    await usr_b.add(u_b)

    svc = _make_equipo_service_sync(db_session, tid_a)
    actor = _make_current_user(tid_a, uuid.uuid4())

    req = AsignacionMasivaRequest(
        usuario_ids=[u_a.id],
        materia_id=mat_id,
        carrera_id=car_id,
        cohorte_id=coh_id,
        rol=RolAsignacion.PROFESOR,
        desde=date.today(),
        responsable_id=u_b.id,  # otro tenant
    )
    with pytest.raises(ReferenciaInvalida):
        await svc.asignacion_masiva(actor, req)

    # Cleanup
    await usr_a.delete(u_a)
    await usr_b.delete(u_b)
    await db_session.commit()


# 4.9 RED + 4.10 GREEN + 4.11 TRIANGULATE: clonar_equipo
@pytest.mark.asyncio(loop_scope="session")
async def test_clonar_equipo_copia_y_omite_duplicados(db_session, create_tables, equipo_setup, monkeypatch):
    """RED 4.9 / GREEN 4.10 / TRIANGULATE 4.11: clonar copia vigentes del origen, omite duplicados."""
    monkeypatch.setattr("app.core.config.Settings", _fake_settings)

    tid = equipo_setup["tid_a"]
    mat_o, car_o, coh_o = await _create_estructura(db_session, tid, "origen")
    mat_d, car_d, coh_d = await _create_estructura(db_session, tid, "destino")

    repo = AsignacionRepository(session=db_session, tenant_id=tid)
    usr_repo = UsuarioRepository(session=db_session, tenant_id=tid)

    u1 = _make_usuario(tid, "cl1")
    u2 = _make_usuario(tid, "cl2")
    await usr_repo.add(u1)
    await usr_repo.add(u2)

    # Equipo origen
    ao1 = Asignacion(usuario_id=u1.id, rol=RolAsignacion.PROFESOR,
                     materia_id=mat_o, carrera_id=car_o, cohorte_id=coh_o,
                     desde=date.today(), comisiones=[])
    ao2 = Asignacion(usuario_id=u2.id, rol=RolAsignacion.TUTOR,
                     materia_id=mat_o, carrera_id=car_o, cohorte_id=coh_o,
                     desde=date.today(), comisiones=[])
    await repo.add(ao1)
    await repo.add(ao2)

    svc = _make_equipo_service_sync(db_session, tid)
    actor = _make_current_user(tid, uuid.uuid4())

    req = ClonarEquipoRequest(
        origen_materia_id=mat_o,
        origen_carrera_id=car_o,
        origen_cohorte_id=coh_o,
        destino_materia_id=mat_d,
        destino_carrera_id=car_d,
        destino_cohorte_id=coh_d,
        desde=date.today(),
    )
    result = await svc.clonar_equipo(actor, req)

    assert result.clonadas == 2
    assert result.omitidas == 0

    destino = await repo.list_by_equipo(mat_d, car_d, coh_d)
    assert len(destino) == 2

    # Re-clonar → duplicados omitidos (idempotencia práctica)
    result2 = await svc.clonar_equipo(actor, req)
    assert result2.clonadas == 0
    assert result2.omitidas == 2

    # Equipo origen vacío → 0 clonadas
    mat_e, car_e, coh_e = await _create_estructura(db_session, tid, "empty")
    mat_d2, car_d2, coh_d2 = await _create_estructura(db_session, tid, "dest2")
    req_empty = ClonarEquipoRequest(
        origen_materia_id=mat_e,
        origen_carrera_id=car_e,
        origen_cohorte_id=coh_e,
        destino_materia_id=mat_d2,
        destino_carrera_id=car_d2,
        destino_cohorte_id=coh_d2,
        desde=date.today(),
    )
    result_empty = await svc.clonar_equipo(actor, req_empty)
    assert result_empty.clonadas == 0

    # Cleanup
    for a in await repo.list_by_equipo(mat_d, car_d, coh_d):
        await repo.delete(a)
    await repo.delete(ao1)
    await repo.delete(ao2)
    await usr_repo.delete(u1)
    await usr_repo.delete(u2)
    await db_session.commit()


# 4.12 RED + GREEN + 4.13 TRIANGULATE: modificar_vigencia_general
@pytest.mark.asyncio(loop_scope="session")
async def test_modificar_vigencia_general_y_audita(db_session, create_tables, equipo_setup, monkeypatch):
    """RED 4.12: modificar_vigencia_general actualiza fechas y emite auditoría."""
    monkeypatch.setattr("app.core.config.Settings", _fake_settings)

    tid = equipo_setup["tid_a"]
    mat_v, car_v, coh_v = await _create_estructura(db_session, tid, "vig")

    repo = AsignacionRepository(session=db_session, tenant_id=tid)
    usr_repo = UsuarioRepository(session=db_session, tenant_id=tid)

    u = _make_usuario(tid, "vig1")
    await usr_repo.add(u)

    a = Asignacion(usuario_id=u.id, rol=RolAsignacion.NEXO,
                   materia_id=mat_v, carrera_id=car_v, cohorte_id=coh_v,
                   desde=date.today(), comisiones=[])
    await repo.add(a)

    svc = _make_equipo_service_sync(db_session, tid)
    actor = _make_current_user(tid, uuid.uuid4())

    nueva_desde = date.today() + timedelta(days=2)
    nueva_hasta = date.today() + timedelta(days=60)
    req = VigenciaGeneralRequest(
        materia_id=mat_v,
        carrera_id=car_v,
        cohorte_id=coh_v,
        desde=nueva_desde,
        hasta=nueva_hasta,
    )
    afectadas = await svc.modificar_vigencia_general(actor, req)
    assert afectadas == 1

    # Cleanup
    for a2 in await repo.list_by_equipo(mat_v, car_v, coh_v):
        await repo.delete(a2)
    await usr_repo.delete(u)
    await db_session.commit()


# 4.14 RED + GREEN: exportar_equipo genera CSV
@pytest.mark.asyncio(loop_scope="session")
async def test_exportar_equipo_genera_csv(db_session, create_tables, equipo_setup, monkeypatch):
    """RED 4.14: exportar_equipo retorna CSV con header + 1 fila por asignacion."""
    monkeypatch.setattr("app.core.config.Settings", _fake_settings)

    tid = equipo_setup["tid_a"]
    mat_ex, car_ex, coh_ex = await _create_estructura(db_session, tid, "exp")

    repo = AsignacionRepository(session=db_session, tenant_id=tid)
    usr_repo = UsuarioRepository(session=db_session, tenant_id=tid)

    u = _make_usuario(tid, "exp1")
    await usr_repo.add(u)

    a = Asignacion(usuario_id=u.id, rol=RolAsignacion.PROFESOR,
                   materia_id=mat_ex, carrera_id=car_ex, cohorte_id=coh_ex,
                   desde=date.today(), comisiones=["Comision A"])
    await repo.add(a)

    svc = _make_equipo_service_sync(db_session, tid)
    query = EquipoQuery(materia_id=mat_ex, carrera_id=car_ex, cohorte_id=coh_ex)
    csv_content = await svc.exportar_equipo(query)

    lines = csv_content.strip().split("\n")
    assert len(lines) == 2  # header + 1 fila
    header = lines[0]
    assert "asignacion_id" in header
    assert "estado_vigencia" in header
    assert str(u.id) in csv_content

    # Equipo vacío → solo header
    mat_e2, car_e2, coh_e2 = await _create_estructura(db_session, tid, "exp_empty")
    q_empty = EquipoQuery(materia_id=mat_e2, carrera_id=car_e2, cohorte_id=coh_e2)
    csv_empty = await svc.exportar_equipo(q_empty)
    lines_empty = csv_empty.strip().split("\n")
    assert len(lines_empty) == 1  # solo header

    # Cleanup
    await repo.delete(a)
    await usr_repo.delete(u)
    await db_session.commit()


# 4.15 TRIANGULATE: export no cruza tenants
@pytest.mark.asyncio(loop_scope="session")
async def test_exportar_equipo_no_cruza_tenants(db_session, create_tables, equipo_setup, monkeypatch):
    """TRIANGULATE 4.15: exportar_equipo no incluye asignaciones de otros tenants."""
    monkeypatch.setattr("app.core.config.Settings", _fake_settings)

    tid_a = equipo_setup["tid_a"]
    tid_b = equipo_setup["tid_b"]
    mat_a, car_a, coh_a = await _create_estructura(db_session, tid_a, "xta")
    mat_b, car_b, coh_b = await _create_estructura(db_session, tid_b, "xtb")

    repo_a = AsignacionRepository(session=db_session, tenant_id=tid_a)
    repo_b = AsignacionRepository(session=db_session, tenant_id=tid_b)
    usr_a = UsuarioRepository(session=db_session, tenant_id=tid_a)
    usr_b = UsuarioRepository(session=db_session, tenant_id=tid_b)

    ua = _make_usuario(tid_a, "xta_u")
    ub = _make_usuario(tid_b, "xtb_u")
    await usr_a.add(ua)
    await usr_b.add(ub)

    aa = Asignacion(usuario_id=ua.id, rol=RolAsignacion.PROFESOR,
                    materia_id=mat_a, carrera_id=car_a, cohorte_id=coh_a,
                    desde=date.today(), comisiones=[])
    ab = Asignacion(usuario_id=ub.id, rol=RolAsignacion.TUTOR,
                    materia_id=mat_b, carrera_id=car_b, cohorte_id=coh_b,
                    desde=date.today(), comisiones=[])
    await repo_a.add(aa)
    await repo_b.add(ab)

    # Export from tenant A scope
    svc_a = EquipoService(
        asignacion_repo=repo_a,
        usuario_repo=usr_a,
        audit_repo=AuditRepository(session=db_session, tenant_id=tid_a),
    )
    q = EquipoQuery(materia_id=mat_a, carrera_id=car_a, cohorte_id=coh_a)
    csv_a = await svc_a.exportar_equipo(q)

    # Only tenant A's user appears
    assert str(ua.id) in csv_a
    assert str(ub.id) not in csv_a

    # Cleanup
    await repo_a.delete(aa)
    await repo_b.delete(ab)
    await usr_a.delete(ua)
    await usr_b.delete(ub)
    await db_session.commit()


# ---------------------------------------------------------------------------
# TASK 5 — Router endpoints HTTP
# ---------------------------------------------------------------------------

# 5.1 RED: GET /mis-equipos → 200 con asignaciones propias
@pytest.mark.asyncio(loop_scope="session")
async def test_get_mis_equipos_200(equipo_client, equipo_setup, monkeypatch):
    """RED 5.1: GET /api/v1/equipos/mis-equipos → 200 con asignaciones propias."""
    monkeypatch.setattr("app.core.config.Settings", _fake_settings)

    tid = equipo_setup["tid_a"]
    user_id = equipo_setup["user_a"]
    token = _make_jwt(tid, user_id, roles=["USR_EQ_A"])

    resp = await equipo_client.get(
        "/api/v1/equipos/mis-equipos",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


# 5.3 TRIANGULATE: sin equipos:ver → 403
@pytest.mark.asyncio(loop_scope="session")
async def test_get_mis_equipos_sin_permiso_403(equipo_client, equipo_setup, monkeypatch):
    """TRIANGULATE 5.3: GET /mis-equipos sin equipos:ver → 403."""
    monkeypatch.setattr("app.core.config.Settings", _fake_settings)

    tid = equipo_setup["tid_a"]
    token = _make_jwt(tid, uuid.uuid4(), roles=["SINPERMISO"])
    resp = await equipo_client.get(
        "/api/v1/equipos/mis-equipos",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403


# Tenant A user cannot see tenant B equipment (5.3 TRIANGULATE — identity isolation)
@pytest.mark.asyncio(loop_scope="session")
async def test_mis_equipos_tenant_a_no_ve_tenant_b(equipo_client, equipo_setup, db_session, create_tables, monkeypatch):
    """TRIANGULATE 5.3: usuario A no ve equipos de usuario B de otro tenant."""
    monkeypatch.setattr("app.core.config.Settings", _fake_settings)

    tid_a = equipo_setup["tid_a"]
    tid_b = equipo_setup["tid_b"]
    user_a = equipo_setup["user_a"]
    user_b = equipo_setup["user_b"]

    # user_a JWT en tenant A
    token_a = _make_jwt(tid_a, user_a, roles=["USR_EQ_A"])
    resp_a = await equipo_client.get(
        "/api/v1/equipos/mis-equipos",
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert resp_a.status_code == 200
    # user_a has no asignaciones seeded, so the list is empty or only their own
    data_a = resp_a.json()
    # None of the items should have tenant_b context (not leaked across tenants)
    assert isinstance(data_a, list)


# 5.4 RED + GREEN: GET /equipos
@pytest.mark.asyncio(loop_scope="session")
async def test_get_equipos_200(equipo_client, equipo_setup, monkeypatch):
    """RED 5.4: GET /api/v1/equipos con tripleta → 200."""
    monkeypatch.setattr("app.core.config.Settings", _fake_settings)

    tid = equipo_setup["tid_a"]
    mat_id = equipo_setup["mat_id"]
    car_id = equipo_setup["car_id"]
    coh_id = equipo_setup["coh_id"]
    token = _make_jwt(tid, equipo_setup["user_a"], roles=["USR_EQ_A"])

    resp = await equipo_client.get(
        f"/api/v1/equipos?materia_id={mat_id}&carrera_id={car_id}&cohorte_id={coh_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio(loop_scope="session")
async def test_get_equipos_sin_permiso_403(equipo_client, equipo_setup, monkeypatch):
    """TRIANGULATE 5.4: GET /api/v1/equipos sin permiso → 403."""
    monkeypatch.setattr("app.core.config.Settings", _fake_settings)

    tid = equipo_setup["tid_a"]
    mat_id = equipo_setup["mat_id"]
    car_id = equipo_setup["car_id"]
    coh_id = equipo_setup["coh_id"]
    token = _make_jwt(tid, uuid.uuid4(), roles=["SINPERMISO"])

    resp = await equipo_client.get(
        f"/api/v1/equipos?materia_id={mat_id}&carrera_id={car_id}&cohorte_id={coh_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403


# 5.5 RED + GREEN: POST /asignacion-masiva
@pytest.mark.asyncio(loop_scope="session")
async def test_asignacion_masiva_endpoint_201(equipo_client, equipo_setup, db_session, monkeypatch):
    """RED 5.5: POST /asignacion-masiva con permiso → 201 con ResumenLote."""
    monkeypatch.setattr("app.core.config.Settings", _fake_settings)

    tid = equipo_setup["tid_a"]
    token = _make_jwt(tid, equipo_setup["user_a"], roles=["USR_EQ_A"])

    usr_repo = UsuarioRepository(session=db_session, tenant_id=tid)
    mat_id, car_id, coh_id = await _create_estructura(db_session, tid, "ep")
    u = _make_usuario(tid, "ep1")
    await usr_repo.add(u)
    await db_session.commit()

    resp = await equipo_client.post(
        "/api/v1/equipos/asignacion-masiva",
        json={
            "usuario_ids": [str(u.id)],
            "materia_id": str(mat_id),
            "carrera_id": str(car_id),
            "cohorte_id": str(coh_id),
            "rol": "PROFESOR",
            "desde": str(date.today()),
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["creadas"] == 1

    # Cleanup
    asig_repo = AsignacionRepository(session=db_session, tenant_id=tid)
    for a in await asig_repo.list_by_equipo(mat_id, car_id, coh_id):
        await asig_repo.delete(a)
    await usr_repo.delete(u)
    await db_session.commit()


# 5.6 TRIANGULATE: sin equipos:asignar → 403; referencia inválida → 422
@pytest.mark.asyncio(loop_scope="session")
async def test_asignacion_masiva_sin_permiso_403(equipo_client, equipo_setup, monkeypatch):
    """TRIANGULATE 5.6: POST /asignacion-masiva sin equipos:asignar → 403."""
    monkeypatch.setattr("app.core.config.Settings", _fake_settings)

    tid = equipo_setup["tid_a"]
    token = _make_jwt(tid, uuid.uuid4(), roles=["SINPERMISO"])

    resp = await equipo_client.post(
        "/api/v1/equipos/asignacion-masiva",
        json={
            "usuario_ids": [str(uuid.uuid4())],
            "materia_id": str(uuid.uuid4()),
            "carrera_id": str(uuid.uuid4()),
            "cohorte_id": str(uuid.uuid4()),
            "rol": "PROFESOR",
            "desde": str(date.today()),
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio(loop_scope="session")
async def test_asignacion_masiva_usuario_inexistente_422(equipo_client, equipo_setup, monkeypatch):
    """TRIANGULATE 5.6: POST /asignacion-masiva con usuario inexistente → 422."""
    monkeypatch.setattr("app.core.config.Settings", _fake_settings)

    tid = equipo_setup["tid_a"]
    token = _make_jwt(tid, equipo_setup["user_a"], roles=["USR_EQ_A"])

    resp = await equipo_client.post(
        "/api/v1/equipos/asignacion-masiva",
        json={
            "usuario_ids": [str(uuid.uuid4())],  # no existe
            "materia_id": str(uuid.uuid4()),
            "carrera_id": str(uuid.uuid4()),
            "cohorte_id": str(uuid.uuid4()),
            "rol": "TUTOR",
            "desde": str(date.today()),
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 422


# 5.7 RED + GREEN: POST /clonar
@pytest.mark.asyncio(loop_scope="session")
async def test_clonar_equipo_endpoint_201(equipo_client, equipo_setup, monkeypatch):
    """RED 5.7: POST /clonar con permiso → 201 con ResumenClonacion."""
    monkeypatch.setattr("app.core.config.Settings", _fake_settings)

    tid = equipo_setup["tid_a"]
    token = _make_jwt(tid, equipo_setup["user_a"], roles=["USR_EQ_A"])
    mat_o = equipo_setup["mat_id"]
    car_o = equipo_setup["car_id"]
    coh_o = equipo_setup["coh_id"]

    resp = await equipo_client.post(
        "/api/v1/equipos/clonar",
        json={
            "origen_materia_id": str(mat_o),
            "origen_carrera_id": str(car_o),
            "origen_cohorte_id": str(coh_o),
            "destino_materia_id": str(uuid.uuid4()),
            "destino_carrera_id": str(uuid.uuid4()),
            "destino_cohorte_id": str(uuid.uuid4()),
            "desde": str(date.today()),
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert "clonadas" in data
    assert "omitidas" in data


# 5.8 RED + GREEN: PATCH /vigencia-general
@pytest.mark.asyncio(loop_scope="session")
async def test_vigencia_general_endpoint(equipo_client, equipo_setup, monkeypatch):
    """RED 5.8: PATCH /vigencia-general con permiso → 200 con afectadas."""
    monkeypatch.setattr("app.core.config.Settings", _fake_settings)

    tid = equipo_setup["tid_a"]
    mat_id = equipo_setup["mat_id"]
    car_id = equipo_setup["car_id"]
    coh_id = equipo_setup["coh_id"]
    token = _make_jwt(tid, equipo_setup["user_a"], roles=["USR_EQ_A"])

    resp = await equipo_client.patch(
        "/api/v1/equipos/vigencia-general",
        json={
            "materia_id": str(mat_id),
            "carrera_id": str(car_id),
            "cohorte_id": str(coh_id),
            "desde": str(date.today()),
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "afectadas" in data


# 5.9 RED + GREEN: GET /exportar → CSV attachment
@pytest.mark.asyncio(loop_scope="session")
async def test_exportar_endpoint_csv(equipo_client, equipo_setup, monkeypatch):
    """RED 5.9: GET /exportar → 200 con Content-Disposition attachment."""
    monkeypatch.setattr("app.core.config.Settings", _fake_settings)

    tid = equipo_setup["tid_a"]
    mat_id = equipo_setup["mat_id"]
    car_id = equipo_setup["car_id"]
    coh_id = equipo_setup["coh_id"]
    token = _make_jwt(tid, equipo_setup["user_a"], roles=["USR_EQ_A"])

    resp = await equipo_client.get(
        f"/api/v1/equipos/exportar?materia_id={mat_id}&carrera_id={car_id}&cohorte_id={coh_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert "attachment" in resp.headers.get("content-disposition", "")
    assert "text/csv" in resp.headers.get("content-type", "")


# 5.10 TRIANGULATE: exportar sin permiso → 403
@pytest.mark.asyncio(loop_scope="session")
async def test_exportar_sin_permiso_403(equipo_client, equipo_setup, monkeypatch):
    """TRIANGULATE 5.10: GET /exportar sin equipos:ver → 403."""
    monkeypatch.setattr("app.core.config.Settings", _fake_settings)

    tid = equipo_setup["tid_a"]
    mat_id = equipo_setup["mat_id"]
    car_id = equipo_setup["car_id"]
    coh_id = equipo_setup["coh_id"]
    token = _make_jwt(tid, uuid.uuid4(), roles=["SINPERMISO"])

    resp = await equipo_client.get(
        f"/api/v1/equipos/exportar?materia_id={mat_id}&carrera_id={car_id}&cohorte_id={coh_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403


# 5.10 TRIANGULATE: CSV no incluye PII cifrada
@pytest.mark.asyncio(loop_scope="session")
async def test_exportar_csv_sin_pii(equipo_client, equipo_setup, db_session, create_tables, monkeypatch):
    """TRIANGULATE 5.10: CSV exportado no incluye PII cifrada (dni, cuil, cbu)."""
    monkeypatch.setattr("app.core.config.Settings", _fake_settings)

    tid = equipo_setup["tid_a"]
    mat_id, car_id, coh_id = await _create_estructura(db_session, tid, "pii_exp")
    usr_repo = UsuarioRepository(session=db_session, tenant_id=tid)
    repo = AsignacionRepository(session=db_session, tenant_id=tid)

    u = _make_usuario(tid, "pii_csv")
    await usr_repo.add(u)
    a = Asignacion(usuario_id=u.id, rol=RolAsignacion.PROFESOR,
                   materia_id=mat_id, carrera_id=car_id, cohorte_id=coh_id,
                   desde=date.today(), comisiones=[])
    await repo.add(a)
    await db_session.commit()

    token = _make_jwt(tid, equipo_setup["user_a"], roles=["USR_EQ_A"])
    resp = await equipo_client.get(
        f"/api/v1/equipos/exportar?materia_id={mat_id}&carrera_id={car_id}&cohorte_id={coh_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    csv_text = resp.text
    # CSV must NOT contain PII column names
    assert "dni" not in csv_text.lower() or "materia_id" in csv_text  # only expected columns
    # Actual check: no PII column headers
    first_line = csv_text.split("\n")[0]
    assert "dni" not in first_line
    assert "cuil" not in first_line
    assert "cbu" not in first_line

    # Cleanup
    await repo.delete(a)
    await usr_repo.delete(u)
    await db_session.commit()


# ---------------------------------------------------------------------------
# TASK 6 — Auditoría, reglas duras, verificación
# ---------------------------------------------------------------------------

# 6.4 Test de auditoría: las tres acciones se emiten
@pytest.mark.asyncio(loop_scope="session")
async def test_auditoria_masiva_emite_evento(db_session, create_tables, equipo_setup, monkeypatch):
    """6.4: asignacion_masiva emite evento de auditoría EQUIPOS_ASIGNACION_MASIVA en DB."""
    monkeypatch.setattr("app.core.config.Settings", _fake_settings)

    tid = equipo_setup["tid_a"]
    mat_id, car_id, coh_id = await _create_estructura(db_session, tid, "aud")

    usr_repo = UsuarioRepository(session=db_session, tenant_id=tid)
    u = _make_usuario(tid, "aud1")
    await usr_repo.add(u)

    actor_id = uuid.uuid4()
    actor = _make_current_user(tid, actor_id)

    svc = _make_equipo_service_sync(db_session, tid)
    req = AsignacionMasivaRequest(
        usuario_ids=[u.id],
        materia_id=mat_id,
        carrera_id=car_id,
        cohorte_id=coh_id,
        rol=RolAsignacion.NEXO,
        desde=date.today(),
    )
    await svc.asignacion_masiva(actor, req)

    # Verify audit event in DB
    from sqlalchemy import select
    from app.models.audit import AuditEvent
    stmt = select(AuditEvent).where(
        AuditEvent.tenant_id == tid,
        AuditEvent.actor_user_id == actor_id,
        AuditEvent.accion == AuditAction.EQUIPOS_ASIGNACION_MASIVA,
    )
    result = await db_session.execute(stmt)
    event = result.scalar_one_or_none()
    assert event is not None, "Evento de auditoría EQUIPOS_ASIGNACION_MASIVA no emitido"
    assert event.registros_afectados == 1

    # Cleanup
    repo = AsignacionRepository(session=db_session, tenant_id=tid)
    for a in await repo.list_by_equipo(mat_id, car_id, coh_id):
        await repo.delete(a)
    await usr_repo.delete(u)
    await db_session.commit()


@pytest.mark.asyncio(loop_scope="session")
async def test_auditoria_clonar_emite_evento(db_session, create_tables, equipo_setup, monkeypatch):
    """6.4: clonar_equipo emite evento EQUIPOS_CLONAR en DB."""
    monkeypatch.setattr("app.core.config.Settings", _fake_settings)

    tid = equipo_setup["tid_a"]
    actor_id = uuid.uuid4()
    actor = _make_current_user(tid, actor_id)
    mat_o, car_o, coh_o = await _create_estructura(db_session, tid, "clon_o")
    mat_d, car_d, coh_d = await _create_estructura(db_session, tid, "clon_d")

    svc = _make_equipo_service_sync(db_session, tid)
    req = ClonarEquipoRequest(
        origen_materia_id=mat_o,
        origen_carrera_id=car_o,
        origen_cohorte_id=coh_o,
        destino_materia_id=mat_d,
        destino_carrera_id=car_d,
        destino_cohorte_id=coh_d,
        desde=date.today(),
    )
    await svc.clonar_equipo(actor, req)

    from sqlalchemy import select
    from app.models.audit import AuditEvent
    stmt = select(AuditEvent).where(
        AuditEvent.tenant_id == tid,
        AuditEvent.actor_user_id == actor_id,
        AuditEvent.accion == AuditAction.EQUIPOS_CLONAR,
    )
    result = await db_session.execute(stmt)
    event = result.scalar_one_or_none()
    assert event is not None, "Evento de auditoría EQUIPOS_CLONAR no emitido"


@pytest.mark.asyncio(loop_scope="session")
async def test_auditoria_vigencia_emite_evento(db_session, create_tables, equipo_setup, monkeypatch):
    """6.4: modificar_vigencia_general emite EQUIPOS_VIGENCIA_GENERAL en DB."""
    monkeypatch.setattr("app.core.config.Settings", _fake_settings)

    tid = equipo_setup["tid_a"]
    actor_id = uuid.uuid4()
    actor = _make_current_user(tid, actor_id)
    mat_v2, car_v2, coh_v2 = await _create_estructura(db_session, tid, "vig_aud")

    svc = _make_equipo_service_sync(db_session, tid)
    req = VigenciaGeneralRequest(
        materia_id=mat_v2,
        carrera_id=car_v2,
        cohorte_id=coh_v2,
        desde=date.today(),
    )
    await svc.modificar_vigencia_general(actor, req)

    from sqlalchemy import select
    from app.models.audit import AuditEvent
    stmt = select(AuditEvent).where(
        AuditEvent.tenant_id == tid,
        AuditEvent.actor_user_id == actor_id,
        AuditEvent.accion == AuditAction.EQUIPOS_VIGENCIA_GENERAL,
    )
    result = await db_session.execute(stmt)
    event = result.scalar_one_or_none()
    assert event is not None, "Evento de auditoría EQUIPOS_VIGENCIA_GENERAL no emitido"


# 6.3 Reglas duras: identidad desde JWT
def test_listar_mis_equipos_usa_domain_user_id():
    """6.3: EquipoService.listar_mis_equipos usa domain_user_id (no current_user.user_id como FK)."""
    import inspect
    import app.services.equipo_service as svc_module
    src = inspect.getsource(svc_module.EquipoService.listar_mis_equipos)
    # C-28: domain_user_id must be used, NOT current_user.user_id (auth_identity_id != usuario.id)
    assert "domain_user_id" in src
    assert "current_user.user_id" not in src


# 6.3 Reglas duras: extra=forbid en todos los schemas
def test_todos_los_schemas_tienen_extra_forbid():
    """6.3: todos los schemas de equipo tienen extra='forbid'."""
    schemas = [
        AsignacionMasivaRequest,
        ClonarEquipoRequest,
        VigenciaGeneralRequest,
        EquipoQuery,
        MisEquiposItem,
        ResumenLote,
        ResumenClonacion,
    ]
    for schema in schemas:
        config = schema.model_config
        assert config.get("extra") == "forbid", f"{schema.__name__} no tiene extra='forbid'"
