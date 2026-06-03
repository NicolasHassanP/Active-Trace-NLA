"""
request_context.py — Request context extraction helper.

C-05: Design decision D7.
    Extracts IP and user-agent from a FastAPI Request.
    These values are treated as informative CONTEXT (not identity).

    IP resolution:
        By default: request.client.host.
        If TRUST_PROXY is set, the first value of X-Forwarded-For is used.
        X-Forwarded-For is only trusted when TRUST_PROXY=true to prevent
        spoofing in environments without a proxy.

    Rule (design.md D7):
        "IP and user-agent SÍ se leen del Request porque son contexto del
         cliente, no identidad."
"""
from dataclasses import dataclass
from typing import Optional

from fastapi import Request


# ---------------------------------------------------------------------------
# RequestContext — value object
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class RequestContext:
    """
    Immutable context extracted from an HTTP request.

    ip         — remote IP address (informative only, not identity).
    user_agent — client user-agent string (informative only, not identity).
    """
    ip: Optional[str]
    user_agent: Optional[str]


# ---------------------------------------------------------------------------
# extract_request_context — helper
# ---------------------------------------------------------------------------

def extract_request_context(
    request: Request,
    *,
    trust_proxy: bool = False,
) -> RequestContext:
    """
    Extract IP and user-agent from *request*.

    trust_proxy — if True, use the first value of X-Forwarded-For instead
                  of request.client.host.  Only enable when the application
                  is deployed behind a trusted reverse proxy.  Defaults to
                  False to prevent header spoofing.

    The extracted values are informative context, never used for access control
    or identity resolution.
    """
    user_agent: Optional[str] = request.headers.get("user-agent")

    ip: Optional[str] = None
    if trust_proxy:
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            # The first entry is the client IP (leftmost in the chain)
            ip = forwarded_for.split(",")[0].strip()
    if ip is None:
        ip = request.client.host if request.client else None

    return RequestContext(ip=ip, user_agent=user_agent)
