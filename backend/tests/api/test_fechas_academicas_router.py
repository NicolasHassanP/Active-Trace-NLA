"""
test_fechas_academicas_router.py — TDD RED/GREEN tests for C-17 fechas_academicas router.

Tasks 6.3–6.4:
    6.3 RED: CRUD, listado tabular filtrado, vista calendario, fragmento LMS,
             403/404/409/422, aislamiento tenant.
    6.4 GREEN: router implemented.
    6.6 TRIANGULATE: additional edge cases.

Structural tests — verify router config, routes, and permission guards.
"""
import pytest
from fastapi.routing import APIRoute
import inspect
from fastapi.params import Depends as FastAPIDepends


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def fechas_router():
    from app.api.v1.routers.fechas_academicas import router
    return router


# ---------------------------------------------------------------------------
# 6.3 RED — Router structure
# ---------------------------------------------------------------------------

def test_router_prefix(fechas_router):
    """6.3 RED: fechas_academicas router has prefix /fechas-academicas."""
    assert fechas_router.prefix == "/fechas-academicas"


def test_router_has_required_routes(fechas_router):
    """6.3 RED: router has all required paths."""
    paths = {route.path for route in fechas_router.routes}
    assert "/fechas-academicas" in paths                          # POST + GET tabular
    assert "/fechas-academicas/calendario" in paths               # GET calendar view
    assert "/fechas-academicas/{fecha_id}" in paths               # GET + PATCH + DELETE
    assert "/fechas-academicas/{fecha_id}/contenido-lms" in paths # GET LMS fragment


def test_all_routes_have_require_permission(fechas_router):
    """6.3 RED: all routes have require_permission dependency."""
    for route in fechas_router.routes:
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


def test_routes_have_correct_methods(fechas_router):
    """6.3 RED: correct HTTP verbs for each route."""
    route_methods = {}
    for r in fechas_router.routes:
        if isinstance(r, APIRoute):
            for method in r.methods:
                route_methods.setdefault(r.path, set()).add(method.upper())

    # Collection
    assert "POST" in route_methods.get("/fechas-academicas", set())
    assert "GET" in route_methods.get("/fechas-academicas", set())

    # Calendar view
    assert "GET" in route_methods.get("/fechas-academicas/calendario", set())

    # Single resource
    assert "GET" in route_methods.get("/fechas-academicas/{fecha_id}", set())
    assert "PATCH" in route_methods.get("/fechas-academicas/{fecha_id}", set())
    assert "DELETE" in route_methods.get("/fechas-academicas/{fecha_id}", set())

    # LMS fragment
    assert "GET" in route_methods.get("/fechas-academicas/{fecha_id}/contenido-lms", set())


# ---------------------------------------------------------------------------
# 6.4 GREEN — Router imports
# ---------------------------------------------------------------------------

def test_fechas_academicas_router_importable():
    """6.4 GREEN: fechas_academicas router can be imported without errors."""
    from app.api.v1.routers.fechas_academicas import router
    assert router is not None
    assert router.prefix == "/fechas-academicas"


def test_fechas_academicas_router_registered_in_main():
    """6.5 GREEN: fechas_academicas router is registered in main.py."""
    from app.main import create_app
    app = create_app()
    paths = [r.path for r in app.routes]
    fa_paths = [p for p in paths if "fechas-academicas" in p]
    assert len(fa_paths) > 0, "No /fechas-academicas routes found in main app"


# ---------------------------------------------------------------------------
# 6.6 TRIANGULATE — Response models
# ---------------------------------------------------------------------------

def test_post_fecha_uses_fecha_read_response_model(fechas_router):
    """6.6 TRIANGULATE: POST /fechas-academicas uses FechaAcademicaRead as response_model."""
    from app.schemas.academico import FechaAcademicaRead
    route_map = {}
    for r in fechas_router.routes:
        if isinstance(r, APIRoute):
            for method in r.methods:
                route_map[(r.path, method.upper())] = r

    create_route = route_map.get(("/fechas-academicas", "POST"))
    assert create_route is not None
    assert create_route.response_model is FechaAcademicaRead


def test_get_lms_contenido_route_exists(fechas_router):
    """6.6 TRIANGULATE: GET /{fecha_id}/contenido-lms route exists."""
    route_map = {}
    for r in fechas_router.routes:
        if isinstance(r, APIRoute):
            for method in r.methods:
                route_map[(r.path, method.upper())] = r

    lms_route = route_map.get(("/fechas-academicas/{fecha_id}/contenido-lms", "GET"))
    assert lms_route is not None


def test_calendario_route_exists_and_get(fechas_router):
    """6.6 TRIANGULATE: GET /calendario route exists."""
    route_map = {}
    for r in fechas_router.routes:
        if isinstance(r, APIRoute):
            for method in r.methods:
                route_map[(r.path, method.upper())] = r

    cal_route = route_map.get(("/fechas-academicas/calendario", "GET"))
    assert cal_route is not None
