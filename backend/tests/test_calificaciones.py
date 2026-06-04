"""
TDD tests for CalificacionService (preview + importar).

C-10 Design Decisions:
    D3 — aprobado derivado y persistido al importar.
    D7 — linkeo fila → EntradaPadron por email contra el padrón activo.
    D8 — importado_por en la clave única de upsert; re-import actualiza en vez de duplicar.
    D10 — auditoría CALIFICACIONES_IMPORTAR en cada importación exitosa.

Follows the same inline setup + try/finally cleanup pattern as test_padron.py.
Uses real DB, no DB mocks.
"""
import csv
import io
import uuid
from datetime import date

import pytest
from sqlalchemy import select, text

from app.core.dependencies import CurrentUser
from app.models.tenant import Tenant, TenantEstado
from app.models.estructura import Materia, Cohorte, EstadoEstructura, Carrera
from app.models.usuario import Asignacion, RolAsignacion, Usuario, UsuarioEstado
from app.models.padron import VersionPadron, EntradaPadron
from app.models.calificacion import Calificacion
from app.schemas.calificacion import ImportarCalificacionesRequest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _fake_settings():
    class FakeSettings:
        SECRET_KEY = "supersecretkeyfortesting1234567890"
        ENCRYPTION_KEY = "E" * 32
        ACCESS_TOKEN_EXPIRE_MINUTES = 30
        MFA_TOKEN_EXPIRE_MINUTES = 10
        REFRESH_TOKEN_EXPIRE_DAYS = 7
        RECOVERY_TOKEN_EXPIRE_MINUTES = 30
        LOGIN_RATE_LIMIT = "10/minute"
        MOODLE_BASE_URL = None
        MOODLE_TOKEN = None
        MOODLE_SYNC_HOUR = 3
        PADRON_MAX_ROWS = 5000
        UMBRAL_PCT_DEFECTO = 60
        VALORES_APROBATORIOS_DEFECTO = ["Satisfactorio", "Supera lo esperado"]
        NOTA_MAXIMA_DEFECTO = 10.0

    return FakeSettings()


def _make_current_user(user_id: uuid.UUID, tenant_id: uuid.UUID) -> CurrentUser:
    return CurrentUser(user_id=user_id, tenant_id=tenant_id, roles=["PROFESOR"])


def _make_csv_bytes(headers, rows):
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(headers)
    for r in rows:
        w.writerow(r)
    return buf.getvalue().encode("utf-8")


_ESCALA_TEXTUAL = ["Satisfactorio", "Supera lo esperado", "No satisfactorio", "No alcanzado"]
_IDENTITY_HEADERS = ["Nombre", "Apellido(s)", "Dirección de correo"]


