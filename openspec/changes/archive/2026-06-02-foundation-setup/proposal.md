## Why

activia-trace todavía no tiene código: existe el contrato de arquitectura (Clean Architecture por capas, multi-tenant row-level, FastAPI async + SQLAlchemy 2.0) pero no hay un esqueleto ejecutable sobre el cual construir. Sin un cimiento que materialice la estructura de directorios, el bootstrap de la app, la conexión a base de datos y el tooling de contenedores/observabilidad, ningún change posterior (C-02 modelos+tenancy, C-03 auth, C-04 RBAC) puede arrancar. Este change crea ese piso, sin lógica de negocio.

## What Changes

- Estructura de directorios **Clean Architecture** del backend bajo `backend/app/`: `api/v1/routers/`, `services/`, `repositories/`, `models/`, `schemas/`, `core/`, `integrations/`, `workers/`. Convención de límite ≤500 LOC por archivo.
- **Esqueleto FastAPI** ejecutable: `app/main.py` con bootstrap de la aplicación y un endpoint de salud `GET /health` que reporta estado de la app y de la base de datos.
- **Configuración tipada** con Pydantic v2 (`pydantic-settings`): `core/config.py` expone un objeto `Settings` cargado desde `.env`, con las variables de entorno base del proyecto.
- **Conexión SQLAlchemy 2.0 async** (`asyncpg`): engine async, factory de sesiones y una **sesión por request** inyectada vía dependency injection de FastAPI.
- **Observabilidad base**: logging estructurado en JSON e instrumentación OpenTelemetry inicial para la app FastAPI.
- **Tooling de contenedores**: `Dockerfile` multi-stage (build / runtime) siguiendo convención Easypanel y `docker-compose.yml` con los servicios `api`, `postgres` y `worker`.
- **`pyproject.toml`** con el set de dependencias del backend: FastAPI, SQLAlchemy 2.0, Alembic, asyncpg, Pydantic v2, pydantic-settings, argon2-cffi, python-jose, pytest, pytest-asyncio, httpx (+ instrumentación OpenTelemetry).
- **Tests de cimiento** (smoke): respuesta de `GET /health`, arranque correcto de la app y conexión a una base de datos de test.
- Se **reservan** (sin implementar) los slots `core/security.py`, `core/permissions.py`, `core/tenancy.py`, `core/dependencies.py`, `core/exceptions.py` para que C-02/C-03/C-04 los completen. C-01 NO escribe su lógica.

No hay cambios BREAKING: es el primer change del proyecto y no existe nada que romper.

## Capabilities

### New Capabilities

- `app-scaffold`: estructura de directorios Clean Architecture del backend y los slots reservados de `core/`; convención de capas (Routers → Services → Repositories → Models) y límite de LOC por archivo.
- `health-check`: endpoint `GET /health` que reporta liveness de la aplicación y readiness de la conexión a base de datos.
- `app-configuration`: carga tipada de configuración con Pydantic v2 desde `.env` (objeto `Settings`), incluyendo el contrato de variables de entorno base del proyecto.
- `database-connection`: engine y sesión async de SQLAlchemy 2.0 con `asyncpg`, y el patrón de sesión-por-request vía dependency injection.
- `observability-base`: logging estructurado JSON e instrumentación OpenTelemetry inicial de la app.
- `container-tooling`: `Dockerfile` multi-stage (convención Easypanel) y `docker-compose.yml` con servicios `api`, `postgres` y `worker`.

### Modified Capabilities

<!-- Ninguna: es el primer change del proyecto, no hay specs previos en openspec/specs/. -->

## Impact

- **Nuevo código** (esqueleto, sin lógica de negocio): árbol `backend/app/**`, `backend/tests/**`, `backend/pyproject.toml`, `backend/Dockerfile`, `docker-compose.yml`, `.env.example`.
- **Dependencias nuevas**: todo el stack backend declarado en `pyproject.toml` (FastAPI, SQLAlchemy 2.0, Alembic, asyncpg, Pydantic v2, pydantic-settings, argon2-cffi, python-jose, pytest, pytest-asyncio, httpx, OpenTelemetry).
- **Infraestructura**: define el modelo de ejecución en contenedores (api/postgres/worker) que usarán todos los changes siguientes y el deploy en Easypanel.
- **Habilita** a C-02 (`core-models-y-tenancy`) y a toda la cadena de Fase 1: sin este cimiento ningún otro change puede correr.
- **Governance**: BAJO — solo scaffold, sin auth, billing, seguridad ni audit (esos slots quedan reservados pero vacíos).
