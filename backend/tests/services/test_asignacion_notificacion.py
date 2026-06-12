"""
test_asignacion_notificacion.py — TDD: notificación vía mensajería al asignar docentes.

Cubre las 3 altas de asignación:
    1. EquipoService.asignacion_masiva  → notifica a cada uid (skip self-assignment)
    2. EquipoService.clonar_equipo      → notifica solo a los clonados (no omitidas)
    3. AsignacionService.crear_asignacion → notifica al docente asignado (skip self)

Ciclo TDD:
    RED:       test falla porque la notificación no existe.
    GREEN:     implementar helper + llamadas en los tres puntos.
    TRIANGULATE: (a) caso normal; (b) auto-asignación → sin mensaje;
                 (c) duplicado en clonar → sin notificación extra.

DB real: activia_trace_test (postgres nativo localhost:5432).
Sin mocks de DB.
Helper create_usuario_con_identidad del conftest (C-28 invariante).
"""
import uuid
from datetime import date

import pytest

from app.core.dependencies import CurrentUser
from tests.conftest import create_usuario_con_identidad


# ---------------------------------------------------------------------------
# Helpers locales
# ---------------------------------------------------------------------------

def _actor(tenant_id: uuid.UUID, domain_user_id: uuid.UUID, roles=None) -> CurrentUser:
    """CurrentUser con user_id = domain_user_id (para tests directos al service)."""
    return CurrentUser(user_id=domain_user_id, tenant_id=tenant_id, roles=roles or ["COORDINADOR"])


async def _setup_tenant(session) -> uuid.UUID:
    """Crea un tenant aislado. Retorna tid."""
    from app.models.tenant import Tenant, TenantEstado

    tid = uuid.uuid4()
    session.add(Tenant(id=tid, nombre=f"AsigNotif_{tid.hex[:4]}", estado=TenantEstado.ACTIVO))
    await session.flush()
    return tid


async def _setup_estructura(session, tid: uuid.UUID, suffix: str):
    """Crea una tripleta materia/carrera/cohorte. Retorna (mat_id, car_id, coh_id)."""
    from app.models.estructura import Carrera, Cohorte, EstadoEstructura, Materia

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
        anio=2025,
        vig_desde=date.today(),
        estado=EstadoEstructura.activa,
    )
    session.add(cohorte)
    await session.flush()
    return materia.id, carrera.id, cohorte.id


def _make_equipo_service(session, tenant_id: uuid.UUID):
    from app.repositories.audit_repository import AuditRepository
    from app.repositories.estructura_repository import CohorteRepository, MateriaRepository
    from app.repositories.mensajeria_repository import MensajeriaRepository
    from app.repositories.usuario_repository import AsignacionRepository, UsuarioRepository
    from app.services.equipo_service import EquipoService

    return EquipoService(
        asignacion_repo=AsignacionRepository(session=session, tenant_id=tenant_id),
        usuario_repo=UsuarioRepository(session=session, tenant_id=tenant_id),
        audit_repo=AuditRepository(session=session, tenant_id=tenant_id),
        mensajeria_repo=MensajeriaRepository(session=session, tenant_id=tenant_id),
        materia_repo=MateriaRepository(session=session, tenant_id=tenant_id),
        cohorte_repo=CohorteRepository(session=session, tenant_id=tenant_id),
    )


def _make_asignacion_service(session, tenant_id: uuid.UUID):
    from app.repositories.estructura_repository import CohorteRepository, MateriaRepository
    from app.repositories.mensajeria_repository import MensajeriaRepository
    from app.repositories.usuario_repository import AsignacionRepository, UsuarioRepository
    from app.services.usuario_service import AsignacionService

    return AsignacionService(
        asignacion_repo=AsignacionRepository(session=session, tenant_id=tenant_id),
        usuario_repo=UsuarioRepository(session=session, tenant_id=tenant_id),
        mensajeria_repo=MensajeriaRepository(session=session, tenant_id=tenant_id),
        materia_repo=MateriaRepository(session=session, tenant_id=tenant_id),
        cohorte_repo=CohorteRepository(session=session, tenant_id=tenant_id),
    )


