"""
Tests for the rate limiting module (in-memory slowapi, fail-closed).
TDD: RED → GREEN → TRIANGULATE → REFACTOR
Tasks 10.1-10.2
"""
import pytest


# ==============================================================================
# 10.1 Rate limiter: basic interface
# ==============================================================================

def test_rate_limiter_module_importable():
    """app.core.rate_limiter is importable."""
    from app.core import rate_limiter
    assert rate_limiter is not None


def test_rate_limiter_exposes_limiter():
    """rate_limiter module exposes a `limiter` object."""
    from app.core.rate_limiter import limiter
    assert limiter is not None


def test_rate_limiter_exposes_login_limit_string():
    """Rate limiting uses the LOGIN_RATE_LIMIT config string."""
    from app.core.rate_limiter import LOGIN_RATE_LIMIT_STRING
    assert "/" in LOGIN_RATE_LIMIT_STRING


# ==============================================================================
# 10.2 Fail-closed: get_login_rate_limit_key
# ==============================================================================

def test_rate_limit_key_combines_ip_and_email():
    """Rate limit key is composed of (ip, email) — composite to avoid DoS."""
    from app.core.rate_limiter import get_rate_limit_key
    key = get_rate_limit_key("192.168.1.1", "user@example.com")
    assert "192.168.1.1" in key
    assert "user@example.com" in key or "user" in key.lower()


def test_rate_limit_key_normalizes_email():
    """Rate limit key normalizes email (case-insensitive)."""
    from app.core.rate_limiter import get_rate_limit_key
    key1 = get_rate_limit_key("1.2.3.4", "User@Example.COM")
    key2 = get_rate_limit_key("1.2.3.4", "user@example.com")
    assert key1 == key2
