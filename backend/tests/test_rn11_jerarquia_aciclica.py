"""
test_rn11_jerarquia_aciclica.py — TDD suite para RN-11: jerarquía acíclica de responsables.

RN-11 (interpretación implementada):
    Una asignación puede declarar un responsable (responsable_id → usuario.id).
    La asignación NO puede:
        a) declarar al mismo usuario como su propio responsable (auto-referencia).
        b) crear un ciclo en la cadena de responsables (A→B→...→A).

    Se valida en AsignacionService.crear_asignacion y editar_asignacion.
    La cadena se recorre solo sobre asignaciones activas (deleted_at IS NULL),
    con scope de tenant.

Ciclo TDD: RED → GREEN → TRIANGULATE → REFACTOR.
DB real (activia_trace_test). Sin mocks.

NOTA: estos tests son de capa de servicio (no HTTP). No usan monkeypatch de
ENCRYPTION_KEY para evitar el conflicto con datos cifrados en la fixture de módulo.
La fixture utiliza la clave real del entorno (.env); los tests solo trabajan con
UUIDs — nunca desencriptan texto.
"""
import uuid
from datetime import date

import pytest
import pytest_asyncio

from app.core.database import build_session_factory
from app.models.tenant import Tenant, TenantEstado
from app.models.usuario import RolAsignacion, UsuarioEstado
from app.repositories.usuario_repository import AsignacionRepository, UsuarioRepository
from app.services.usuario_service import (
    AsignacionService,
    ReferenciaInvalida,
)
from tests.conftest import create_usuario_con_identidad


# ---------------------------------------------------------------------------
# Fixtures de módulo
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture(scope="module")
async def rn11_setup(test_engine, create_tables):
    """
    Crea un tenant aislado con tres usuarios (A, B, C) para los tests de RN-11.
    Usa create_usuario_con_identidad (invariante C-28: auth_identity_id ≠ usuario.id).
    No crea asignaciones — cada test construye las suyas y limpia al final.
    """
    factory = build_session_factory(test_engine)
    session = factory()

    tid = uuid.uuid4()
    session.add(Tenant(id=tid, nombre="RN11 Tenant", estado=TenantEstado.ACTIVO))
    await session.flush()

    # Crear tres usuarios con AuthIdentity real (invariante C-28)
    u_a = await create_usuario_con_identidad(session, tid, nombre="A", apellidos="RN11")
    u_b = await create_usuario_con_identidad(session, tid, nombre="B", apellidos="RN11")
    u_c = await create_usuario_con_identidad(session, tid, nombre="C", apellidos="RN11")

    await session.commit()
    await session.close()

    yield {
        "tid": tid,
        "usuario_a": u_a,
        "usuario_b": u_b,
        "usuario_c": u_c,
    }


# ---------------------------------------------------------------------------
# Helpers de fixtures
# ---------------------------------------------------------------------------

def _make_service(session, tid):
    """Crea AsignacionService scoped a tid usando la sesión dada."""
    asig_repo = AsignacionRepository(session=session, tenant_id=tid)
    usr_repo = UsuarioRepository(session=session, tenant_id=tid)
    return AsignacionService(asignacion_repo=asig_repo, usuario_repo=usr_repo)


def _make_actor(tid):
    from app.core.dependencies import CurrentUser
    return CurrentUser(user_id=uuid.uuid4(), tenant_id=tid, roles=["ADMIN"])


# ===========================================================================
# RED → test que falla antes de implementar (auto-referencia y ciclos)
# ===========================================================================


@pytest.mark.asyncio(loop_scope="session")
async def test_rn11_red_auto_referencia_rechazada(db_session, rn11_setup):
    """
    RED: crear asignación donde usuario_id == responsable_id debe lanzar
    ReferenciaInvalida (auto-referencia, ciclo de longitud 1).
    """
    tid = rn11_setup["tid"]
    u_a = rn11_setup["usuario_a"]
    svc = _make_service(db_session, tid)
    actor = _make_actor(tid)

    with pytest.raises(ReferenciaInvalida, match="(?i)ciclo"):
        await svc.crear_asignacion(
            actor,
            u_a.id,
            RolAsignacion.PROFESOR,
            date.today(),
            responsable_id=u_a.id,  # Auto-referencia: A es responsable de sí mismo
        )