# ---------------------------------------------------------------------------
# TASK A — asignacion_masiva: notifica a cada uid != actor
# ---------------------------------------------------------------------------

@pytest.mark.asyncio(loop_scope="session")
async def test_asignacion_masiva_notifica_a_cada_docente(db_session, create_tables):
    """
    RED A.1 / GREEN A.1: asignacion_masiva notifica a cada usuario_id vía mensajería.

    El actor (coordinador) asigna a dos docentes.
    Cada docente debe quedar con al menos un mensaje no leído del actor.
    """
    from app.repositories.mensajeria_repository import MensajeriaRepository
    from app.models.usuario import RolAsignacion
    from app.schemas.equipo import AsignacionMasivaRequest

    tid = await _setup_tenant(db_session)
    mat_id, car_id, coh_id = await _setup_estructura(db_session, tid, "mas_notif")

    coord = await create_usuario_con_identidad(
        db_session, tid,
        email=f"coord_mn_{uuid.uuid4().hex[:6]}@t.com",
        nombre="Coord", apellidos="MasNotif",
    )
    docente1 = await create_usuario_con_identidad(
        db_session, tid,
        email=f"doc1_mn_{uuid.uuid4().hex[:6]}@t.com",
        nombre="Docente1", apellidos="MasNotif",
    )
    docente2 = await create_usuario_con_identidad(
        db_session, tid,
        email=f"doc2_mn_{uuid.uuid4().hex[:6]}@t.com",
        nombre="Docente2", apellidos="MasNotif",
    )
    await db_session.commit()

    actor = _actor(tid, coord.id)
    svc = _make_equipo_service(db_session, tid)
    mensajeria_repo = MensajeriaRepository(session=db_session, tenant_id=tid)

    req = AsignacionMasivaRequest(
        usuario_ids=[docente1.id, docente2.id],
        materia_id=mat_id,
        carrera_id=car_id,
        cohorte_id=coh_id,
        rol=RolAsignacion.PROFESOR,
        desde=date.today(),
    )
    resultado = await svc.asignacion_masiva(actor, req, domain_user_id=coord.id)

    assert resultado.creadas == 2

    # Docente1 debe tener hilo+mensaje del coord
    hilo1 = await mensajeria_repo.buscar_hilo_existente(coord.id, docente1.id)
    assert hilo1 is not None, "Docente1 debe tener hilo con el coord tras asignacion_masiva"
    no_leidos1 = await mensajeria_repo.contar_no_leidos(hilo1, docente1.id)
    assert no_leidos1 > 0, "Docente1 debe tener mensajes no leídos (campanita)"

    # Docente2 también
    hilo2 = await mensajeria_repo.buscar_hilo_existente(coord.id, docente2.id)
    assert hilo2 is not None, "Docente2 debe tener hilo con el coord tras asignacion_masiva"
    no_leidos2 = await mensajeria_repo.contar_no_leidos(hilo2, docente2.id)
    assert no_leidos2 > 0, "Docente2 debe tener mensajes no leídos (campanita)"

    # Los mensajes deben mencionar la asignación
    mensajes1 = await mensajeria_repo.obtener_mensajes(hilo1, docente1.id)
    assert any("asignado" in m.cuerpo.lower() or "asignación" in m.asunto.lower() for m in mensajes1)


