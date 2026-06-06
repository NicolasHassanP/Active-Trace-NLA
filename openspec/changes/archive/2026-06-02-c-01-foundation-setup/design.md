## Context

activia-trace es una plataforma de gestión académica y trazabilidad multi-tenant que se integra con Moodle. El contrato de arquitectura ya está definido (`docs/ARQUITECTURA.md`, `knowledge-base/08_arquitectura_propuesta.md`): Clean Architecture por capas, multi-tenancy row-level desde el día 0 (ADR-002), auth propio JWT + Argon2id (ADR-001), FastAPI async + SQLAlchemy 2.0 async sobre PostgreSQL, deploy en Easypanel con observabilidad JSON + OpenTelemetry.

Hoy no existe código. Este change (C-01, governance **BAJO**, sin dependencias) crea el esqueleto ejecutable sobre el cual se construyen todos los changes siguientes. Es el cimiento: define el layout de directorios, el bootstrap de la app, la conexión a base de datos y el tooling de contenedores. **No implementa lógica de negocio, ni auth, ni tenancy, ni RBAC** — esos llegan en C-02/C-03/C-04. La restricción dura es dejar los slots correctos reservados para que esos changes encajen sin reorganizar el cimiento.

## Goals / Non-Goals

**Goals:**

- Materializar el árbol Clean Architecture exacto del backend, con la convención ≤500 LOC/archivo.
- App FastAPI que arranca y sirve `GET /health` reportando liveness + readiness de DB.
- Configuración tipada Pydantic v2 desde `.env`, validada en arranque.
- Conexión SQLAlchemy 2.0 **async** (asyncpg) con patrón **sesión-por-request** vía DI.
- Logging estructurado JSON + instrumentación OpenTelemetry inicial.
- `Dockerfile` multi-stage (convención Easypanel) + `docker-compose.yml` (api/postgres/worker).
- `pyproject.toml` con todo el stack backend declarado.
- Smoke tests: `/health`, arranque de la app, conexión a DB de test.
- Reservar (vacíos) los slots transversales de `core/` para C-02/C-03/C-04.

**Non-Goals:**

- Modelos de dominio, `Tenant`, mixin base, repository genérico (→ C-02).
- Auth, JWT, Argon2id, 2FA, refresh rotation (→ C-03).
- RBAC, matriz de permisos, `require_permission` (→ C-04).
- Cliente Moodle Web Services, worker de comunicaciones con lógica real (→ changes de integración).
- Frontend, CI/CD pipeline completo, migraciones de negocio (Alembic se declara como dependencia y se deja inicializable, pero las migraciones de dominio son de C-02 en adelante).

## Decisions

### D1 — Layout exacto de directorios