@pytest.mark.asyncio(loop_scope="session")
async def test_rn11_red_ciclo_de_2_rechazado(db_session, rn11_setup):
    """
    RED: ciclo A→B, B→A debe ser rechazado al crear la segunda asignación.

    Setup:
        asig_a: usuario=A, responsable=B  (válida)
        asig_b: usuario=B, responsable=A  (INVÁLIDA — crea ciclo)
    """
    tid = rn11_setup["tid"]
    u_a = rn11_setup["usuario_a"]
    u_b = rn11_setup["usuario_b"]
    svc = _make_service(db_session, tid)
    actor = _make_actor(tid)

    # Primera asignación: A con responsable B (válida)
    asig_a = await svc.crear_asignacion(
        actor, u_a.id, RolAsignacion.PROFESOR, date.today(),
        responsable_id=u_b.id,
    )

    # Segunda asignación: B con responsable A → CICLO
    try:
        with pytest.raises(ReferenciaInvalida, match="(?i)ciclo"):
            await svc.crear_asignacion(
                actor, u_b.id, RolAsignacion.TUTOR, date.today(),
                responsable_id=u_a.id,
            )
    finally:
        # Cleanup: eliminar asig_a
        asig_repo = AsignacionRepository(session=db_session, tenant_id=tid)
        await asig_repo.delete(asig_a)
        await db_session.commit()


@pytest.mark.asyncio(loop_scope="session")
async def test_rn11_red_ciclo_de_3_rechazado(db_session, rn11_setup):
    """
    RED: ciclo A→B→C→A debe ser rechazado al crear la tercera asignación.

    Setup:
        asig_a: usuario=A, responsable=B  (válida)
        asig_b: usuario=B, responsable=C  (válida)
        asig_c: usuario=C, responsable=A  (INVÁLIDA — crea ciclo)
    """
    tid = rn11_setup["tid"]
    u_a = rn11_setup["usuario_a"]
    u_b = rn11_setup["usuario_b"]
    u_c = rn11_setup["usuario_c"]
    svc = _make_service(db_session, tid)
    actor = _make_actor(tid)

    asig_a = await svc.crear_asignacion(
        actor, u_a.id, RolAsignacion.PROFESOR, date.today(),
        responsable_id=u_b.id,
    )
    asig_b = await svc.crear_asignacion(
        actor, u_b.id, RolAsignacion.TUTOR, date.today(),
        responsable_id=u_c.id,
    )

    try:
        with pytest.raises(ReferenciaInvalida, match="(?i)ciclo"):
            await svc.crear_asignacion(
                actor, u_c.id, RolAsignacion.COORDINADOR, date.today(),
                responsable_id=u_a.id,  # C→A cierra el ciclo A→B→C→A
            )
    finally:
        asig_repo = AsignacionRepository(session=db_session, tenant_id=tid)
        await asig_repo.delete(asig_a)
        await asig_repo.delete(asig_b)
        await db_session.commit()


@pytest.mark.asyncio(loop_scope="session")
async def test_rn11_happy_path_cadena_valida(db_session, rn11_setup):
    """
    Triangulación: cadena lineal A→B→C (sin ciclo) debe ser aceptada.
    """
    tid = rn11_setup["tid"]
    u_a = rn11_setup["usuario_a"]
    u_b = rn11_setup["usuario_b"]
    u_c = rn11_setup["usuario_c"]
    svc = _make_service(db_session, tid)
    actor = _make_actor(tid)

    # A supervisa a B, B supervisa a C — cadena lineal, sin ciclo
    asig_a = await svc.crear_asignacion(
        actor, u_a.id, RolAsignacion.COORDINADOR, date.today(),
        responsable_id=u_b.id,
    )
    asig_b = await svc.crear_asignacion(
        actor, u_b.id, RolAsignacion.TUTOR, date.today(),
        responsable_id=u_c.id,
    )
    asig_c = await svc.crear_asignacion(
        actor, u_c.id, RolAsignacion.PROFESOR, date.today(),
        # Sin responsable
    )

    # Las tres asignaciones existen y son válidas
    asig_repo = AsignacionRepository(session=db_session, tenant_id=tid)
    lista = await asig_repo.list(usuario_id=u_a.id)
    ids = {a.id for a in lista}
    assert asig_a.id in ids

    # Cleanup
    await asig_repo.delete(asig_a)
    await asig_repo.delete(asig_b)
    await asig_repo.delete(asig_c)
    await db_session.commit()


