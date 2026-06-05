"""
test_auditoria_panel_service.py — Tasks 3.1–3.4 (C-19)

Tests for AuditoriaPanelService: scope translation, delegation to repository,
and limite validation (D4).

Coverage:
    3.1 RED+GREEN — scope propio → actor_filter=user_id; scope global → None.
    3.2 RED+GREEN — each service method delegates to repository with correct filters.
    3.3 RED+GREEN — limite validation: omitted→200, valid→passed, >max→ValueError.
    3.4 REFACTOR  — service has no SQL, no direct DB access (structural test).

Uses unittest.mock for repository (pure unit tests — no DB needed).
"""
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from app.core.dependencies import CurrentUser
from app.models.rbac import PermisoScope
from app.services.authorization_service import PermissionGrant


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _grant(scope: PermisoScope) -> PermissionGrant:
    return PermissionGrant(codigo="auditoria:ver", scope=scope)


def _user(user_id: uuid.UUID | None = None) -> CurrentUser:
    return CurrentUser(
        user_id=user_id or uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        roles=["ADMIN"],
    )


def _mock_repo():
    repo = MagicMock()
    repo.acciones_por_dia = AsyncMock(return_value=[])
    repo.interacciones_por_docente = AsyncMock(return_value=[])
    repo.interacciones_por_docente_materia = AsyncMock(return_value=[])
    repo.comunicaciones_por_docente = AsyncMock(return_value=[])
    repo.ultimas_acciones = AsyncMock(return_value=[])
    return repo


# ---------------------------------------------------------------------------
# Task 3.1 — scope translation
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_service_scope_propio_sets_actor_filter():
    """scope=propio → actor_filter = current_user.user_id."""
    from app.services.auditoria_panel_service import AuditoriaPanelService

    user = _user()
    grant = _grant(PermisoScope.propio)
    repo = _mock_repo()

    svc = AuditoriaPanelService(repository=repo, settings=MagicMock(AUDIT_PANEL_LOG_MAX=200))
    await svc.acciones_por_dia(current_user=user, grant=grant)

    # actor_user_id should be user.user_id (scope propio)
    repo.acciones_por_dia.assert_called_once()
    call_kwargs = repo.acciones_por_dia.call_args.kwargs
    assert call_kwargs.get("actor_user_id") == user.user_id


@pytest.mark.asyncio
async def test_service_scope_global_no_actor_filter():
    """scope=global → actor_filter = None (no row-level filter)."""
    from app.services.auditoria_panel_service import AuditoriaPanelService

    user = _user()
    grant = _grant(PermisoScope.global_)
    repo = _mock_repo()

    svc = AuditoriaPanelService(repository=repo, settings=MagicMock(AUDIT_PANEL_LOG_MAX=200))
    await svc.acciones_por_dia(current_user=user, grant=grant)

    call_kwargs = repo.acciones_por_dia.call_args.kwargs
    assert call_kwargs.get("actor_user_id") is None


# ---------------------------------------------------------------------------
# Task 3.2 — delegation methods
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_service_delegates_interacciones_docente_with_scope():
    """interacciones_docente calls repo with correct actor_filter."""
    from app.services.auditoria_panel_service import AuditoriaPanelService

    user = _user()
    grant = _grant(PermisoScope.propio)
    repo = _mock_repo()
    svc = AuditoriaPanelService(repository=repo, settings=MagicMock(AUDIT_PANEL_LOG_MAX=200))

    await svc.interacciones_docente(current_user=user, grant=grant)
    call_kwargs = repo.interacciones_por_docente.call_args.kwargs
    assert call_kwargs.get("actor_user_id") == user.user_id


@pytest.mark.asyncio
async def test_service_delegates_interacciones_docente_materia():
    """interacciones_docente_materia delegates to repository."""
    from app.services.auditoria_panel_service import AuditoriaPanelService

    user = _user()
    grant = _grant(PermisoScope.global_)
    repo = _mock_repo()
    svc = AuditoriaPanelService(repository=repo, settings=MagicMock(AUDIT_PANEL_LOG_MAX=200))

    materia_id = str(uuid.uuid4())
    await svc.interacciones_docente_materia(current_user=user, grant=grant, materia_id=materia_id)
    call_kwargs = repo.interacciones_por_docente_materia.call_args.kwargs
    assert call_kwargs.get("actor_user_id") is None
    assert call_kwargs.get("materia_id") == materia_id