async def _create_cal_context(db_session, monkeypatch):
    """
    Create a full context: tenant, carrera, cohorte, materia, usuario+asignacion,
    and an active padron with 2 entries.
    """
    from app.core.security.passwords import email_lookup_hash
    monkeypatch.setattr("app.core.config.Settings", _fake_settings)

    # Ensure session is in clean state
    try:
        await db_session.rollback()
    except Exception:
        pass

    tenant = Tenant(nombre=f"Cal Tenant {uuid.uuid4().hex[:8]}", estado=TenantEstado.ACTIVO)
    db_session.add(tenant)
    await db_session.commit()
    await db_session.refresh(tenant)

    carrera = Carrera(
        tenant_id=tenant.id,
        nombre="Ingeniería Cal",
        codigo=f"ING-{uuid.uuid4().hex[:6]}",
        estado=EstadoEstructura.activa,
    )
    db_session.add(carrera)
    await db_session.commit()
    await db_session.refresh(carrera)

    cohorte = Cohorte(
        tenant_id=tenant.id,
        nombre="Cohorte Cal 2026",
        anio=2026,
        carrera_id=carrera.id,
        vig_desde=date(2026, 3, 1),
        estado=EstadoEstructura.activa,
    )
    db_session.add(cohorte)
    await db_session.commit()
    await db_session.refresh(cohorte)

    materia = Materia(
        tenant_id=tenant.id,
        nombre="Algebra Cal",
        codigo=f"ALG-{uuid.uuid4().hex[:6]}",
        estado=EstadoEstructura.activa,
    )
    db_session.add(materia)
    await db_session.commit()
    await db_session.refresh(materia)

    # PROFESOR
    email_prof = f"prof-{uuid.uuid4().hex[:8]}@cal.test"
    profesor = Usuario(
        tenant_id=tenant.id,
        email_encrypted=email_prof,
        email_hash=email_lookup_hash(email_prof),
        nombre="Prof Cal",
        apellidos="Test",
        estado=UsuarioEstado.activo,
    )
    db_session.add(profesor)
    await db_session.commit()
    await db_session.refresh(profesor)

    asignacion = Asignacion(
        tenant_id=tenant.id,
        usuario_id=profesor.id,
        rol=RolAsignacion.PROFESOR,
        materia_id=materia.id,
        desde=date(2026, 1, 1),
    )
    db_session.add(asignacion)
    await db_session.commit()
    await db_session.refresh(asignacion)

    # Active padron with 2 entries
    version = VersionPadron(
        tenant_id=tenant.id,
        materia_id=materia.id,
        cohorte_id=cohorte.id,
        cargado_por=profesor.id,
        activa=True,
    )
    db_session.add(version)
    await db_session.commit()
    await db_session.refresh(version)

    email_a = f"alumno-a-{uuid.uuid4().hex[:8]}@alumnos.test"
    email_b = f"alumno-b-{uuid.uuid4().hex[:8]}@alumnos.test"

    entry_a = EntradaPadron(
        tenant_id=tenant.id,
        version_id=version.id,
        nombre="Alumno A",
        apellidos="Test",
        email_encrypted=email_a,
    )
    entry_b = EntradaPadron(
        tenant_id=tenant.id,
        version_id=version.id,
        nombre="Alumno B",
        apellidos="Test",
        email_encrypted=email_b,
    )
    db_session.add(entry_a)
    db_session.add(entry_b)
    await db_session.commit()
    await db_session.refresh(entry_a)
    await db_session.refresh(entry_b)

    return {
        "tenant": tenant,
        "carrera": carrera,
        "cohorte": cohorte,
        "materia": materia,
        "profesor": profesor,
        "asignacion": asignacion,
        "version": version,
        "entry_a": entry_a,
        "entry_b": entry_b,
        "email_a": email_a,
        "email_b": email_b,
    }


async def _cleanup_cal(db_session, tenant_id: uuid.UUID):
    tid = str(tenant_id)
    await db_session.execute(text("DELETE FROM audit_event WHERE tenant_id = :tid"), {"tid": tid})
    await db_session.execute(text("DELETE FROM calificacion WHERE tenant_id = :tid"), {"tid": tid})
    await db_session.execute(text("DELETE FROM umbral_materia WHERE tenant_id = :tid"), {"tid": tid})
    await db_session.execute(text("DELETE FROM entrada_padron WHERE tenant_id = :tid"), {"tid": tid})
    await db_session.execute(text("DELETE FROM version_padron WHERE tenant_id = :tid"), {"tid": tid})
    await db_session.execute(text("DELETE FROM asignacion WHERE tenant_id = :tid"), {"tid": tid})
    await db_session.execute(text("DELETE FROM materia WHERE tenant_id = :tid"), {"tid": tid})
    await db_session.execute(text("DELETE FROM cohorte WHERE tenant_id = :tid"), {"tid": tid})
    await db_session.execute(text("DELETE FROM carrera WHERE tenant_id = :tid"), {"tid": tid})
    await db_session.execute(text("DELETE FROM usuario WHERE tenant_id = :tid"), {"tid": tid})
    await db_session.execute(text("DELETE FROM tenants WHERE id = :tid"), {"tid": tid})
    await db_session.commit()


def _make_cal_service(db_session, tenant_id):
    from app.repositories.calificacion_repository import CalificacionRepository
    from app.repositories.padron_repository import PadronRepository
    from app.repositories.audit_repository import AuditRepository
    from app.services.calificacion_service import CalificacionService
    repo = CalificacionRepository(session=db_session, tenant_id=tenant_id)
    padron_repo = PadronRepository(session=db_session, tenant_id=tenant_id)
    audit_repo = AuditRepository(session=db_session, tenant_id=tenant_id)
    return CalificacionService(repo=repo, padron_repo=padron_repo, audit_repo=audit_repo)