@pytest.mark.asyncio(loop_scope="session")
async def test_asignacion_masiva_autoasignacion_no_crea_hilo_propio(db_session, create_tables):
    """
    TRIANGULATE A.2: si el actor se asigna SOLO a sí mismo (lista con solo su propio ID),
    NO debe crearse ningún hilo de mensajería.

    Verifica la guarda: remitente_id == destinatario_id → return early.
    """
    from app.models.mensajeria import HiloMensaje
    from app.models.usuario import RolAsignacion
    from app.schemas.equipo import AsignacionMasivaRequest
    from sqlalchemy import select, func

    tid = await _setup_tenant(db_session)
    mat_id, car_id, coh_id = await _setup_estructura(db_session, tid, "mas_self_solo")

    coord = await create_usuario_con_identidad(
        db_session, tid,
        email=f"coord_solo_{uuid.uuid4().hex[:6]}@t.com",
        nombre="Coord", apellidos="Solo",
    )
    await db_session.commit()

    actor = _actor(tid, coord.id)
    svc = _make_equipo_service(db_session, tid)

    # Contar hilos ANTES de la operación para el tenant aislado
    stmt_antes = select(func.count()).select_from(HiloMensaje).where(
        HiloMensaje.tenant_id == tid,
        HiloMensaje.deleted_at.is_(None),
    )
    hilos_antes = (await db_session.execute(stmt_antes)).scalar() or 0

    # El actor se asigna SOLO a sí mismo
    req = AsignacionMasivaRequest(
        usuario_ids=[coord.id],
        materia_id=mat_id,
        carrera_id=car_id,
        cohorte_id=coh_id,
        rol=RolAsignacion.COORDINADOR,
        desde=date.today(),
    )
    resultado = await svc.asignacion_masiva(actor, req, domain_user_id=coord.id)
    assert resultado.creadas == 1

    # NO debe haberse creado ningún HiloMensaje nuevo para este tenant
    hilos_despues = (await db_session.execute(stmt_antes)).scalar() or 0
    assert hilos_despues == hilos_antes, (
        "Auto-asignación pura: no debe crearse ningún hilo de mensajería"
    )


# ---------------------------------------------------------------------------
# TASK B — clonar_equipo: notifica to_clone, NO omitidas/duplicados
# ---------------------------------------------------------------------------

@pytest.mark.asyncio(loop_scope="session")
async def test_clonar_equipo_notifica_clonados_no_omitidos(db_session, create_tables):
    """
    RED B.1 / GREEN B.1: clonar_equipo notifica a los docentes efectivamente clonados.
    Los duplicados (omitidas) NO generan notificación adicional.
    """
    from app.repositories.mensajeria_repository import MensajeriaRepository
    from app.models.usuario import Asignacion, RolAsignacion
    from app.repositories.usuario_repository import AsignacionRepository
    from app.schemas.equipo import ClonarEquipoRequest

    tid = await _setup_tenant(db_session)
    mat_o, car_o, coh_o = await _setup_estructura(db_session, tid, "clon_origen")
    mat_d, car_d, coh_d = await _setup_estructura(db_session, tid, "clon_destino")

    coord = await create_usuario_con_identidad(
        db_session, tid,
        email=f"coord_clon_{uuid.uuid4().hex[:6]}@t.com",
        nombre="Coord", apellidos="Clon",
    )
    docente1 = await create_usuario_con_identidad(
        db_session, tid,
        email=f"doc1_clon_{uuid.uuid4().hex[:6]}@t.com",
        nombre="Docente1", apellidos="Clon",
    )
    docente2 = await create_usuario_con_identidad(
        db_session, tid,
        email=f"doc2_clon_{uuid.uuid4().hex[:6]}@t.com",
        nombre="Docente2", apellidos="Clon",
    )
    await db_session.flush()

    # Crear equipo origen con ambos docentes
    asig_repo = AsignacionRepository(session=db_session, tenant_id=tid)
    ao1 = Asignacion(
        usuario_id=docente1.id, rol=RolAsignacion.PROFESOR,
        materia_id=mat_o, carrera_id=car_o, cohorte_id=coh_o,
        desde=date.today(), comisiones=[],
    )
    ao2 = Asignacion(
        usuario_id=docente2.id, rol=RolAsignacion.TUTOR,
        materia_id=mat_o, carrera_id=car_o, cohorte_id=coh_o,
        desde=date.today(), comisiones=[],
    )
    await asig_repo.add(ao1)
    await asig_repo.add(ao2)

    # Docente2 ya existe en el destino (duplicado / omitida)
    ad2_prev = Asignacion(
        usuario_id=docente2.id, rol=RolAsignacion.TUTOR,
        materia_id=mat_d, carrera_id=car_d, cohorte_id=coh_d,
        desde=date.today(), comisiones=[],
    )
    await asig_repo.add(ad2_prev)
    await db_session.commit()

    actor = _actor(tid, coord.id)
    svc = _make_equipo_service(db_session, tid)
    mensajeria_repo = MensajeriaRepository(session=db_session, tenant_id=tid)

    req = ClonarEquipoRequest(
        origen_materia_id=mat_o,
        origen_carrera_id=car_o,
        origen_cohorte_id=coh_o,
        destino_materia_id=mat_d,
        destino_carrera_id=car_d,
        destino_cohorte_id=coh_d,
        desde=date.today(),
    )
    resultado = await svc.clonar_equipo(actor, req, domain_user_id=coord.id)

    # Solo docente1 fue clonado (docente2 era duplicado)
    assert resultado.clonadas == 1
    assert resultado.omitidas == 1

    # Docente1 (clonado) debe recibir notificación
    hilo1 = await mensajeria_repo.buscar_hilo_existente(coord.id, docente1.id)
    assert hilo1 is not None, "Docente1 (clonado) debe recibir notificación"
    no_leidos1 = await mensajeria_repo.contar_no_leidos(hilo1, docente1.id)
    assert no_leidos1 > 0

    # Docente2 (omitida/duplicado) NO debe recibir notificación nueva
    hilo2 = await mensajeria_repo.buscar_hilo_existente(coord.id, docente2.id)
    assert hilo2 is None, "Docente2 (omitida) NO debe recibir notificación nueva por el clonar"


