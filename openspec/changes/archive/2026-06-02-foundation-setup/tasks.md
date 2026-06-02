## 1. Bootstrap del proyecto y dependencias

- [x] 1.1 Crear el árbol `backend/` con `app/`, `tests/`, `alembic/` y los paquetes Clean Architecture (`api/v1/routers`, `core`, `models`, `schemas`, `repositories`, `services`, `integrations`, `workers`), cada uno con su `__init__.py`
- [x] 1.2 Crear `backend/pyproject.toml` (Python 3.13) declarando el stack: FastAPI, uvicorn, SQLAlchemy 2.0, Alembic, asyncpg, Pydantic v2, pydantic-settings, argon2-cffi, python-jose, opentelemetry-instrumentation-fastapi, y deps de test (pytest, pytest-asyncio, httpx)
- [x] 1.3 Crear `backend/.env.example` documentando `DATABASE_URL`, `SECRET_KEY`, `ENCRYPTION_KEY`, `ACCESS_TOKEN_EXPIRE_MINUTES` (default 15) y un `DATABASE_URL` de test, sin valores secretos reales

## 2. Configuración tipada (core/config.py)

- [x] 2.1 (RED) Escribir test que verifique que `Settings` se instancia con env válido y que falla en arranque si falta una variable requerida o un valor es inválido
- [x] 2.2 (GREEN) Implementar `core/config.py` con `Settings` (Pydantic v2 / pydantic-settings) cargando desde `.env`, con `ACCESS_TOKEN_EXPIRE_MINUTES` default 15 y validación de longitudes de `SECRET_KEY`/`ENCRYPTION_KEY`
- [x] 2.3 (TRIANGULATE) Agregar caso de variable ausente y caso de valor con tipo inválido; verificar que la validación falla con error claro

## 3. Conexión a base de datos async (core/database.py)

- [x] 3.1 Implementar `core/database.py`: `create_async_engine` (asyncpg), `async_sessionmaker(expire_on_commit=False)` y la `Base` declarativa
- [x] 3.2 Implementar la dependency `get_db` en `core/dependencies.py` como async-generator que abre sesión, hace `yield` y cierra en `finally`
- [x] 3.3 (RED) Escribir `tests/test_database.py` contra la DB de test: una sesión async ejecuta `SELECT 1` y obtiene resultado
- [x] 3.4 (GREEN) Ajustar engine/fixtures hasta que el smoke de conexión pase; agregar fixture de sesión de DB de test en `conftest.py`
- [x] 3.5 (TRIANGULATE) Verificar que la sesión se cierra ante excepción dentro del scope de `get_db` (no fuga de conexión al pool)

## 4. Observabilidad base (core/logging.py, core/observability.py)

- [x] 4.1 Implementar `core/logging.py`: logger estructurado JSON (una línea por evento, campos timestamp/level/message), aplicado al logger raíz; nunca secretos/PII en claro
- [x] 4.2 Implementar `core/observability.py`: init de OpenTelemetry para FastAPI, activable por entorno y sin exporter obligatorio (la app arranca aunque no haya backend OTLP)

## 5. Esqueleto FastAPI y health-check

- [x] 5.1 (RED) Escribir `tests/test_health.py`: `GET /health` responde `200` con JSON que incluye `status` y campo de readiness de DB (`database: up`)
- [x] 5.2 (GREEN) Implementar `api/v1/routers/health.py` con `GET /health` que ejecuta `SELECT 1` vía `get_db` y arma la respuesta `{status, database}`
- [x] 5.3 (TRIANGULATE) Agregar caso DB down: el endpoint reporta `database: down` y responde sin caerse el proceso
- [x] 5.4 (RED) Escribir `tests/test_app_startup.py`: la app FastAPI se instancia/arranca (lifespan) sin error
- [x] 5.5 (GREEN) Implementar `app/main.py`: bootstrap FastAPI con lifespan (engine), middleware, init de logging + OTel y registro del router de health; confirmar arranque verde

## 6. Slots reservados de core (sin lógica)

- [x] 6.1 Crear `core/security.py`, `core/permissions.py`, `core/tenancy.py`, `core/exceptions.py` como placeholders con docstring "RESERVADO para C-0X" (sin lógica de auth/RBAC/tenancy)
- [x] 6.2 Dejar en `core/dependencies.py` solo `get_db`; documentar como reservados los slots `get_current_user`, `get_tenant`, `require_permission` (a llenar en C-03/C-04)

## 7. Worker y Alembic (placeholders)

- [x] 7.1 Crear `workers/main.py`: entrypoint mínimo del worker (loop no-op / placeholder); la tecnología real de la cola queda para ADR-003
- [x] 7.2 Inicializar Alembic en `backend/alembic/` con `env.py` configurado para engine async, sin migraciones de dominio (la migración 001 es de C-02)

## 8. Contenedores

- [x] 8.1 Crear `backend/Dockerfile` multi-stage (builder con deps + runtime slim Python 3.13) siguiendo convención Easypanel; runtime arranca uvicorn sin toolchain de build
- [x] 8.2 Crear `docker-compose.yml` en la raíz con servicios `api` (build del Dockerfile, depende de `postgres`, lee `.env`), `postgres` (volumen persistente + healthcheck) y `worker` (mismo build, `command` → `workers/main.py`)

## 9. Verificación final

- [x] 9.1 Ejecutar la suite completa de tests (`pytest`) y confirmar verde: health, arranque y conexión a DB de test
- [ ] 9.2 Levantar el stack con docker-compose y verificar `GET /health` respondiendo `200` con `database: up`
- [x] 9.3 Confirmar que ningún archivo `.py` del scaffold supera 500 LOC y que el árbol coincide con `docs/ARQUITECTURA.md §4`