# ---------------------------------------------------------------------------
# §9.1 / §9.2 — preview returns activities without DB write
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_preview_returns_activities_without_db_write(db_session, create_tables, monkeypatch):
    """Valid file → activities detected, Calificacion count remains 0."""
    ctx = await _create_cal_context(db_session, monkeypatch)
    tenant = ctx["tenant"]
    materia = ctx["materia"]
    profesor = ctx["profesor"]

    try:
        headers = _IDENTITY_HEADERS + ["Tarea 1 (Real)", "TP 1"]
        rows = [
            ["Alumno A", "Test", ctx["email_a"], "8", "Satisfactorio"],
            ["Alumno B", "Test", ctx["email_b"], "6", "No alcanzado"],
        ]
        file_bytes = _make_csv_bytes(headers, rows)
        svc = _make_cal_service(db_session, tenant.id)
        current_user = _make_current_user(profesor.id, tenant.id)

        result = await svc.preview(file_bytes=file_bytes, filename="notas.csv", current_user=current_user)

        # Activities detected
        assert len(result.actividades) == 2
        names = [a.actividad for a in result.actividades]
        assert "Tarea 1" in names
        assert "TP 1" in names

        # No Calificacion written
        from app.repositories.calificacion_repository import CalificacionRepository
        repo = CalificacionRepository(session=db_session, tenant_id=tenant.id)
        count = await repo.count_calificaciones()
        assert count == 0
    finally:
        await _cleanup_cal(db_session, tenant.id)


# ---------------------------------------------------------------------------
# §9.3 / §9.4 — importar persists only selected activities
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_importar_persists_only_selected_activities(db_session, create_tables, monkeypatch):
    """Detect A,B,C; select A,C → Calificacion only for A and C."""
    ctx = await _create_cal_context(db_session, monkeypatch)
    tenant = ctx["tenant"]
    materia = ctx["materia"]
    cohorte = ctx["cohorte"]
    profesor = ctx["profesor"]
    email_a = ctx["email_a"]
    email_b = ctx["email_b"]

    try:
        headers = _IDENTITY_HEADERS + ["Tarea 1 (Real)", "TP 1", "TP 2"]
        rows = [
            ["Alumno A", "Test", email_a, "8", "Satisfactorio", "No alcanzado"],
            ["Alumno B", "Test", email_b, "6", "No alcanzado", "Satisfactorio"],
        ]
        file_bytes = _make_csv_bytes(headers, rows)
        svc = _make_cal_service(db_session, tenant.id)
        current_user = _make_current_user(profesor.id, tenant.id)

        # First preview to get filas
        preview = await svc.preview(file_bytes=file_bytes, filename="notas.csv", current_user=current_user)

        req = ImportarCalificacionesRequest(
            materia_id=materia.id,
            cohorte_id=cohorte.id,
            actividades_seleccionadas=["Tarea 1", "TP 1"],  # Skip TP 2
            filas=preview.filas,
        )
        result = await svc.importar(req=req, current_user=current_user)

        # Only Tarea 1 and TP 1 were selected — 2 students × 2 activities = 4
        assert len(result) == 4
        activities = {c.actividad for c in result}
        assert "Tarea 1" in activities
        assert "TP 1" in activities
        assert "TP 2" not in activities
    finally:
        await _cleanup_cal(db_session, tenant.id)


# ---------------------------------------------------------------------------
# §9.5 — row not in active padron is reported, not persisted
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_row_not_in_active_padron_is_reported_not_persisted(db_session, create_tables, monkeypatch):
    """Email with no padrón match → in no_en_padron, no Calificacion."""
    ctx = await _create_cal_context(db_session, monkeypatch)
    tenant = ctx["tenant"]
    materia = ctx["materia"]
    cohorte = ctx["cohorte"]
    profesor = ctx["profesor"]
    email_a = ctx["email_a"]
    unknown_email = "unknown@nowhere.test"

    try:
        headers = _IDENTITY_HEADERS + ["Tarea 1 (Real)"]
        rows = [
            ["Alumno A", "Test", email_a, "8"],
            ["Unknown", "User", unknown_email, "5"],
        ]
        file_bytes = _make_csv_bytes(headers, rows)
        svc = _make_cal_service(db_session, tenant.id)
        current_user = _make_current_user(profesor.id, tenant.id)

        preview = await svc.preview(file_bytes=file_bytes, filename="notas.csv", current_user=current_user)

        req = ImportarCalificacionesRequest(
            materia_id=materia.id,
            cohorte_id=cohorte.id,
            actividades_seleccionadas=["Tarea 1"],
            filas=preview.filas,
        )
        # importar returns (calificaciones, no_en_padron)
        cals, not_found = await svc.importar_with_report(req=req, current_user=current_user)

        # Only entry_a matched
        assert len(cals) == 1
        # unknown_email reported as not in padron
        assert unknown_email in not_found
    finally:
        await _cleanup_cal(db_session, tenant.id)


