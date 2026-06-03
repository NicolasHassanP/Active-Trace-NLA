"""
test_audit_model.py — Tasks 2.1, 2.3 RED/TRIANGULATE

Tests for AuditEvent SQLAlchemy model structure (D2).

Verifies:
  - All required columns present.
  - Structural immutability: NO updated_at, NO deleted_at.
  - before/after accept dict (JSONB) and are nullable.
  - Model table name is 'audit_event'.
"""
import inspect
import pytest

from app.models.audit import AuditEvent, AuditAction, AuditResultado


class TestAuditEventModelStructure:
    """Task 2.1 — RED: AuditEvent has required columns and NOT updated_at/deleted_at."""

    def test_has_id(self):
        assert hasattr(AuditEvent, "id")

    def test_has_tenant_id(self):
        assert hasattr(AuditEvent, "tenant_id")

    def test_has_actor_user_id(self):
        assert hasattr(AuditEvent, "actor_user_id")

    def test_has_impersonated_user_id(self):
        assert hasattr(AuditEvent, "impersonated_user_id")

    def test_has_accion(self):
        assert hasattr(AuditEvent, "accion")

    def test_has_modulo(self):
        assert hasattr(AuditEvent, "modulo")

    def test_has_entidad_tipo(self):
        assert hasattr(AuditEvent, "entidad_tipo")

    def test_has_entidad_id(self):
        assert hasattr(AuditEvent, "entidad_id")

    def test_has_resultado(self):
        assert hasattr(AuditEvent, "resultado")

    def test_has_registros_afectados(self):
        assert hasattr(AuditEvent, "registros_afectados")

    def test_has_before(self):
        assert hasattr(AuditEvent, "before")

    def test_has_after(self):
        assert hasattr(AuditEvent, "after")

    def test_has_created_at(self):
        assert hasattr(AuditEvent, "created_at")

    def test_no_updated_at(self):
        """D2: append-only — updated_at MUST NOT exist."""
        assert not hasattr(AuditEvent, "updated_at"), (
            "AuditEvent must not have updated_at (append-only, D2)"
        )

    def test_no_deleted_at(self):
        """D2: append-only — deleted_at MUST NOT exist."""
        assert not hasattr(AuditEvent, "deleted_at"), (
            "AuditEvent must not have deleted_at (append-only, D2)"
        )

    def test_table_name(self):
        assert AuditEvent.__tablename__ == "audit_event"


class TestAuditEventModelJsonbFields:
    """Task 2.3 — Triangulación: before/after are nullable dicts (JSONB)."""

    def test_before_nullable(self):
        """before accepts None (nullable)."""
        event = AuditEvent()
        event.before = None
        assert event.before is None

    def test_after_nullable(self):
        """after accepts None (nullable)."""
        event = AuditEvent()
        event.after = None
        assert event.after is None

    def test_before_accepts_dict(self):
        """before accepts a dict value (maps to JSONB)."""
        event = AuditEvent()
        event.before = {"field": "value", "nested": {"key": 1}}
        assert event.before == {"field": "value", "nested": {"key": 1}}

    def test_after_accepts_dict(self):
        """after accepts a dict value (maps to JSONB)."""
        event = AuditEvent()
        event.after = {"field": "new_value"}
        assert event.after == {"field": "new_value"}

    def test_impersonated_user_id_nullable(self):
        """impersonated_user_id is optional (present only under impersonation)."""
        event = AuditEvent()
        event.impersonated_user_id = None
        assert event.impersonated_user_id is None

    def test_entidad_id_nullable(self):
        """OQ-3 resolved: entidad_id is VARCHAR nullable."""
        event = AuditEvent()
        event.entidad_id = None
        assert event.entidad_id is None

    def test_entidad_id_accepts_string(self):
        """entidad_id can hold UUID string, business key, or composite key."""
        event = AuditEvent()
        event.entidad_id = "some-composite-key-or-uuid"
        assert event.entidad_id == "some-composite-key-or-uuid"


class TestAuditResultado:
    """Additional coverage for AuditResultado enum."""

    def test_has_ok(self):
        assert AuditResultado.ok == "ok"

    def test_has_fail(self):
        assert AuditResultado.fail == "fail"

    def test_has_partial(self):
        assert AuditResultado.partial == "partial"
