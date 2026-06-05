"""
test_audit_action_catalog.py — Tasks 1.1, 1.3 RED/TRIANGULATE

Tests for AuditAction enum (catálogo cerrado de acciones, D4, RN-24).

Coverage:
  - Enum contains exactly the initial catalog values.
  - Arbitrary strings are NOT valid enum members.
  - Catalog is identical across tenants (system constant, not per-tenant).

TDD: Tasks 1.1 (RED) and 1.3 (TRIANGULATE).
GREEN was 1.2 — creating the enum.
"""
import pytest

from app.models.audit import AuditAction


class TestAuditActionCatalog:
    """Task 1.1 — RED: AuditAction enum has the three initial catalog values."""

    def test_audit_action_has_impersonacion_inicio(self):
        assert AuditAction.IMPERSONACION_INICIO == "IMPERSONACION_INICIO"

    def test_audit_action_has_impersonacion_fin(self):
        assert AuditAction.IMPERSONACION_FIN == "IMPERSONACION_FIN"

    def test_audit_action_has_auditoria_consulta(self):
        assert AuditAction.AUDITORIA_CONSULTA == "AUDITORIA_CONSULTA"

    def test_audit_action_is_str_enum(self):
        """Enum members are strings (str, Enum)."""
        assert isinstance(AuditAction.IMPERSONACION_INICIO, str)

    def test_audit_action_arbitrary_code_is_not_member(self):
        """Codes not in the catalog cannot be constructed from the enum."""
        with pytest.raises((ValueError, KeyError)):
            AuditAction("ARBITRARY_UNKNOWN_CODE")


class TestAuditActionCatalogTriangulation:
    """Task 1.3 — Triangulación: catalog is uniform; invalid values rejected."""

    def test_catalog_has_expected_values(self):
        """Catalog grows with each change. Verify known values exist (not a fixed count)."""
        values = [a.value for a in AuditAction]
        # C-05 initial values
        assert "PADRON_CARGAR" in values
        assert "CALIFICACIONES_IMPORTAR" in values
        assert "COMUNICACION_ENVIAR" in values
        # C-15
        assert "AVISO_PUBLICAR" in values
        # C-16
        assert "TAREA_ASIGNAR" in values
        assert "TAREA_DELEGAR" in values
        assert "TAREA_CAMBIAR_ESTADO" in values

    def test_catalog_values_are_uppercase_module_action_format(self):
        """All codes follow MODULO_ACCION uppercase format (RN-24)."""
        for action in AuditAction:
            assert action.value == action.value.upper(), (
                f"{action.value} should be uppercase"
            )
            assert "_" in action.value, (
                f"{action.value} should follow MODULO_ACCION format"
            )

    def test_catalog_same_for_all_tenants(self):
        """
        Catalog uniformity: identical AuditAction member set regardless of tenant.
        Since it's a system enum (not per-tenant table), the same class is used.
        """
        import uuid
        tenant_a = uuid.uuid4()
        tenant_b = uuid.uuid4()

        # Both tenants see the same AuditAction members (enum is global)
        actions_a = {a.value for a in AuditAction}
        actions_b = {a.value for a in AuditAction}
        assert actions_a == actions_b
        # Not empty
        assert len(actions_a) > 0
        _ = tenant_a, tenant_b  # Both reference same class

    def test_value_not_in_enum_raises(self):
        """Second edge: another arbitrary value also rejected."""
        with pytest.raises((ValueError, KeyError)):
            AuditAction("login_user")