# ---------------------------------------------------------------------------
# §9.6 — import scope isolated per user (RN-04)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_import_scope_isolated_per_user(db_session, create_tables, monkeypatch):
    """A and B import same materia → distinct rows, no overwrite of each other."""
    from app.core.security.passwords import email_lookup_hash

    ctx = await _create_cal_context(db_session, monkeypatch)
    tenant = ctx["tenant"]
    materia = ctx["materia"]
    cohorte = ctx["cohorte"]
    email_a = ctx["email_a"]
    profesor_a = ctx["profesor"]

    # Create a second profesor
    email_prof_b = f"profb-{uuid.uuid4().hex[:8]}@cal.test"
    profesor_b = Usuario(
        tenant_id=tenant.id,
        email_encrypted=email_prof_b,
        email_hash=email_lookup_hash(email_prof_b),
        nombre="Prof B Cal",
        apellidos="Test",
        estado=UsuarioEstado.activo,
    )
    db_session.add(profesor_b)
    await db_session.commit()
    await db_session.refresh(profesor_b)

    asignacion_b = Asignacion(
        tenant_id=tenant.id,
        usuario_id=profesor_b.id,
        rol=RolAsignacion.PROFESOR,
        materia_id=materia.id,
        desde=date(2026, 1, 1),
    )
    db_session.add(asignacion_b)
    await db_session.commit()

    try:
        headers = _IDENTITY_HEADERS + ["Tarea 1 (Real)"]
        rows = [["Alumno A", "Test", email_a, "8"]]
        file_bytes = _make_csv_bytes(headers, rows)

        svc = _make_cal_service(db_session, tenant.id)

        # Profesor A imports
        user_a = _make_current_user(profesor_a.id, tenant.id)
        preview_a = await svc.preview(file_bytes=file_bytes, filename="notas.csv", current_user=user_a)
        req_a = ImportarCalificacionesRequest(
            materia_id=materia.id, cohorte_id=cohorte.id,
            actividades_seleccionadas=["Tarea 1"], filas=preview_a.filas,
        )
        cals_a = await svc.importar(req=req_a, current_user=user_a)

        # Profesor B imports different grades
        rows_b = [["Alumno A", "Test", email_a, "5"]]
        file_bytes_b = _make_csv_bytes(headers, rows_b)
        user_b = _make_current_user(profesor_b.id, tenant.id)
        preview_b = await svc.preview(file_bytes=file_bytes_b, filename="notas.csv", current_user=user_b)
        req_b = ImportarCalificacionesRequest(
            materia_id=materia.id, cohorte_id=cohorte.id,
            actividades_seleccionadas=["Tarea 1"], filas=preview_b.filas,
        )
        cals_b = await svc.importar(req=req_b, current_user=user_b)

        # Two distinct rows: one per importador
        from app.repositories.calificacion_repository import CalificacionRepository
        repo = CalificacionRepository(session=db_session, tenant_id=tenant.id)
        all_cals = await repo.list_by_materia_importador(materia.id, profesor_a.id)
        assert len(all_cals) == 1
        assert float(all_cals[0].nota_numerica) == 8.0

        cals_b_list = await repo.list_by_materia_importador(materia.id, profesor_b.id)
        assert len(cals_b_list) == 1
        assert float(cals_b_list[0].nota_numerica) == 5.0
    finally:
        await _cleanup_cal(db_session, tenant.id)


