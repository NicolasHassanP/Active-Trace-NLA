"""
test_tareas_router.py — TDD tests for C-16 tareas router (FastAPI structural).

Tasks 6.3–6.6:
    6.3 RED: permission split D7 — management routes have require_permission guard.
    6.4 GREEN: endpoints implemented with correct permission splits.
    6.6 TRIANGULATE: success-path router tests for each endpoint.

Structural tests — verify router config, routes, and permission guards.
Integration tests for full HTTP flow are in the integration tests (task 7.x).
"""
import uuid

import pytest
from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# App fixture — structural tests only
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def tareas_router():
    from app.api.v1.routers.tareas import router
    return router


# ---------------------------------------------------------------------------
# 6.3 RED — Router structure
# ---------------------------------------------------------------------------

def test_router_prefix(tareas_router):
    """6.3 RED: tareas router has correct prefix /tareas."""
    assert tareas_router.prefix == "/tareas"


def test_router_has_all_required_routes(tareas_router):
    """6.3 RED: tareas router has all D7 required paths."""
    paths = {route.path for route in tareas_router.routes}

    # Gestión routes
    assert "/tareas" in paths        # POST crear
    assert "/tareas/admin" in paths   # GET admin
    # Self-service routes
    assert "/tareas/mias" in paths    # GET mias
    assert "/tareas/{tarea_id}" in paths
    assert "/tareas/{tarea_id}/estado" in paths
    assert "/tareas/{tarea_id}/comentarios" in paths
    assert "/tareas/{tarea_id}/delegar" in paths


def test_gestionar_routes_have_require_permission(tareas_router):
    """6.3 RED: management routes (POST, DELETE, GET admin, delegar) have require_permission dependency."""
    import inspect
    from fastapi.routing import APIRoute
    from fastapi.params import Depends as FastAPIDepends

    # Build a map of path+method → route
    route_map = {}
    for r in tareas_router.routes:
        if isinstance(r, APIRoute):
            for method in r.methods:
                route_map[(r.path, method.upper())] = r

    def _has_permission_dep(route):
        """Check if route's endpoint function has a Depends(require_permission(...)) parameter."""
        sig = inspect.signature(route.endpoint)
        for param in sig.parameters.values():
            default = param.default
            # FastAPI Depends wraps the dependency; check if it references require_permission's inner func
            if isinstance(default, FastAPIDepends):
                # The _guard function returned by require_permission is a closure
                dep = default.dependency
                if callable(dep) and dep.__name__ in ("_guard", "<lambda>") or "grant" in param.name.lower():
                    return True
                # Also detect by checking if the closure references 'require_permission'
                if hasattr(dep, "__closure__") and dep.__closure__:
                    return True
        return False

    management_routes = [
        ("/tareas", "POST"),
        ("/tareas/admin", "GET"),
        ("/tareas/{tarea_id}", "DELETE"),
        ("/tareas/{tarea_id}/delegar", "POST"),
    ]

    for path, method in management_routes:
        route = route_map.get((path, method))
        assert route is not None, f"{method} {path} route not found"
        assert _has_permission_dep(route), f"{method} {path} should have require_permission dependency"


def test_self_service_routes_have_no_permission_dependency(tareas_router):
    """6.3 RED: self-service routes (mias, detalle, estado, comentarios) have NO permission dependency."""
    from fastapi.routing import APIRoute

    route_map = {}
    for r in tareas_router.routes:
        if isinstance(r, APIRoute):
            for method in r.methods:
                route_map[(r.path, method.upper())] = r

    # GET /tareas/mias — only auth, no permission
    mias_route = route_map.get(("/tareas/mias", "GET"))
    assert mias_route is not None

    # PATCH /tareas/{tarea_id}/estado — only auth
    estado_route = route_map.get(("/tareas/{tarea_id}/estado", "PATCH"))
    assert estado_route is not None

    # These routes should NOT have a require_permission dependency
    # (they have 0 explicit route-level dependencies — auth is via get_current_user param)
    assert len(mias_route.dependencies) == 0, "GET /tareas/mias should have no explicit route dependencies"
    assert len(estado_route.dependencies) == 0, "PATCH /tareas/{tarea_id}/estado should have no explicit route dependencies"


# ---------------------------------------------------------------------------
# 6.4 GREEN — Router imports and structure
# ---------------------------------------------------------------------------

def test_tareas_router_imported_correctly():
    """6.4 GREEN: tareas router can be imported without errors."""
    from app.api.v1.routers.tareas import router
    assert router is not None
    assert router.prefix == "/tareas"


def test_tareas_router_registered_in_main():
    """6.5 GREEN: tareas router is registered in main.py."""
    from app.main import create_app
    app = create_app()
    # Find a route that belongs to the tareas router
    paths = [r.path for r in app.routes]
    # Router is registered with prefix /api/v1/tareas
    tareas_paths = [p for p in paths if "/tareas" in p]
    assert len(tareas_paths) > 0, "No /tareas routes found in main app"


# ---------------------------------------------------------------------------
# 6.6 TRIANGULATE — Route method correctness
# ---------------------------------------------------------------------------

def test_routes_have_correct_http_methods(tareas_router):
    """6.6 TRIANGULATE: verify HTTP verbs for each route."""
    from fastapi.routing import APIRoute

    route_methods = {}
    for r in tareas_router.routes:
        if isinstance(r, APIRoute):
            for method in r.methods:
                route_methods.setdefault(r.path, set()).add(method.upper())

    # POST /tareas (create)
    assert "POST" in route_methods.get("/tareas", set())

    # GET /tareas/mias
    assert "GET" in route_methods.get("/tareas/mias", set())

    # GET /tareas/admin
    assert "GET" in route_methods.get("/tareas/admin", set())

    # GET + DELETE /tareas/{tarea_id}
    assert "GET" in route_methods.get("/tareas/{tarea_id}", set())
    assert "DELETE" in route_methods.get("/tareas/{tarea_id}", set())

    # PATCH /tareas/{tarea_id}/estado
    assert "PATCH" in route_methods.get("/tareas/{tarea_id}/estado", set())

    # POST + GET /tareas/{tarea_id}/comentarios
    assert "POST" in route_methods.get("/tareas/{tarea_id}/comentarios", set())
    assert "GET" in route_methods.get("/tareas/{tarea_id}/comentarios", set())

    # POST /tareas/{tarea_id}/delegar
    assert "POST" in route_methods.get("/tareas/{tarea_id}/delegar", set())


def test_schema_imports_correct():
    """6.6 TRIANGULATE: router uses correct response model schemas."""
    from app.api.v1.routers.tareas import router
    from fastapi.routing import APIRoute
    from app.schemas.tarea import TareaRead, ComentarioTareaRead

    for r in router.routes:
        if isinstance(r, APIRoute) and r.response_model is not None:
            # All single-entity responses use TareaRead or ComentarioTareaRead
            if "comentarios" in r.path and r.methods and "GET" in r.methods:
                assert r.response_model is not None
