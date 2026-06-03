"""
test_audit_repository.py — Tasks 5.1–5.4

Tests for AuditRepository (D6, append-only, tenant-scoped).

Coverage:
  5.1 RED  — record() persists event with tenant_id forced to scope.
             Repository does NOT expose update() or delete().
  5.2 GREEN — AuditRepository structure (verified via 5.1 tests).
  5.3 RED  — tenant isolation: list() from tenant A never returns events of B.
  5.4 TRIANG — list(actor_user_id=...) filter and created_at DESC ordering.

Uses real DB (no mocks). Requires conftest session/db fixtures.
"""
import uuid
import pytest
import pytest_asyncio

from app.models.audit import AuditAction, AuditEvent, AuditResultado
from app.models.tenant import Tenant, TenantEstado
from app.repositories.audit_repository import AuditRepository


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _make_tenant(db_session) -> uuid.UUID:
    """Create a real Tenant row and return its id (satisfies audit_event FK)."""
    tid = uuid.uuid4()
    tenant = Tenant(id=tid, nombre=f"Audit Test Tenant {tid.hex[:8]}", estado=TenantEstado.ACTIVO)
    db_session.add(tenant)
    await db_session.commit()
    return tid


def _make_event(
    tenant_id: uuid.UUID,
    actor_id: uuid.UUID,
    accion: AuditAction = AuditAction.AUDITORIA_CONSULTA,
) -> AuditEvent:
    return AuditEvent(
        tenant_id=tenant_id,
        actor_user_id=actor_id,
        accion=accion,
        modulo="auditoria",
        entidad_tipo="AuditEvent",
        resultado=AuditResultado.ok,
    )


# ---------------------------------------------------------------------------
# Task 5.1 — record() persists with forced tenant_id; no update/delete methods
# ---------------------------------------------------------------------------

@pytest.mark.asyncio(loop_scope="session")
async def test_audit_repository_record_persists_event(db_session, create_tables):
    """record() persists an AuditEvent and returns it with a DB id."""
    tenant_id = await _make_tenant(db_session)
    actor_id = uuid.uuid4()
    repo = AuditRepository(session=db_session, tenant_id=tenant_id)

    event = AuditEvent(
        tenant_id=tenant_id,
        actor_user_id=actor_id,
        accion=AuditAction.AUDITORIA_CONSULTA,
        modulo="auditoria",
        entidad_tipo="AuditEvent",
        resultado=AuditResultado.ok,
    )
    persisted = await repo.record(event)

    assert persisted.id is not None
    assert persisted.created_at is not None
    assert persisted.tenant_id == tenant_id
    assert persisted.actor_user_id == actor_id


@pytest.mark.asyncio(loop_scope="session")
async def test_audit_repository_record_overrides_tenant_id(db_session, create_tables):
    """record() overrides tenant_id with the scope tenant, ignoring whatever was set."""
    scope_tenant = await _make_tenant(db_session)
    different_tenant = await _make_tenant(db_session)
    actor_id = uuid.uuid4()
    repo = AuditRepository(session=db_session, tenant_id=scope_tenant)

    event = AuditEvent(
        tenant_id=different_tenant,  # caller passed different tenant
        actor_user_id=actor_id,
        accion=AuditAction.AUDITORIA_CONSULTA,
        modulo="auditoria",
        entidad_tipo="AuditEvent",
        resultado=AuditResultado.ok,
    )
    persisted = await repo.record(event)

    # Must be overridden to scope_tenant, not different_tenant
    assert persisted.tenant_id == scope_tenant


def test_audit_repository_has_no_update_method():
    """Task 5.1: AuditRepository does NOT expose an update() method."""
    assert not hasattr(AuditRepository, "update"), (
        "AuditRepository must not expose update() — append-only"
    )


def test_audit_repository_has_no_delete_method():
    """Task 5.1: AuditRepository does NOT expose a delete() method."""
    assert not hasattr(AuditRepository, "delete"), (
        "AuditRepository must not expose delete() — append-only"
    )