@pytest.mark.asyncio(loop_scope="session")
async def test_clonar_equipo_reclonado_no_notifica(db_session, create_tables):
    """
    TRIANGULATE B.2: re-clonar (todos duplicados) → 0 clonadas, 0 notificaciones.
    """
    from app.repositories.mensajeria_repository import MensajeriaRepository
    from app.models.usuario import Asignacion, RolAsignacion
    from app.repositories.usuario_repository import AsignacionRepository
    from app.schemas.equipo import ClonarEquipoRequest

    tid = await _setup_tenant(db_session)
    mat_o, car_o, coh_o = await _setup_estructura(db_session, tid, "reclon_o")
    mat_d, car_d, coh_d = await _setup_estructura(db_session, tid, "reclon_d")

    coord = await create_usuario_con_identidad(
        db_session, tid,
        email=f"coord_rc_{uuid.uuid4().hex[:6]}@t.com",
        nombre="Coord", apellidos="RC",
    )
    docente = await create_usuario_con_identidad(
        db_session, tid,
        email=f"doc_rc_{uuid.uuid4().hex[:6]}@t.com",
        nombre="Docente", apellidos="RC",
    )
    await db_session.flush()

    asig_repo = AsignacionRepository(session=db_session, tenant_id=tid)
    # En origen y en destino ya existe la misma asignación
    for mat, car, coh in [(mat_o, car_o, coh_o), (mat_d, car_d, coh_d)]:
        a = Asignacion(
            usuario_id=docente.id, rol=RolAsignacion.PROFESOR,
            materia_id=mat, carrera_id=car, cohorte_id=coh,
            desde=date.today(), comisiones=[],
        )
        await asig_repo.add(a)
    await db_session.commit()

    actor = _actor(tid, coord.id)
    svc = _make_equipo_service(db_session, tid)
    mensajeria_repo = MensajeriaRepository(session=db_session, tenant_id=tid)

    req = ClonarEquipoRequest(
        origen_materia_id=mat_o, origen_carrera_id=car_o, origen_cohorte_id=coh_o,
        destino_materia_id=mat_d, destino_carrera_id=car_d, destino_cohorte_id=coh_d,
        desde=date.today(),
    )
    resultado = await svc.clonar_equipo(actor, req, domain_user_id=coord.id)

    assert resultado.clonadas == 0
    assert resultado.omitidas == 1

    # Sin clonaciones → sin notificaciones nuevas
    hilo = await mensajeria_repo.buscar_hilo_existente(coord.id, docente.id)
    assert hilo is None, "Sin clonaciones → no debe haber notificación"


# ---------------------------------------------------------------------------
# TASK C — AsignacionService.crear_asignacion: notifica al docente
# ---------------------------------------------------------------------------

