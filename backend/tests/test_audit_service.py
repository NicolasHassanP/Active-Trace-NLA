"""
test_audit_service.py — Tasks 7.1–7.4, 10.1–10.3 RED/GREEN/TRIANGULATE

Tests for AuditService (D7, RN-24, RN-41).

Coverage:
  7.1 RED   — record() with valid action persists event;
              invalid action raises InvalidAuditAction and does NOT persist.
  7.2 GREEN — AuditService implemented (verified by tests).
  7.3 RED   — Attribution: impersonated event has both actor and impersonated user;
              non-impersonated event has no impersonated_user_id.
  7.4 REFACTOR — PII redaction integrated inside record() — tested via
                 record() calls that include sensitive before/after data.
  10.1 RED  — record_impersonation_start emits IMPERSONACION_INICIO.
  10.2 RED  — record_impersonation_end emits IMPERSONACION_FIN.
  10.3 GREEN — convenience methods implemented.

Uses real DB (no mocks). Requires conftest session/db fixtures.
"""
import uuid
import pytest
import pytest_asyncio

from app.core.dependencies import CurrentUser
from app.models.audit import AuditAction, AuditResultado
from app.models.tenant import Tenant, TenantEstado
from app.repositories.audit_repository import AuditRepository
from app.services.audit_service import AuditService, InvalidAuditAction


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _make_tenant(db_session) -> uuid.UUID:
    """Create a real Tenant row and return its id (satisfies audit_event FK)."""
    tid = uuid.uuid4()
    tenant = Tenant(id=tid, nombre=f"AuditSvc Tenant {tid.hex[:8]}", estado=TenantEstado.ACTIVO)
    db_session.add(tenant)
    await db_session.commit()
    return tid


def _make_user(tenant_id: uuid.UUID) -> CurrentUser:
    return CurrentUser(
        user_id=uuid.uuid4(),
        tenant_id=tenant_id,
        roles=["ADMIN"],
    )


def _make_service(db_session, tenant_id: uuid.UUID) -> AuditService:
    repo = AuditRepository(session=db_session, tenant_id=tenant_id)
    return AuditService(repository=repo)


# ---------------------------------------------------------------------------
# Task 7.1 — record() with valid/invalid actions
# ---------------------------------------------------------------------------

@pytest.mark.asyncio(loop_scope="session")
async def test_audit_service_record_valid_action_persists(db_session, create_tables):
    """record() with a catalog action persists the event."""
    tenant_id = await _make_tenant(db_session)
    actor = _make_user(tenant_id)
    svc = _make_service(db_session, tenant_id)

    event = await svc.record(
        actor=actor,
        action=AuditAction.AUDITORIA_CONSULTA,
        modulo="auditoria",
        entidad_tipo="AuditEvent",
        resultado=AuditResultado.ok,
    )

    assert event.id is not None
    assert event.accion == AuditAction.AUDITORIA_CONSULTA
    assert event.actor_user_id == actor.user_id
    assert event.tenant_id == tenant_id


@pytest.mark.asyncio(loop_scope="session")
async def test_audit_service_record_invalid_action_raises_and_does_not_persist(
    db_session, create_tables
):
    """record() with an arbitrary string raises InvalidAuditAction; no DB write."""
    tenant_id = await _make_tenant(db_session)
    actor = _make_user(tenant_id)
    svc = _make_service(db_session, tenant_id)
    repo = AuditRepository(session=db_session, tenant_id=tenant_id)

    count_before = len(await repo.list())

    with pytest.raises(InvalidAuditAction):
        await svc.record(
            actor=actor,
            action="RANDOM_UNKNOWN",  # type: ignore[arg-type]
            modulo="test",
            entidad_tipo="Foo",
            resultado=AuditResultado.fail,
        )

    count_after = len(await repo.list())
    assert count_after == count_before, "No event should be persisted for invalid action"


# ---------------------------------------------------------------------------
# Task 7.3 — Attribution: impersonation vs. non-impersonation
# ---------------------------------------------------------------------------

@pytest.mark.asyncio(loop_scope="session")
async def test_audit_service_record_without_impersonation(db_session, create_tables):
    """RN-41: non-impersonated event has impersonated_user_id = None."""
    tenant_id = await _make_tenant(db_session)
    actor = _make_user(tenant_id)
    svc = _make_service(db_session, tenant_id)

    event = await svc.record(
        actor=actor,
        action=AuditAction.AUDITORIA_CONSULTA,
        modulo="auditoria",
        entidad_tipo="AuditEvent",
        resultado=AuditResultado.ok,
    )

    assert event.actor_user_id == actor.user_id
    assert event.impersonated_user_id is None