# ---------------------------------------------------------------------------
# §9.7 — importar records audit CALIFICACIONES_IMPORTAR
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_importar_records_audit_calificaciones_importar(db_session, create_tables, monkeypatch):
    """Successful import → AuditEvent accion='CALIFICACIONES_IMPORTAR', registros_afectados=N."""
    ctx = await _create_cal_context(db_session, monkeypatch)
    tenant = ctx["tenant"]
    materia = ctx["materia"]
    cohorte = ctx["cohorte"]
    profesor = ctx["profesor"]
    email_a = ctx["email_a"]
    email_b = ctx["email_b"]

    try:
        headers = _IDENTITY_HEADERS + ["Tarea 1 (Real)"]
        rows = [
            ["Alumno A", "Test", email_a, "8"],
            ["Alumno B", "Test", email_b, "5"],
        ]
        file_bytes = _make_csv_bytes(headers, rows)
        svc = _make_cal_service(db_session, tenant.id)
        current_user = _make_current_user(profesor.id, tenant.id)

        preview = await svc.preview(file_bytes=file_bytes, filename="notas.csv", current_user=current_user)
        req = ImportarCalificacionesRequest(
            materia_id=materia.id,
            cohorte_id=cohorte.id,
            actividades_seleccionadas=["Tarea 1"],
            filas=preview.filas,
        )
        await svc.importar(req=req, current_user=current_user)

        # Verify audit event was created
        from sqlalchemy import text as sqla_text
        result = await db_session.execute(
            sqla_text(
                "SELECT accion, registros_afectados FROM audit_event "
                "WHERE tenant_id = :tid AND accion = 'CALIFICACIONES_IMPORTAR' "
                "ORDER BY created_at DESC LIMIT 1"
            ),
            {"tid": str(tenant.id)},
        )
        row = result.fetchone()
        assert row is not None, "Audit event CALIFICACIONES_IMPORTAR not found"
        assert row[0] == "CALIFICACIONES_IMPORTAR"
        assert row[1] == 2  # 2 rows × 1 activity = 2
    finally:
        await _cleanup_cal(db_session, tenant.id)


# ---------------------------------------------------------------------------
# §9.8 — re-import same activity updates, not duplicates
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_reimport_same_activity_updates_not_duplicates(db_session, create_tables, monkeypatch):
    """Re-import corrected file → updates nota/aprobado, no duplicate row."""
    ctx = await _create_cal_context(db_session, monkeypatch)
    tenant = ctx["tenant"]
    materia = ctx["materia"]
    cohorte = ctx["cohorte"]
    profesor = ctx["profesor"]
    email_a = ctx["email_a"]

    try:
        headers = _IDENTITY_HEADERS + ["Tarea 1 (Real)"]
        rows_v1 = [["Alumno A", "Test", email_a, "5"]]
        file_bytes_v1 = _make_csv_bytes(headers, rows_v1)
        svc = _make_cal_service(db_session, tenant.id)
        current_user = _make_current_user(profesor.id, tenant.id)

        preview1 = await svc.preview(file_bytes=file_bytes_v1, filename="notas.csv", current_user=current_user)
        req1 = ImportarCalificacionesRequest(
            materia_id=materia.id,
            cohorte_id=cohorte.id,
            actividades_seleccionadas=["Tarea 1"],
            filas=preview1.filas,
        )
        await svc.importar(req=req1, current_user=current_user)

        # Re-import with corrected note
        rows_v2 = [["Alumno A", "Test", email_a, "9"]]
        file_bytes_v2 = _make_csv_bytes(headers, rows_v2)
        preview2 = await svc.preview(file_bytes=file_bytes_v2, filename="notas.csv", current_user=current_user)
        req2 = ImportarCalificacionesRequest(
            materia_id=materia.id,
            cohorte_id=cohorte.id,
            actividades_seleccionadas=["Tarea 1"],
            filas=preview2.filas,
        )
        cals = await svc.importar(req=req2, current_user=current_user)

        # Only 1 row (upsert, not duplicate)
        from app.repositories.calificacion_repository import CalificacionRepository
        repo = CalificacionRepository(session=db_session, tenant_id=tenant.id)
        count = await repo.count_calificaciones()
        assert count == 1
        # Note is updated
        assert float(cals[0].nota_numerica) == 9.0
    finally:
        await _cleanup_cal(db_session, tenant.id)
