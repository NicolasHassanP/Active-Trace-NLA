"""
test_tarea_notificacion.py — TDD D9: notificación vía mensajería al asignar/reasignar tarea.

Ciclo TDD:
    RED        : tests que verifican hilo + mensaje al asignar → falla antes de implementar.
    GREEN      : implementar _notificar_asignado en TareaService.
    TRIANGULATE: (a) crear → notifica; (b) auto-asignación → NO notifica;
                 (c) delegar → notifica al NUEVO asignado.
    REFACTOR   : código limpio, sin duplicación.

DB real: activia_trace_test (postgres nativo localhost:5432).
Sin mocks de DB.
Helper create_usuario_con_identidad del conftest — garantiza auth_identity_id ≠ usuario.id.
"""
import uuid

import pytest

from app.core.dependencies import CurrentUser
from tests.conftest import create_usuario_con_identidad


# ---------------------------------------------------------------------------
# Helpers locales
# ---------------------------------------------------------------------------

def _actor(tenant_id: uuid.UUID, user_id: uuid.UUID, roles=None) -> CurrentUser:
    """CurrentUser con auth_identity_id (JWT sub) = user_id."""
    return CurrentUser(user_id=user_id, tenant_id=tenant_id, roles=roles or ["COORDINADOR"])


def _make_service(session, tenant_id: uuid.UUID):
    from app.repositories.audit_repository import AuditRepository
    from app.repositories.mensajeria_repository import MensajeriaRepository
    from app.repositories.tarea_repository import ComentarioTareaRepository, TareaRepository
    from app.services.tarea_service import TareaService

    return TareaService(
        tarea_repo=TareaRepository(session=session, tenant_id=tenant_id),
        comentario_repo=ComentarioTareaRepository(session=session, tenant_id=tenant_id),
        audit_repo=AuditRepository(session=session, tenant_id=tenant_id),
        mensajeria_repo=MensajeriaRepository(session=session, tenant_id=tenant_id),
    )


async def _setup_tenant(session):
    """Crea un tenant aislado con UUID único. Retorna tid."""
    from app.models.tenant import Tenant, TenantEstado

    tid = uuid.uuid4()
    session.add(Tenant(id=tid, nombre=f"NotifTest_{tid.hex[:4]}", estado=TenantEstado.ACTIVO))
    await session.flush()
    return tid


# ---------------------------------------------------------------------------
# (a) RED → GREEN: publicar crea hilo+mensaje para el asignado_a
# ---------------------------------------------------------------------------

@pytest.mark.asyncio(loop_scope="session")
async def test_publicar_notifica_asignado_a_via_mensajeria(db_session, create_tables):
    """
    (a) RED: al publicar una tarea, el asignado_a debe tener al menos un mensaje
    no leído en la mensajería interna (conteo > 0 para el hilo creado).

    Triangulación: dos usuarios distintos (coord y docente) → coord notifica a docente.
    """
    from app.repositories.mensajeria_repository import MensajeriaRepository
    from app.schemas.tarea import TareaCreate

    tid = await _setup_tenant(db_session)

    coord = await create_usuario_con_identidad(
        db_session, tid,
        email=f"coord_notif_{uuid.uuid4().hex[:6]}@t.com",
        nombre="Coord", apellidos="Notif",
    )
    docente = await create_usuario_con_identidad(
        db_session, tid,
        email=f"docente_notif_{uuid.uuid4().hex[:6]}@t.com",
        nombre="Docente", apellidos="Notif",
    )
    await db_session.commit()

    # El actor usa su auth_identity_id como JWT sub; domain_user_id = coord.id
    actor = _actor(tid, coord.auth_identity_id)
    svc = _make_service(db_session, tid)
    mensajeria_repo = MensajeriaRepository(session=db_session, tenant_id=tid)

    req = TareaCreate(asignado_a=docente.id, descripcion="Revisar actas de examen")
    await svc.publicar(req, actor, domain_user_id=coord.id)

    # Verificar: debe existir un hilo 1:1 entre coord.id y docente.id
    hilo_id = await mensajeria_repo.buscar_hilo_existente(coord.id, docente.id)
    assert hilo_id is not None, (
        "publicar() debe crear un hilo 1:1 entre coord (asignado_por) y docente (asignado_a)"
    )

    # El asignado_a (docente) debe tener mensajes no leídos
    no_leidos = await mensajeria_repo.contar_no_leidos(hilo_id, docente.id)
    assert no_leidos > 0, (
        "El asignado_a debe tener mensajes no leídos en su campanita tras la asignación"
    )

    # El mensaje debe mencionar la tarea
    mensajes = await mensajeria_repo.obtener_mensajes(hilo_id, docente.id)
    assert len(mensajes) >= 1
    assert "Revisar actas de examen" in mensajes[0].cuerpo or "asignó" in mensajes[0].cuerpo