@pytest.mark.asyncio(loop_scope="session")
async def test_crear_asignacion_individual_notifica_docente(db_session, create_tables):
    """
    RED C.1 / GREEN C.1: crear_asignacion individual notifica al docente asignado.
    """
    from app.repositories.mensajeria_repository import MensajeriaRepository
    from app.models.usuario import RolAsignacion

    tid = await _setup_tenant(db_session)
    mat_id, car_id, coh_id = await _setup_estructura(db_session, tid, "ind_notif")

    coord = await create_usuario_con_identidad(
        db_session, tid,
        email=f"coord_ind_{uuid.uuid4().hex[:6]}@t.com",
        nombre="Coord", apellidos="Ind",
    )
    docente = await create_usuario_con_identidad(
        db_session, tid,
        email=f"doc_ind_{uuid.uuid4().hex[:6]}@t.com",
        nombre="Docente", apellidos="Ind",
    )
    await db_session.commit()

    actor = _actor(tid, coord.id)
    svc = _make_asignacion_service(db_session, tid)
    mensajeria_repo = MensajeriaRepository(session=db_session, tenant_id=tid)

    asignacion = await svc.crear_asignacion(
        actor,
        usuario_id=docente.id,
        rol=RolAsignacion.TUTOR,
        desde=date.today(),
        materia_id=mat_id,
        carrera_id=car_id,
        cohorte_id=coh_id,
        domain_user_id=coord.id,
    )

    assert asignacion is not None

    # El docente debe tener un hilo con el coord y mensajes no leídos
    hilo = await mensajeria_repo.buscar_hilo_existente(coord.id, docente.id)
    assert hilo is not None, "crear_asignacion debe crear hilo coord→docente"
    no_leidos = await mensajeria_repo.contar_no_leidos(hilo, docente.id)
    assert no_leidos > 0, "El docente debe tener mensajes no leídos (campanita)"

    # El mensaje debe mencionar la asignación
    mensajes = await mensajeria_repo.obtener_mensajes(hilo, docente.id)
    assert len(mensajes) >= 1
    assert any("asignado" in m.cuerpo.lower() for m in mensajes)


@pytest.mark.asyncio(loop_scope="session")
async def test_crear_asignacion_autoasignacion_no_notifica(db_session, create_tables):
    """
    TRIANGULATE C.2: si el actor se asigna a sí mismo → no notificación.
    """
    from app.repositories.mensajeria_repository import MensajeriaRepository
    from app.models.usuario import RolAsignacion

    tid = await _setup_tenant(db_session)
    mat_id, car_id, coh_id = await _setup_estructura(db_session, tid, "self_notif")

    coord = await create_usuario_con_identidad(
        db_session, tid,
        email=f"coord_self2_{uuid.uuid4().hex[:6]}@t.com",
        nombre="Coord", apellidos="SelfAsig",
    )
    await db_session.commit()

    actor = _actor(tid, coord.id)
    svc = _make_asignacion_service(db_session, tid)
    mensajeria_repo = MensajeriaRepository(session=db_session, tenant_id=tid)

    # El actor se asigna a sí mismo
    asignacion = await svc.crear_asignacion(
        actor,
        usuario_id=coord.id,
        rol=RolAsignacion.COORDINADOR,
        desde=date.today(),
        materia_id=mat_id,
        carrera_id=car_id,
        cohorte_id=coh_id,
        domain_user_id=coord.id,  # actor == destinatario
    )

    assert asignacion is not None

    # Auto-asignación: NO debe existir hilo (nadie a quien notificar)
    hilo_self = await mensajeria_repo.buscar_hilo_existente(coord.id, coord.id)
    assert hilo_self is None, "Auto-asignación: no debe haber notificación"


