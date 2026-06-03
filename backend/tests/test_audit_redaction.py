"""
test_audit_redaction.py — Tasks 6.1, 6.2, 6.4 RED/TRIANGULATE

Tests for the redact_pii helper (D7, audit-event-log spec).

Coverage:
  6.1 RED  — before/after with cbu or password values are redacted.
  6.2 RED  — redaction is recursive in nested dicts.
  6.4      — sensitive keys constant is importable and extensible.
"""
import pytest

from app.core.audit_redaction import SENSITIVE_KEYS, redact_pii


class TestRedactPiiBasic:
    """Task 6.1 — RED: top-level sensitive keys are redacted."""

    def test_password_redacted(self):
        result = redact_pii({"password": "super_secret"})
        assert result["password"] == "[REDACTED]"

    def test_cbu_redacted(self):
        result = redact_pii({"cbu": "0000111122223333444455556666"})
        assert result["cbu"] == "[REDACTED]"

    def test_dni_redacted(self):
        result = redact_pii({"dni": "12345678"})
        assert result["dni"] == "[REDACTED]"

    def test_alias_cbu_redacted(self):
        result = redact_pii({"alias_cbu": "mi.alias.bancario"})
        assert result["alias_cbu"] == "[REDACTED]"

    def test_token_redacted(self):
        result = redact_pii({"token": "eyJhbGciOiJIUzI1NiJ9..."})
        assert result["token"] == "[REDACTED]"

    def test_secret_redacted(self):
        result = redact_pii({"secret": "my_app_secret"})
        assert result["secret"] == "[REDACTED]"

    def test_hash_redacted(self):
        result = redact_pii({"hash": "$argon2id$v=19..."})
        assert result["hash"] == "[REDACTED]"

    def test_non_sensitive_key_preserved(self):
        """Non-sensitive values pass through unchanged."""
        result = redact_pii({"email": "user@example.com", "nombre": "Ana"})
        assert result == {"email": "user@example.com", "nombre": "Ana"}

    def test_none_passthrough(self):
        """None is returned as-is (both before and after can be None)."""
        assert redact_pii(None) is None

    def test_original_dict_not_mutated(self):
        """redact_pii must not mutate the input dict."""
        original = {"password": "s3cr3t", "field": "value"}
        _ = redact_pii(original)
        assert original["password"] == "s3cr3t"  # unchanged


class TestRedactPiiRecursive:
    """Task 6.2 — RED: redaction is recursive into nested dicts."""

    def test_nested_password_redacted(self):
        result = redact_pii({"user": {"password": "abc123"}})
        assert result["user"]["password"] == "[REDACTED]"

    def test_nested_cbu_redacted(self):
        result = redact_pii({"account": {"cbu": "1234567890123456789012", "bank": "BNA"}})
        assert result["account"]["cbu"] == "[REDACTED]"
        assert result["account"]["bank"] == "BNA"  # preserved

    def test_deeply_nested_redacted(self):
        data = {"level1": {"level2": {"secret": "deepsecret"}}}
        result = redact_pii(data)
        assert result["level1"]["level2"]["secret"] == "[REDACTED]"

    def test_mixed_nested_and_flat(self):
        data = {
            "password": "root_secret",
            "data": {
                "cbu": "nested_cbu",
                "nombre": "visible",
            },
            "visible_field": "ok",
        }
        result = redact_pii(data)
        assert result["password"] == "[REDACTED]"
        assert result["data"]["cbu"] == "[REDACTED]"
        assert result["data"]["nombre"] == "visible"
        assert result["visible_field"] == "ok"


class TestRedactPiiCaseInsensitive:
    """Triangulation: keys are compared case-insensitively."""

    def test_password_uppercase_redacted(self):
        result = redact_pii({"PASSWORD": "value"})
        assert result["PASSWORD"] == "[REDACTED]"

    def test_password_mixed_case_redacted(self):
        result = redact_pii({"Password": "value"})
        assert result["Password"] == "[REDACTED]"


class TestSensitiveKeysConstant:
    """Task 6.4 — sensitive keys extracted to an importable constant."""

    def test_sensitive_keys_is_a_set(self):
        assert isinstance(SENSITIVE_KEYS, set)

    def test_sensitive_keys_contains_expected_values(self):
        expected = {"password", "cbu", "dni", "alias_cbu", "token", "secret", "hash"}
        assert expected.issubset(SENSITIVE_KEYS)

    def test_redact_pii_uses_sensitive_keys_default(self):
        """Calling redact_pii without explicit sensitive_keys uses the constant."""
        result = redact_pii({"password": "x", "cbu": "y", "safe": "z"})
        assert result["password"] == "[REDACTED]"
        assert result["cbu"] == "[REDACTED]"
        assert result["safe"] == "z"
