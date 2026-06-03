"""
test_request_context.py — Tasks 8.1, 8.2 RED/GREEN

Tests for extract_request_context helper (D7).

Coverage:
  8.1 RED  — returns IP from request.client.host and user-agent from header;
             uses X-Forwarded-For only when trust_proxy=True.
  8.2 GREEN — helper implemented; these tests verify behavior.
"""
from unittest.mock import MagicMock
import pytest

from app.core.request_context import RequestContext, extract_request_context


def _make_request(host: str, user_agent: str = "Mozilla/5.0", xff: str = None):
    """Build a minimal mock FastAPI Request."""
    request = MagicMock()
    request.client = MagicMock()
    request.client.host = host

    headers = {"user-agent": user_agent}
    if xff is not None:
        headers["x-forwarded-for"] = xff
    request.headers = headers
    return request


class TestExtractRequestContextBasic:
    """Task 8.1 RED: basic extraction from request.client.host."""

    def test_returns_request_context(self):
        request = _make_request("192.168.1.1")
        ctx = extract_request_context(request)
        assert isinstance(ctx, RequestContext)

    def test_ip_from_client_host(self):
        request = _make_request("10.0.0.1")
        ctx = extract_request_context(request)
        assert ctx.ip == "10.0.0.1"

    def test_user_agent_from_header(self):
        request = _make_request("1.2.3.4", user_agent="MyTestAgent/1.0")
        ctx = extract_request_context(request)
        assert ctx.user_agent == "MyTestAgent/1.0"

    def test_missing_user_agent_is_none(self):
        request = MagicMock()
        request.client = MagicMock()
        request.client.host = "1.2.3.4"
        request.headers = {}
        ctx = extract_request_context(request)
        assert ctx.user_agent is None

    def test_no_client_ip_is_none(self):
        request = MagicMock()
        request.client = None
        request.headers = {"user-agent": "TestAgent"}
        ctx = extract_request_context(request)
        assert ctx.ip is None


class TestExtractRequestContextProxy:
    """Task 8.1 RED: X-Forwarded-For only trusted when trust_proxy=True."""

    def test_xff_ignored_by_default(self):
        """Default: X-Forwarded-For is ignored, uses client.host."""
        request = _make_request("10.0.0.1", xff="203.0.113.1, 10.0.0.2")
        ctx = extract_request_context(request)
        assert ctx.ip == "10.0.0.1"

    def test_xff_used_when_trust_proxy(self):
        """trust_proxy=True: first entry of X-Forwarded-For used as IP."""
        request = _make_request("10.0.0.1", xff="203.0.113.1, 10.0.0.2")
        ctx = extract_request_context(request, trust_proxy=True)
        assert ctx.ip == "203.0.113.1"

    def test_xff_single_value_trust_proxy(self):
        request = _make_request("10.0.0.1", xff="198.51.100.5")
        ctx = extract_request_context(request, trust_proxy=True)
        assert ctx.ip == "198.51.100.5"

    def test_xff_missing_falls_back_to_client_host(self):
        """trust_proxy=True but no XFF header → falls back to client.host."""
        request = _make_request("10.0.0.1")
        ctx = extract_request_context(request, trust_proxy=True)
        assert ctx.ip == "10.0.0.1"


class TestRequestContextImmutable:
    """RequestContext is a frozen dataclass (immutable)."""

    def test_cannot_set_ip(self):
        ctx = RequestContext(ip="1.2.3.4", user_agent="Test")
        with pytest.raises((AttributeError, TypeError)):
            ctx.ip = "5.6.7.8"  # type: ignore[misc]
