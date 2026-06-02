"""
Tenancy scope contract (C-02).

This module contains ONLY the mechanism for injecting a tenant scope into a
repository — completely decoupled from auth.

How it works today (C-02):
    The caller (a test, a CLI script, or a future FastAPI dependency) provides
    the tenant_id directly when constructing a TenantScopedRepository.

How it works after C-03:
    A FastAPI dependency will derive the tenant_id from the verified JWT and
    pass it here.  The repository contract does not change.

Nothing in this module reads a JWT, a session cookie, or any request data.
That wiring is deliberately deferred to C-03.

Keeping this module as a dedicated slot (reserved by C-01) clarifies the
architectural boundary between "who I am" (auth → C-03) and "what I can see"
(tenancy scope → here).
"""
import uuid
from typing import Any

from app.repositories.base import TenantScopedRepository


def build_scoped_repository(
    model: Any,
    session: Any,
    tenant_id: uuid.UUID,
) -> TenantScopedRepository:
    """
    Build a TenantScopedRepository bound to *tenant_id*.

    Parameters
    ----------
    model:
        The SQLAlchemy model class to operate on.
    session:
        An AsyncSession from the current request context.
    tenant_id:
        The UUID of the tenant whose data will be scoped.
        In C-03, this will be extracted from the JWT; here it is passed
        directly by the caller.

    Returns
    -------
    TenantScopedRepository
        A repository whose reads and writes are bounded to *tenant_id*.
    """
    return TenantScopedRepository(model, session, tenant_id)