@pytest.mark.asyncio(loop_scope="session")
async def test_crear_asignacion_sin_mensajeria_repo_no_falla(db_session, create_tables):
    """
    TRIANGULATE C.3: crear_asignacion sin mensajeria_repo (None) debe funcionar
    normalmente, solo sin notificación (backward-compatible).
    """
    from app.models.usuario import RolAsignacion
    from app.repositories.usuario_repository import AsignacionRepository, UsuarioRepository
    from app.services.usuario_service import AsignacionService

    tid = await _setup_tenant(db_session)
    mat_id, car_id, coh_id = await _setup_estructura(db_session, tid, "no_msg_repo")

    coord = await create_usuario_con_identidad(
        db_session, tid,
        email=f"coord_nmr_{uuid.uuid4().hex[:6]}@t.com",
        nombre="Coord", apellidos="NoMsgRepo",
    )
    docente = await create_usuario_con_identidad(
        db_session, tid,
        email=f"doc_nmr_{uuid.uuid4().hex[:6]}@t.com",
        nombre="Docente", apellidos="NoMsgRepo",
    )
    await db_session.commit()

    # Service SIN mensajeria_repo (como antes de la feature)
    svc = AsignacionService(
        asignacion_repo=AsignacionRepository(session=db_session, tenant_id=tid),
        usuario_repo=UsuarioRepository(session=db_session, tenant_id=tid),
        mensajeria_repo=None,
    )

    actor = _actor(tid, coord.id)

    # Debe funcionar sin error, sin notificación
    asignacion = await svc.crear_asignacion(
        actor,
        usuario_id=docente.id,
        rol=RolAsignacion.PROFESOR,
        desde=date.today(),
        materia_id=mat_id,
        domain_user_id=coord.id,
    )
    assert asignacion is not None


# ---------------------------------------------------------------------------
# TASK D — Nombres legibles en el cuerpo del mensaje
# ---------------------------------------------------------------------------

@pytest.mark.asyncio(loop_scope="session")
async def test_notificacion_muestra_nombres_legibles_no_uuids(db_session, create_tables):
    """
    RED D.1 / GREEN D.1: el cuerpo del mensaje de notificación debe mostrar
    los NOMBRES de materia y cohorte, NO los UUIDs crudos.

    Crea materia 'Análisis Matemático I' y cohorte '2026-2C', asigna un docente,
    y verifica que el cuerpo contiene los nombres legibles.
    """
    from app.models.estructura import Carrera, Cohorte, EstadoEstructura, Materia
    from app.models.usuario import RolAsignacion
    from app.repositories.mensajeria_repository import MensajeriaRepository
    from app.schemas.equipo import AsignacionMasivaRequest

    tid = await _setup_tenant(db_session)

    # Crear estructura con nombres conocidos y verificables
    carrera = Carrera(
        tenant_id=tid,
        codigo=f"CAR_{uuid.uuid4().hex[:6]}",
        nombre="Ingeniería en Sistemas",
        estado=EstadoEstructura.activa,
    )
    materia = Materia(
        tenant_id=tid,
        codigo=f"MAT_{uuid.uuid4().hex[:6]}",
        nombre="Análisis Matemático I",
        estado=EstadoEstructura.activa,
    )
    db_session.add(carrera)
    db_session.add(materia)
    await db_session.flush()

    cohorte = Cohorte(
        tenant_id=tid,
        carrera_id=carrera.id,
        nombre="2026-2C",
        anio=2026,
        vig_desde=date.today(),
        estado=EstadoEstructura.activa,
    )
    db_session.add(cohorte)
    await db_session.flush()

    coord = await create_usuario_con_identidad(
        db_session, tid,
        email=f"coord_nombres_{uuid.uuid4().hex[:6]}@t.com",
        nombre="Coord", apellidos="Nombres",
    )
    docente = await create_usuario_con_identidad(
        db_session, tid,
        email=f"doc_nombres_{uuid.uuid4().hex[:6]}@t.com",
        nombre="Docente", apellidos="Nombres",
    )
    await db_session.commit()

    actor = _actor(tid, coord.id)
    svc = _make_equipo_service(db_session, tid)
    mensajeria_repo = MensajeriaRepository(session=db_session, tenant_id=tid)

    req = AsignacionMasivaRequest(
        usuario_ids=[docente.id],
        materia_id=materia.id,
        carrera_id=carrera.id,
        cohorte_id=cohorte.id,
        rol=RolAsignacion.PROFESOR,
        desde=date.today(),
    )
    resultado = await svc.asignacion_masiva(actor, req, domain_user_id=coord.id)
    assert resultado.creadas == 1

    hilo = await mensajeria_repo.buscar_hilo_existente(coord.id, docente.id)
    assert hilo is not None

    mensajes = await mensajeria_repo.obtener_mensajes(hilo, docente.id)
    assert len(mensajes) >= 1

    cuerpo = mensajes[0].cuerpo
    # El cuerpo DEBE contener los nombres legibles
    assert "Análisis Matemático I" in cuerpo, (
        f"El cuerpo debería contener el nombre de materia. Cuerpo actual: {cuerpo!r}"
    )
    assert "2026-2C" in cuerpo, (
        f"El cuerpo debería contener el nombre de cohorte. Cuerpo actual: {cuerpo!r}"
    )
    # El cuerpo NO debe contener el UUID crudo de materia ni de cohorte
    assert str(materia.id) not in cuerpo, (
        f"El UUID de materia no debe aparecer en el cuerpo. Cuerpo actual: {cuerpo!r}"
    )
    assert str(cohorte.id) not in cuerpo, (
        f"El UUID de cohorte no debe aparecer en el cuerpo. Cuerpo actual: {cuerpo!r}"
    )