# ---------------------------------------------------------------------------
# (b) TRIANGULATE: auto-asignación → NO notifica
# ---------------------------------------------------------------------------

@pytest.mark.asyncio(loop_scope="session")
async def test_publicar_autoasignacion_no_notifica(db_session, create_tables):
    """
    (b) TRIANGULATE: si asignado_a == asignado_por (auto-asignación),
    NO debe crearse ningún hilo de mensajería.
    """
    from app.repositories.mensajeria_repository import MensajeriaRepository
    from app.schemas.tarea import TareaCreate

    tid = await _setup_tenant(db_session)

    coord = await create_usuario_con_identidad(
        db_session, tid,
        email=f"coord_auto_{uuid.uuid4().hex[:6]}@t.com",
        nombre="Coord", apellidos="Auto",
    )
    await db_session.commit()

    actor = _actor(tid, coord.auth_identity_id)
    svc = _make_service(db_session, tid)
    mensajeria_repo = MensajeriaRepository(session=db_session, tenant_id=tid)

    # Se asigna a sí mismo
    req = TareaCreate(asignado_a=coord.id, descripcion="Tarea propia")
    await svc.publicar(req, actor, domain_user_id=coord.id)

    # NO debe existir ningún hilo (self-loop)
    hilo_id = await mensajeria_repo.buscar_hilo_existente(coord.id, coord.id)
    assert hilo_id is None, (
        "Auto-asignación: NO debe crearse un hilo de mensajería (nadie a quién notificar)"
    )


# ---------------------------------------------------------------------------
# (c) TRIANGULATE: delegar → notifica al NUEVO asignado_a
# ---------------------------------------------------------------------------

@pytest.mark.asyncio(loop_scope="session")
async def test_delegar_notifica_nuevo_asignado_a(db_session, create_tables):
    """
    (c) TRIANGULATE: al delegar una tarea, el NUEVO asignado_a recibe una
    notificación vía mensajería (hilo + mensaje no leído).
    El asignado original (docente1) NO recibe nueva notificación en el paso de delegación.
    """
    from app.repositories.mensajeria_repository import MensajeriaRepository
    from app.schemas.tarea import TareaCreate

    tid = await _setup_tenant(db_session)

    coord = await create_usuario_con_identidad(
        db_session, tid,
        email=f"coord_del_{uuid.uuid4().hex[:6]}@t.com",
        nombre="Coord", apellidos="Del",
    )
    docente1 = await create_usuario_con_identidad(
        db_session, tid,
        email=f"doc1_del_{uuid.uuid4().hex[:6]}@t.com",
        nombre="Docente1", apellidos="Del",
    )
    docente2 = await create_usuario_con_identidad(
        db_session, tid,
        email=f"doc2_del_{uuid.uuid4().hex[:6]}@t.com",
        nombre="Docente2", apellidos="Del",
    )
    await db_session.commit()

    actor = _actor(tid, coord.auth_identity_id)
    svc = _make_service(db_session, tid)
    mensajeria_repo = MensajeriaRepository(session=db_session, tenant_id=tid)

    # Crear tarea para docente1
    req = TareaCreate(asignado_a=docente1.id, descripcion="Corregir parciales")
    tarea = await svc.publicar(req, actor, domain_user_id=coord.id)

    # Verificar que docente1 recibió notificación al crearse la tarea
    hilo_coord_doc1 = await mensajeria_repo.buscar_hilo_existente(coord.id, docente1.id)
    assert hilo_coord_doc1 is not None, "publicar() debe haber creado hilo coord→docente1"
    no_leidos_doc1_antes = await mensajeria_repo.contar_no_leidos(hilo_coord_doc1, docente1.id)
    assert no_leidos_doc1_antes > 0

    # Delegar a docente2
    await svc.delegar(tarea.id, docente2.id, actor, domain_user_id=coord.id)

    # docente2 debe tener un hilo con mensajes no leídos
    hilo_coord_doc2 = await mensajeria_repo.buscar_hilo_existente(coord.id, docente2.id)
    assert hilo_coord_doc2 is not None, "delegar() debe crear hilo coord→docente2"

    no_leidos_doc2 = await mensajeria_repo.contar_no_leidos(hilo_coord_doc2, docente2.id)
    assert no_leidos_doc2 > 0, (
        "El nuevo asignado_a (docente2) debe tener mensajes no leídos tras delegar"
    )

    # El cuerpo del mensaje debe indicar reasignación
    mensajes_doc2 = await mensajeria_repo.obtener_mensajes(hilo_coord_doc2, docente2.id)
    assert any("reasign" in m.cuerpo.lower() or "deleg" in m.cuerpo.lower() for m in mensajes_doc2), (
        "El mensaje de delegación debe mencionar reasignación o delegación"
    )