El backend vive bajo `backend/` (separado del futuro `frontend/`). Layout objetivo:

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py                  # bootstrap FastAPI + wiring (lifespan, middleware, routers, OTel)
│   ├── api/
│   │   └── v1/
│   │       └── routers/
│   │           ├── __init__.py
│   │           └── health.py    # GET /health (única ruta de C-01)
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py            # Settings (Pydantic v2) — IMPLEMENTADO en C-01
│   │   ├── database.py          # engine async + async_sessionmaker — IMPLEMENTADO en C-01
│   │   ├── logging.py           # logging estructurado JSON — IMPLEMENTADO en C-01
│   │   ├── observability.py     # init OpenTelemetry — IMPLEMENTADO en C-01
│   │   ├── security.py          # RESERVADO → C-03 (JWT, Argon2, AES-256)
│   │   ├── permissions.py       # RESERVADO → C-04 (matriz rol × permiso)
│   │   ├── tenancy.py           # RESERVADO → C-02 (resolución/aislamiento de tenant)
│   │   ├── dependencies.py      # get_db IMPLEMENTADO; get_current_user/require_permission RESERVADOS → C-03/C-04
│   │   └── exceptions.py        # RESERVADO → handlers estandarizados (C-02+)
│   ├── models/__init__.py       # vacío (Base declarativa puede vivir aquí o en database.py)
│   ├── schemas/__init__.py      # vacío salvo HealthResponse si se decide tiparlo
│   ├── repositories/__init__.py # vacío
│   ├── services/__init__.py     # vacío
│   ├── integrations/__init__.py # vacío (n8n_client.py, moodle_ws.py → changes futuros)
│   └── workers/
│       ├── __init__.py
│       └── main.py              # entrypoint mínimo del worker (loop no-op / placeholder)
├── alembic/                     # init de Alembic (env.py async), sin migraciones de dominio
├── tests/
│   ├── __init__.py
│   ├── conftest.py              # fixtures: app, async client httpx, sesión de DB de test
│   ├── test_health.py
│   ├── test_app_startup.py
│   └── test_database.py
├── pyproject.toml
├── Dockerfile
└── .env.example
```

`docker-compose.yml` vive en la **raíz del repo** (orquesta backend + servicios). El árbol respeta literalmente `docs/ARQUITECTURA.md §4`.

**Alternativa descartada**: poner `app/` en la raíz del repo (sin `backend/`). Se descarta porque el contrato (§4) ya prevé `frontend/` paralelo; mezclar ambos en la raíz ensucia el árbol.

### D2 — Qué de `core/` se implementa ahora vs. qué se reserva

Regla: C-01 implementa SOLO lo transversal que no es negocio (config, DB, logging, OTel, `get_db`). Todo lo que toque identidad, permisos o tenant queda como **placeholder con docstring de intención** (no `pass` silencioso: un docstring que diga "RESERVADO para C-0X"). Esto evita que C-02/C-03/C-04 tengan que mover archivos: solo rellenan.

| Módulo `core/` | C-01 | Llenado por |
|----------------|------|-------------|
| `config.py` | ✅ Settings completo | — |
| `database.py` | ✅ engine + sessionmaker + Base | — |
| `logging.py` | ✅ JSON logger | — |
| `observability.py` | ✅ init OTel | — |
| `dependencies.py` | ✅ solo `get_db` | `get_current_user`, `get_tenant`, `require_permission` → C-03/C-04 |
| `security.py` | 🔒 reservado | C-03 |
| `permissions.py` | 🔒 reservado | C-04 |
| `tenancy.py` | 🔒 reservado | C-02 |
| `exceptions.py` | 🔒 reservado | C-02+ |

**Por qué reservar y no omitir**: el contrato lista estos módulos como parte de la estructura canónica. Crearlos vacíos hace explícito el "dónde va cada cosa" y guía a los agentes de changes futuros — fail-explicit sobre fail-silent.

### D3 — Estrategia de sesión async por request

- Engine async único a nivel de módulo (`create_async_engine(DATABASE_URL, ...)`), creado en el arranque (lifespan).
- `async_sessionmaker(engine, expire_on_commit=False)` como factory.
- Dependency `get_db()` async-generator: abre sesión, `yield`, cierra en `finally` (garantiza cierre incluso ante excepción → no fuga de conexiones al pool).
- **Una sesión por request, nunca compartida.** No se usa scoped_session (es patrón sync); en async la sesión-por-request via DI es el patrón correcto de SQLAlchemy 2.0 + FastAPI.

**Alternativa descartada**: sesión global/singleton. Se descarta: rompe aislamiento por request y es un anti-patrón en async (estado compartido entre corutinas concurrentes).

### D4 — Health-check con readiness de DB

`GET /health` devuelve `200` con `{"status": "ok", "database": "<up|down>"}`. La verificación de DB ejecuta un `SELECT 1` sobre una sesión async; si falla, el endpoint **no se cae** — captura el error y reporta `database: "down"` (degradado, no crash). Liveness y readiness conviven en un solo endpoint para simplicidad del cimiento; si más adelante se requiere separar `/health/live` vs `/health/ready` (k8s probes), es un cambio aditivo.

### D5 — Dockerfile multi-stage (convención Easypanel)

Dos etapas:
1. **builder**: imagen Python 3.13, instala dependencias (idealmente con un gestor rápido tipo `uv` o `pip` sobre `pyproject.toml`), genera el entorno.
2. **runtime**: imagen Python 3.13-slim mínima, copia solo el entorno y el código de `app/`, expone el puerto, define el `CMD` que levanta uvicorn. Sin toolchain de build en runtime.

`docker-compose.yml` define `api` (build del Dockerfile, depende de `postgres`, lee `.env`), `postgres` (imagen oficial con volumen persistente y healthcheck), y `worker` (mismo build/imagen que `api`, distinto `command` → `workers/main.py`). Convención Easypanel: variables por entorno, sin secretos hardcodeados, healthchecks declarados.

### D6 — Observabilidad base

- **Logging**: configurador que reemplaza el formatter por uno JSON (una línea por evento, campos timestamp/level/message + extras). Aplica al logger raíz en el arranque.
- **OpenTelemetry**: instrumentación de FastAPI (`opentelemetry-instrumentation-fastapi`) activable por entorno. Sin exporter obligatorio: si no hay endpoint OTLP configurado, la app arranca igual (no se acopla a un backend de telemetría en el cimiento).

### D7 — TDD del cimiento

Strict TDD aplica a lo testeable de C-01: los smoke tests se escriben **antes** que su implementación.
- `test_health.py`: RED primero (espera `200` + JSON de `/health`) → implementar router → GREEN → triangular (caso DB down).
- `test_app_startup.py`: la app se instancia/arranca sin error (TestClient/ASGI lifespan).
- `test_database.py`: contra DB de test, una sesión async ejecuta `SELECT 1`.

El scaffolding puro (crear directorios, `__init__.py`, `pyproject.toml`, Dockerfile) no es "código con comportamiento" testeable por TDD clásico; se valida por existencia/arranque, no por test-first unitario. La fixture de DB de test usa `DATABASE_URL` de test (compose o variable de CI).

## Risks / Trade-offs

- **[Slots reservados quedan como código muerto temporal]** → Mitigación: cada placeholder lleva docstring "RESERVADO para C-0X" y se referencia en `CHANGES.md`; no es muerto, es contrato de extensión.
- **[Health-check con readiness de DB agrega acoplamiento del endpoint a la sesión]** → Mitigación: el chequeo captura excepciones y degrada (no crashea); el endpoint sigue respondiendo aunque la DB esté caída.
- **[Tests de DB requieren una PostgreSQL real (async/asyncpg no levanta sobre SQLite)]** → Mitigación: usar el servicio `postgres` de compose o un Postgres efímero en CI; documentar `DATABASE_URL` de test en `.env.example`. No se mockea la DB en el smoke de conexión porque el objetivo es justamente validar la conexión real.
- **[Python 3.13 reciente puede tener wheels faltantes de alguna dep]** → Mitigación: fijar versiones compatibles en `pyproject.toml`; si una dep no soporta 3.13, evaluar pin/alternativa en apply.
- **[OTel sin exporter podría parecer "no hacer nada"]** → Trade-off aceptado: el cimiento deja la instrumentación lista; el destino de exportación es configuración de despliegue, no del cimiento.

## Migration Plan

No hay migración de datos (primer change, sin estado previo). Deploy: build de la imagen multi-stage → `docker-compose up` levanta api/postgres/worker → `GET /health` verde confirma el cimiento. Rollback: trivial — al ser el primer change, revertir es borrar el árbol; no hay datos ni consumidores aguas arriba.

## Open Questions

- **Gestor de dependencias / lockfile**: `uv` (rápido, lock determinista) vs `pip` + `pip-tools`. Se decide en apply; no bloquea el diseño. Recomendación: `uv` por velocidad de build en multi-stage.
- **Runner del worker**: en C-01 el `worker` es un placeholder (loop no-op). La tecnología real de la cola (asyncio propio / Celery / ARQ) es **ADR-003**, abierta, se resuelve al construir el módulo de comunicaciones. C-01 solo deja el servicio y el entrypoint.
- **Alembic async env**: dejar `alembic/env.py` configurado para engine async ya en C-01 (sin migraciones) vs. inicializarlo recién en C-02. Recomendación: dejar la inicialización en C-01 para que C-02 solo escriba la migración 001; decisión menor, no bloqueante.