@pytest.mark.asyncio(loop_scope="session")
async def test_notificacion_individual_muestra_nombres_legibles(db_session, create_tables):
    """
    TRIANGULATE D.2: AsignacionService.crear_asignacion también muestra nombres legibles.
    """
    from app.models.usuario import RolAsignacion
    from app.repositories.mensajeria_repository import MensajeriaRepository

    tid = await _setup_tenant(db_session)
    mat_id, car_id, coh_id = await _setup_estructura(db_session, tid, "ind_nombres")

    # Recuperar los nombres creados por _setup_estructura para verificar
    from sqlalchemy import select
    from app.models.estructura import Cohorte, Materia

    mat_row = (await db_session.execute(
        select(Materia).where(Materia.id == mat_id)
    )).scalar_one()
    coh_row = (await db_session.execute(
        select(Cohorte).where(Cohorte.id == coh_id)
    )).scalar_one()

    coord = await create_usuario_con_identidad(
        db_session, tid,
        email=f"coord_ind2_{uuid.uuid4().hex[:6]}@t.com",
        nombre="Coord", apellidos="IndNombres",
    )
    docente = await create_usuario_con_identidad(
        db_session, tid,
        email=f"doc_ind2_{uuid.uuid4().hex[:6]}@t.com",
        nombre="Docente", apellidos="IndNombres",
    )
    await db_session.commit()

    actor = _actor(tid, coord.id)
    svc = _make_asignacion_service(db_session, tid)
    mensajeria_repo = MensajeriaRepository(session=db_session, tenant_id=tid)

    await svc.crear_asignacion(
        actor,
        usuario_id=docente.id,
        rol=RolAsignacion.TUTOR,
        desde=date.today(),
        materia_id=mat_id,
        carrera_id=car_id,
        cohorte_id=coh_id,
        domain_user_id=coord.id,
    )

    hilo = await mensajeria_repo.buscar_hilo_existente(coord.id, docente.id)
    assert hilo is not None

    mensajes = await mensajeria_repo.obtener_mensajes(hilo, docente.id)
    assert len(mensajes) >= 1

    cuerpo = mensajes[0].cuerpo
    assert mat_row.nombre in cuerpo, (
        f"El nombre de materia '{mat_row.nombre}' debe estar en el cuerpo: {cuerpo!r}"
    )
    assert coh_row.nombre in cuerpo, (
        f"El nombre de cohorte '{coh_row.nombre}' debe estar en el cuerpo: {cuerpo!r}"
    )
    assert str(mat_id) not in cuerpo, (
        f"El UUID de materia no debe aparecer en el cuerpo: {cuerpo!r}"
    )
    assert str(coh_id) not in cuerpo, (
        f"El UUID de cohorte no debe aparecer en el cuerpo: {cuerpo!r}"
    )
