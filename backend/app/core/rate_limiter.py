"""
Rate limiting for authentication endpoints.

C-03 D7: In-memory backend (slowapi) for MVP single-instance.
Interface is decoupled to allow Redis migration without changing the business logic.

Key: (client_ip, email_normalizado) — composite to balance between:
    - IP-only: penalizes shared NAT
    - Email-only: allows DoS targeting a specific user

Fail-closed: if the backend fails, deny (not allow) the request.
"""
from slowapi import Limiter
from slowapi.util import get_remote_address


def _settings():
    from app.core.config import Settings
    return Settings()


def get_rate_limit_key(ip: str, email: str) -> str:
    """
    Build the composite rate-limiting key from client IP and normalized email.

    Normalization: lowercase + strip (matches email_lookup_hash normalization).
    """
    normalized_email = email.strip().lower()
    return f"{ip}:{normalized_email}"


# Rate limit string read from config at import time (cached for the process lifetime).
# Override via LOGIN_RATE_LIMIT env var.
try:
    LOGIN_RATE_LIMIT_STRING = _settings().LOGIN_RATE_LIMIT
except Exception:
    LOGIN_RATE_LIMIT_STRING = "5/60seconds"


def _get_key_func(request):
    """Key function for slowapi: returns remote address (IP)."""
    return get_remote_address(request)


limiter = Limiter(key_func=_get_key_func, default_limits=[])