@pytest.mark.asyncio(loop_scope="session")
async def test_audit_service_record_under_impersonation_attributes_real_actor(
    db_session, create_tables
):
    """RN-41: under impersonation the real actor is recorded, impersonated stored separately."""
    tenant_id = await _make_tenant(db_session)
    real_actor = _make_user(tenant_id)
    impersonated_id = uuid.uuid4()
    svc = _make_service(db_session, tenant_id)

    event = await svc.record(
        actor=real_actor,
        action=AuditAction.IMPERSONACION_INICIO,
        modulo="impersonacion",
        entidad_tipo="User",
        resultado=AuditResultado.ok,
        impersonated_user_id=impersonated_id,
    )

    # Attribution is the real actor, not the impersonated user
    assert event.actor_user_id == real_actor.user_id
    assert event.impersonated_user_id == impersonated_id


# ---------------------------------------------------------------------------
# Task 7.4 — PII redaction integrated inside record()
# ---------------------------------------------------------------------------

@pytest.mark.asyncio(loop_scope="session")
async def test_audit_service_record_redacts_pii_in_before(db_session, create_tables):
    """record() persists before with sensitive values redacted."""
    tenant_id = await _make_tenant(db_session)
    actor = _make_user(tenant_id)
    svc = _make_service(db_session, tenant_id)

    event = await svc.record(
        actor=actor,
        action=AuditAction.AUDITORIA_CONSULTA,
        modulo="auditoria",
        entidad_tipo="User",
        resultado=AuditResultado.ok,
        before={"cbu": "0000111122223333444455556666", "nombre": "Ana"},
    )

    assert event.before["cbu"] == "[REDACTED]"
    assert event.before["nombre"] == "Ana"


@pytest.mark.asyncio(loop_scope="session")
async def test_audit_service_record_redacts_pii_in_after(db_session, create_tables):
    """record() persists after with password redacted."""
    tenant_id = await _make_tenant(db_session)
    actor = _make_user(tenant_id)
    svc = _make_service(db_session, tenant_id)

    event = await svc.record(
        actor=actor,
        action=AuditAction.AUDITORIA_CONSULTA,
        modulo="auditoria",
        entidad_tipo="User",
        resultado=AuditResultado.ok,
        after={"password": "newsecret123", "email": "user@example.com"},
    )

    assert event.after["password"] == "[REDACTED]"
    assert event.after["email"] == "user@example.com"


# ---------------------------------------------------------------------------
# Tasks 10.1–10.3 — Impersonation convenience methods
# ---------------------------------------------------------------------------

@pytest.mark.asyncio(loop_scope="session")
async def test_audit_service_record_impersonation_start(db_session, create_tables):
    """Task 10.1: record_impersonation_start emits IMPERSONACION_INICIO."""
    tenant_id = await _make_tenant(db_session)
    actor = _make_user(tenant_id)
    impersonated_id = uuid.uuid4()
    svc = _make_service(db_session, tenant_id)

    event = await svc.record_impersonation_start(
        actor=actor,
        impersonated_user_id=impersonated_id,
        ip="10.0.0.1",
    )

    assert event.accion == AuditAction.IMPERSONACION_INICIO
    assert event.actor_user_id == actor.user_id
    assert event.impersonated_user_id == impersonated_id
    assert event.ip == "10.0.0.1"
    assert event.created_at is not None


@pytest.mark.asyncio(loop_scope="session")
async def test_audit_service_record_impersonation_end(db_session, create_tables):
    """Task 10.2: record_impersonation_end emits IMPERSONACION_FIN."""
    tenant_id = await _make_tenant(db_session)
    actor = _make_user(tenant_id)
    impersonated_id = uuid.uuid4()
    svc = _make_service(db_session, tenant_id)

    event = await svc.record_impersonation_end(
        actor=actor,
        impersonated_user_id=impersonated_id,
        user_agent="Mozilla/5.0",
    )

    assert event.accion == AuditAction.IMPERSONACION_FIN
    assert event.actor_user_id == actor.user_id
    assert event.impersonated_user_id == impersonated_id
    assert event.user_agent == "Mozilla/5.0"
    assert event.created_at is not None


@pytest.mark.asyncio(loop_scope="session")
async def test_audit_service_impersonation_start_and_end_both_attributed_to_real_actor(
    db_session, create_tables
):
    """Triangulation: both impersonation events attribute the real actor."""
    tenant_id = await _make_tenant(db_session)
    real_actor = _make_user(tenant_id)
    impersonated_id = uuid.uuid4()
    svc = _make_service(db_session, tenant_id)

    start_event = await svc.record_impersonation_start(real_actor, impersonated_id)
    end_event = await svc.record_impersonation_end(real_actor, impersonated_id)

    for event in (start_event, end_event):
        assert event.actor_user_id == real_actor.user_id, (
            f"Event {event.accion} attributed to wrong actor"
        )
        assert event.impersonated_user_id == impersonated_id
