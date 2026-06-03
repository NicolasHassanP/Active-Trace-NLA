"""
test_audit_schemas.py — Tasks 9.1, 9.2 RED/GREEN

Tests for AuditEventRead Pydantic v2 schema (D9).

Coverage:
  9.1 RED  — AuditEventRead validates well-formed data; rejects extra fields.
  9.2 GREEN — Schema implemented; these tests verify behavior.
"""
import uuid
from datetime import datetime, timezone
import pytest

from app.models.audit import AuditAction, AuditResultado
from app.schemas.audit import AuditEventRead


def _valid_payload(**overrides) -> dict:
    base = {
        "id": uuid.uuid4(),
        "tenant_id": uuid.uuid4(),
        "actor_user_id": uuid.uuid4(),
        "impersonated_user_id": None,
        "accion": AuditAction.AUDITORIA_CONSULTA,
        "modulo": "auditoria",
        "entidad_tipo": "AuditEvent",
        "entidad_id": None,
        "resultado": AuditResultado.ok,
        "registros_afectados": None,
        "ip": "192.168.1.1",
        "user_agent": "TestAgent/1.0",
        "before": None,
        "after": None,
        "created_at": datetime.now(tz=timezone.utc),
    }
    base.update(overrides)
    return base


class TestAuditEventReadValidation:
    """Task 9.1 RED: AuditEventRead validates a well-formed payload."""

    def test_valid_payload_parses(self):
        schema = AuditEventRead(**_valid_payload())
        assert schema.accion == AuditAction.AUDITORIA_CONSULTA

    def test_extra_field_rejected(self):
        """extra='forbid': undeclared fields raise ValidationError."""
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            AuditEventRead(**_valid_payload(), extra_undeclared_field="bad")

    def test_before_accepts_dict(self):
        schema = AuditEventRead(**_valid_payload(before={"key": "value"}))
        assert schema.before == {"key": "value"}

    def test_after_accepts_dict(self):
        schema = AuditEventRead(**_valid_payload(after={"field": 42}))
        assert schema.after == {"field": 42}

    def test_before_none_allowed(self):
        schema = AuditEventRead(**_valid_payload(before=None))
        assert schema.before is None

    def test_impersonated_user_id_none(self):
        schema = AuditEventRead(**_valid_payload(impersonated_user_id=None))
        assert schema.impersonated_user_id is None

    def test_impersonated_user_id_set(self):
        imp_id = uuid.uuid4()
        schema = AuditEventRead(**_valid_payload(impersonated_user_id=imp_id))
        assert schema.impersonated_user_id == imp_id

    def test_resultado_ok(self):
        schema = AuditEventRead(**_valid_payload(resultado=AuditResultado.ok))
        assert schema.resultado == AuditResultado.ok

    def test_resultado_fail(self):
        schema = AuditEventRead(**_valid_payload(resultado=AuditResultado.fail))
        assert schema.resultado == AuditResultado.fail

    def test_resultado_partial(self):
        schema = AuditEventRead(**_valid_payload(resultado=AuditResultado.partial))
        assert schema.resultado == AuditResultado.partial


class TestAuditEventReadConfig:
    """Verify schema config."""

    def test_extra_forbid_configured(self):
        """model_config extra='forbid' is set (D9)."""
        config = AuditEventRead.model_config
        assert config.get("extra") == "forbid"

    def test_from_attributes_enabled(self):
        """from_attributes=True allows ORM → schema conversion."""
        config = AuditEventRead.model_config
        assert config.get("from_attributes") is True
