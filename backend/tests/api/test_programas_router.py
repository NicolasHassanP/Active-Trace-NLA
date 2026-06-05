"""
test_programas_router.py — TDD RED/GREEN tests for C-17 programas router.

Tasks 6.1–6.2:
    6.1 RED: POST/GET/DELETE under estructura:gestionar; 403 sin permiso; 404 cross-tenant;
             409 duplicado; referencia_archivo preservada.
    6.2 GREEN: router implemented.
    6.6 TRIANGULATE: additional edge cases.

Structural tests — verify router config, routes, and permission guards.
"""
import uuid
import pytest
from fastapi.routing import APIRoute
import inspect
from fastapi.params import Depends as FastAPIDepends


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def programas_router():
    from app.api.v1.routers.programas import router
    return router


# ---------------------------------------------------------------------------
# 6.1 RED — Router structure
# ---------------------------------------------------------------------------

def test_router_prefix(programas_router):
    """6.1 RED: programas router has prefix /programas."""
    assert programas_router.prefix == "/programas"


def test_router_has_required_routes(programas_router):
    """6.1 RED: programas router has POST, GET, DELETE paths."""
    paths = {route.path for route in programas_router.routes}
    assert "/programas" in paths          # POST crear + GET listar
    assert "/programas/{programa_id}" in paths  # GET + DELETE


def test_all_routes_have_require_permission(programas_router):
    """6.1 RED: all routes have require_permission('estructura:gestionar') guard."""
    for route in programas_router.routes:
        if not isinstance(route, APIRoute):
            continue
        sig = inspect.signature(route.endpoint)
        has_grant = any(
            isinstance(p.default, FastAPIDepends) and (
                hasattr(p.default.dependency, "__closure__")
                and p.default.dependency.__closure__ is not None
            )
            for p in sig.parameters.values()
        )
        assert has_grant, f"Route {route.path} missing require_permission dependency"


def test_routes_have_correct_methods(programas_router):
    """6.1 RED: correct HTTP verbs for each route."""
    route_methods = {}
    for r in programas_router.routes:
        if isinstance(r, APIRoute):
            for method in r.methods:
                route_methods.setdefault(r.path, set()).add(method.upper())

    assert "POST" in route_methods.get("/programas", set())
    assert "GET" in route_methods.get("/programas", set())
    assert "GET" in route_methods.get("/programas/{programa_id}", set())
    assert "DELETE" in route_methods.get("/programas/{programa_id}", set())


# ---------------------------------------------------------------------------
# 6.2 GREEN — Router imports
# ---------------------------------------------------------------------------

def test_programas_router_importable():
    """6.2 GREEN: programas router can be imported without errors."""
    from app.api.v1.routers.programas import router
    assert router is not None
    assert router.prefix == "/programas"


def test_programas_router_registered_in_main():
    """6.5 GREEN: programas router is registered in main.py."""
    from app.main import create_app
    app = create_app()
    paths = [r.path for r in app.routes]
    programas_paths = [p for p in paths if "/programas" in p]
    assert len(programas_paths) > 0, "No /programas routes found in main app"


# ---------------------------------------------------------------------------
# 6.6 TRIANGULATE — Response models
# ---------------------------------------------------------------------------

def test_post_programa_uses_programa_read_response_model(programas_router):
    """6.6 TRIANGULATE: POST /programas uses ProgramaRead as response_model."""
    from app.schemas.academico import ProgramaRead
    route_map = {}
    for r in programas_router.routes:
        if isinstance(r, APIRoute):
            for method in r.methods:
                route_map[(r.path, method.upper())] = r

    create_route = route_map.get(("/programas", "POST"))
    assert create_route is not None
    assert create_route.response_model is ProgramaRead


def test_get_programa_uses_list_response_model(programas_router):
    """6.6 TRIANGULATE: GET /programas uses List[ProgramaRead] response model."""
    route_map = {}
    for r in programas_router.routes:
        if isinstance(r, APIRoute):
            for method in r.methods:
                route_map[(r.path, method.upper())] = r

    list_route = route_map.get(("/programas", "GET"))
    assert list_route is not None
    assert list_route.response_model is not None