# ---------------------------------------------------------------------------
# Task 5.3 — Tenant isolation: list() never returns events from other tenants
# ---------------------------------------------------------------------------

@pytest.mark.asyncio(loop_scope="session")
async def test_audit_repository_tenant_isolation(db_session, create_tables):
    """list() for tenant A never returns events that belong to tenant B."""
    tenant_a = await _make_tenant(db_session)
    tenant_b = await _make_tenant(db_session)
    actor_a = uuid.uuid4()
    actor_b = uuid.uuid4()

    repo_a = AuditRepository(session=db_session, tenant_id=tenant_a)
    repo_b = AuditRepository(session=db_session, tenant_id=tenant_b)

    # Insert one event per tenant
    event_a = _make_event(tenant_a, actor_a)
    event_b = _make_event(tenant_b, actor_b)
    await repo_a.record(event_a)
    await repo_b.record(event_b)

    # Tenant A's list must not include tenant B's event
    results_a = await repo_a.list()
    tenant_ids_a = {e.tenant_id for e in results_a}
    assert tenant_b not in tenant_ids_a, (
        "Tenant isolation broken: tenant A's list returned a tenant B event"
    )

    # Tenant B's list must not include tenant A's event
    results_b = await repo_b.list()
    tenant_ids_b = {e.tenant_id for e in results_b}
    assert tenant_a not in tenant_ids_b, (
        "Tenant isolation broken: tenant B's list returned a tenant A event"
    )


# ---------------------------------------------------------------------------
# Task 5.4 — Triangulation: actor_user_id filter and created_at DESC order
# ---------------------------------------------------------------------------

@pytest.mark.asyncio(loop_scope="session")
async def test_audit_repository_list_filters_by_actor(db_session, create_tables):
    """list(actor_user_id=...) returns only events for that actor."""
    tenant_id = await _make_tenant(db_session)
    actor_mine = uuid.uuid4()
    actor_other = uuid.uuid4()

    repo = AuditRepository(session=db_session, tenant_id=tenant_id)

    # Insert events for two different actors
    for _ in range(2):
        await repo.record(_make_event(tenant_id, actor_mine))
    await repo.record(_make_event(tenant_id, actor_other))

    filtered = await repo.list(actor_user_id=actor_mine)
    assert len(filtered) >= 2
    assert all(e.actor_user_id == actor_mine for e in filtered)
    # Other actor's event must not appear
    assert not any(e.actor_user_id == actor_other for e in filtered)


@pytest.mark.asyncio(loop_scope="session")
async def test_audit_repository_list_ordered_desc(db_session, create_tables):
    """list() returns events ordered by created_at DESC (most recent first)."""
    tenant_id = await _make_tenant(db_session)
    actor_id = uuid.uuid4()

    repo = AuditRepository(session=db_session, tenant_id=tenant_id)

    # Insert two events; DB assigns created_at via DEFAULT now()
    ev1 = await repo.record(_make_event(tenant_id, actor_id))
    ev2 = await repo.record(_make_event(tenant_id, actor_id))

    results = await repo.list(actor_user_id=actor_id)
    # Most recently inserted should come first
    assert results[0].created_at >= results[-1].created_at


@pytest.mark.asyncio(loop_scope="session")
async def test_audit_repository_get_by_id_scoped(db_session, create_tables):
    """get_by_id() returns None for an event that belongs to a different tenant."""
    tenant_a = await _make_tenant(db_session)
    tenant_b = await _make_tenant(db_session)
    actor_id = uuid.uuid4()

    repo_a = AuditRepository(session=db_session, tenant_id=tenant_a)
    repo_b = AuditRepository(session=db_session, tenant_id=tenant_b)

    event = await repo_a.record(_make_event(tenant_a, actor_id))

    # Trying to get it through tenant B's repo must return None
    result = await repo_b.get_by_id(event.id)
    assert result is None