@pytest.mark.asyncio
async def test_service_delegates_comunicaciones_por_docente():
    """comunicaciones_por_docente delegates with scope propio."""
    from app.services.auditoria_panel_service import AuditoriaPanelService

    user = _user()
    grant = _grant(PermisoScope.propio)
    repo = _mock_repo()
    svc = AuditoriaPanelService(repository=repo, settings=MagicMock(AUDIT_PANEL_LOG_MAX=200))

    await svc.comunicaciones_por_docente(current_user=user, grant=grant)
    call_kwargs = repo.comunicaciones_por_docente.call_args.kwargs
    assert call_kwargs.get("actor_user_id") == user.user_id


# ---------------------------------------------------------------------------
# Task 3.3 — limite validation (D4)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_service_limite_default_200():
    """When limite is None, service uses AUDIT_PANEL_LOG_MAX as default."""
    from app.services.auditoria_panel_service import AuditoriaPanelService

    user = _user()
    grant = _grant(PermisoScope.global_)
    repo = _mock_repo()
    svc = AuditoriaPanelService(repository=repo, settings=MagicMock(AUDIT_PANEL_LOG_MAX=200))

    await svc.ultimas_acciones(current_user=user, grant=grant, limite=None)
    call_kwargs = repo.ultimas_acciones.call_args.kwargs
    assert call_kwargs.get("limite") == 200


@pytest.mark.asyncio
async def test_service_limite_explicit_valid():
    """A valid explicit limite is passed through to the repository."""
    from app.services.auditoria_panel_service import AuditoriaPanelService

    user = _user()
    grant = _grant(PermisoScope.global_)
    repo = _mock_repo()
    svc = AuditoriaPanelService(repository=repo, settings=MagicMock(AUDIT_PANEL_LOG_MAX=200))

    await svc.ultimas_acciones(current_user=user, grant=grant, limite=50)
    call_kwargs = repo.ultimas_acciones.call_args.kwargs
    assert call_kwargs.get("limite") == 50


@pytest.mark.asyncio
async def test_service_limite_exceeds_max_raises():
    """limite > AUDIT_PANEL_LOG_MAX raises ValueError (D4)."""
    from app.services.auditoria_panel_service import AuditoriaPanelService

    user = _user()
    grant = _grant(PermisoScope.global_)
    repo = _mock_repo()
    svc = AuditoriaPanelService(repository=repo, settings=MagicMock(AUDIT_PANEL_LOG_MAX=200))

    with pytest.raises(ValueError, match="limite"):
        await svc.ultimas_acciones(current_user=user, grant=grant, limite=201)


@pytest.mark.asyncio
async def test_service_limite_zero_raises():
    """limite < 1 raises ValueError (D4)."""
    from app.services.auditoria_panel_service import AuditoriaPanelService

    user = _user()
    grant = _grant(PermisoScope.global_)
    repo = _mock_repo()
    svc = AuditoriaPanelService(repository=repo, settings=MagicMock(AUDIT_PANEL_LOG_MAX=200))

    with pytest.raises(ValueError, match="limite"):
        await svc.ultimas_acciones(current_user=user, grant=grant, limite=0)


# ---------------------------------------------------------------------------
# Task 3.4 — structural: service has no SQL, no direct DB
# ---------------------------------------------------------------------------

def test_service_has_no_sql_imports():
    """Service module must not import SQLAlchemy (no SQL in service layer)."""
    import app.services.auditoria_panel_service as svc_module
    import inspect
    source = inspect.getsource(svc_module)
    assert "from sqlalchemy" not in source, (
        "Service must not import SQLAlchemy — queries belong in repositories"
    )
    # The service should NOT import or declare AsyncSession directly
    # (docstrings may mention it for clarity, but import lines must not exist)
    lines = source.splitlines()
    import_lines = [l for l in lines if l.startswith("from ") or l.startswith("import ")]
    assert not any("AsyncSession" in l for l in import_lines), (
        "Service must not import AsyncSession — that belongs in repositories"
    )