@pytest.mark.asyncio(loop_scope="session")
async def test_rn11_sin_responsable_siempre_valido(db_session, rn11_setup):
    """
    Triangulación: crear asignación sin responsable_id nunca falla por RN-11.
    """
    tid = rn11_setup["tid"]
    u_a = rn11_setup["usuario_a"]
    svc = _make_service(db_session, tid)
    actor = _make_actor(tid)

    asig = await svc.crear_asignacion(
        actor, u_a.id, RolAsignacion.FINANZAS, date.today(),
        responsable_id=None,
    )
    assert asig.id is not None

    asig_repo = AsignacionRepository(session=db_session, tenant_id=tid)
    await asig_repo.delete(asig)
    await db_session.commit()


@pytest.mark.asyncio(loop_scope="session")
async def test_rn11_editar_asignacion_auto_referencia_rechazada(db_session, rn11_setup):
    """
    Triangulación: editar_asignacion con responsable_id == usuario_id también
    debe lanzar ReferenciaInvalida (auto-referencia vía edit).
    """
    tid = rn11_setup["tid"]
    u_a = rn11_setup["usuario_a"]
    u_b = rn11_setup["usuario_b"]
    svc = _make_service(db_session, tid)
    actor = _make_actor(tid)

    # Crear asignación de A sin responsable
    asig = await svc.crear_asignacion(
        actor, u_a.id, RolAsignacion.PROFESOR, date.today(),
    )

    try:
        with pytest.raises(ReferenciaInvalida, match="(?i)ciclo"):
            await svc.editar_asignacion(
                asig.id,
                responsable_id=u_a.id,  # A como responsable de sí mismo
                _responsable_provided=True,
            )
    finally:
        asig_repo = AsignacionRepository(session=db_session, tenant_id=tid)
        await asig_repo.delete(asig)
        await db_session.commit()


@pytest.mark.asyncio(loop_scope="session")
async def test_rn11_editar_asignacion_ciclo_rechazado(db_session, rn11_setup):
    """
    Triangulación: editar_asignacion que introduce un ciclo debe ser rechazada.

    Setup:
        asig_b: usuario=B, responsable=A (A supervisa B)
        asig_a: usuario=A, sin responsable
    Luego editar asig_a para poner responsable=B → crea ciclo A→B→A
    """
    tid = rn11_setup["tid"]
    u_a = rn11_setup["usuario_a"]
    u_b = rn11_setup["usuario_b"]
    svc = _make_service(db_session, tid)
    actor = _make_actor(tid)

    # B supervisado por A
    asig_b = await svc.crear_asignacion(
        actor, u_b.id, RolAsignacion.TUTOR, date.today(),
        responsable_id=u_a.id,
    )
    # A sin responsable
    asig_a = await svc.crear_asignacion(
        actor, u_a.id, RolAsignacion.COORDINADOR, date.today(),
    )

    try:
        with pytest.raises(ReferenciaInvalida, match="(?i)ciclo"):
            # Intento de A con responsable B → ciclo: A→B→A
            await svc.editar_asignacion(
                asig_a.id,
                responsable_id=u_b.id,
                _responsable_provided=True,
            )
    finally:
        asig_repo = AsignacionRepository(session=db_session, tenant_id=tid)
        await asig_repo.delete(asig_a)
        await asig_repo.delete(asig_b)
        await db_session.commit()
