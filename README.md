# activia-trace

Plataforma de gestión académica y trazabilidad multi-tenant. Opera como capa de orquestación sobre Moodle: consolida calificaciones, detecta atrasos, gestiona comunicación saliente con aprobación, equipos docentes, encuentros, coloquios, liquidaciones y auditoría completa. Cada institución es un tenant aislado — todo audita.

---

## Stack

| Capa | Tecnología |
|------|-----------|
| Lenguaje | Python 3.13 |
| Framework | FastAPI (async) |
| ORM | SQLAlchemy 2.0 async |
| Migraciones | Alembic |
| Base de datos | PostgreSQL |
| Validación | Pydantic v2 |
| Auth | JWT (access + refresh rotation) + Argon2id |
| Cifrado en reposo | AES-256-GCM (PII: CBU, DNI) |
| Testing | pytest + coverage (≥80% líneas, ≥90% reglas de negocio) |

---

## Requisitos previos

- **Python 3.13+**
- **PostgreSQL** corriendo localmente — opciones:
  - pgAdmin 4 (mantiene el servicio activo mientras está abierto)
  - Docker Desktop: `docker-compose up -d postgres`
  - Servicio nativo de Windows (recomendado para desarrollo continuo): ver nota al final

---

## Setup local (primera vez)

### 1. Clonar e instalar dependencias

```bash
git clone https://github.com/NicolasHassanP/Active-Trace-NLA.git
cd active-trace/backend
pip install -e ".[dev]"
```

### 2. Crear las bases de datos

Desde pgAdmin o psql:

```sql
CREATE DATABASE activia_trace;
CREATE DATABASE activia_trace_test;
```

> `activia_trace` es la DB de desarrollo/producción.
> `activia_trace_test` es la DB de tests (se usa en `pytest`).

### 3. Crear el archivo `.env`

Crear `backend/.env` con el siguiente contenido:

```env
# Base de datos principal
DATABASE_URL=postgresql+asyncpg://postgres:TU_PASSWORD@localhost:5432/activia_trace

# Base de datos de tests
TEST_DATABASE_URL=postgresql+asyncpg://postgres:TU_PASSWORD@localhost:5432/activia_trace_test

# JWT — mínimo 32 caracteres, generá uno con: python -c "import secrets; print(secrets.token_hex(32))"
SECRET_KEY=reemplaza_con_string_de_al_menos_32_caracteres

# Cifrado AES-256 — EXACTAMENTE 32 caracteres
ENCRYPTION_KEY=reemplaza_con_string_de_exactamente32c
```

> El archivo `.env` nunca se commitea (está en `.gitignore`).

### 4. Aplicar migraciones

```bash
cd backend
alembic upgrade head
```

Esto aplica las 4 migraciones existentes (001 base, 002 auth, 003 rbac, 004 audit) sobre `activia_trace`.

Para la DB de tests, las migraciones se aplican automáticamente al correr los tests por primera vez (el conftest usa `create_all`).

### 5. Seed de datos de prueba (tenant Demo)

```bash
cd backend
python seed_rbac_demo.py   # roles, permisos y matriz RBAC
python seed_demo_user.py   # usuario admin@demo.com / Admin1234!
```

Ambos scripts son idempotentes — pueden correrse más de una vez sin problema.

### 6. Verificar

```bash
cd backend
pytest tests/ -q
```

Deberías ver los tests de C-01 a C-05 pasar (~140+ tests). Los fallos pre-existentes relacionados con `TEST_DATABASE_URL extra_forbidden` son conocidos y no bloquean el desarrollo.

---

## Levantar el servidor

```bash
cd backend
uvicorn app.main:app --reload
```

El servidor queda disponible en `http://localhost:8000`.

- Health check: `GET /health`
- Docs: `GET /docs` (Swagger UI)

> Solo necesitás `activia_trace` corriendo para el servidor. `activia_trace_test` es solo para tests.

---

## Comandos útiles

```bash
# Correr todos los tests
pytest tests/ -q

# Correr tests de un módulo específico
pytest tests/test_rbac_models.py -v

# Ver cobertura
pytest tests/ --cov=app --cov-report=term-missing

# Crear una nueva migración
alembic revision --autogenerate -m "descripcion_del_cambio"

# Ver estado de migraciones
alembic current
alembic history

# Rollback una migración
alembic downgrade -1
```

---

## Estructura del proyecto

```
active-trace/
├── backend/
│   ├── app/
│   │   ├── api/v1/routers/     # Endpoints FastAPI
│   │   ├── core/               # Config, DB, dependencies, seguridad
│   │   ├── models/             # SQLAlchemy models
│   │   ├── repositories/       # Acceso a DB (tenant-scoped)
│   │   ├── schemas/            # Pydantic DTOs
│   │   └── services/           # Lógica de negocio
│   ├── alembic/versions/       # Migraciones (001–004)
│   ├── tests/                  # Suite de tests
│   └── pyproject.toml
├── openspec/
│   ├── changes/archive/        # Changes implementados
│   └── specs/                  # Specs por capability
├── knowledge-base/             # Dominio del negocio (fuente de verdad)
├── docs/                       # Arquitectura, PRD
└── CHANGES.md                  # Roadmap de implementación
```

---

## Estado del roadmap

Ver [CHANGES.md](CHANGES.md) — es la fuente de verdad del plan de implementación (24 changes, 6 fases, estado actualizado en cada archive).

---

## Notas importantes

### PostgreSQL debe estar corriendo antes de los tests

Si PostgreSQL no está activo, `pytest` se cuelga indefinidamente esperando conexión (no falla rápido).

**Recomendación**: habilitar PostgreSQL como servicio de arranque automático en Windows:

```powershell
# En PowerShell como Administrador
Set-Service -Name "postgresql-x64-17" -StartupType Automatic
# (ajustar el nombre según la versión instalada)
```

O desde `services.msc` → buscar el servicio de PostgreSQL → Tipo de inicio: Automático.

### `TEST_DATABASE_URL` en `.env` y `extra='forbid'`

`Settings` tiene `extra='forbid'`. Si `TEST_DATABASE_URL` está en el `.env`, algunos módulos que instancian `Settings()` directamente fallan. Este es un bug conocido (pre-existente desde C-03) que no bloquea el desarrollo — los tests de auth e infraestructura base tienen ~70 fallos por esta causa. Los módulos de C-04 y C-05 lo sortean con monkeypatching en los tests que lo necesitan.

### No correr múltiples `pytest` en paralelo

Todos los tests comparten `activia_trace_test`. Correr dos instancias de pytest simultáneamente genera colisiones. Siempre una a la vez.

### Reglas de arquitectura (no negociables)

- Identidad **siempre** desde el JWT (`get_current_user`), nunca desde params/body/header
- `tenant_id` en cada query — los repositories filtran por tenant por defecto
- `require_permission("modulo:accion")` en cada endpoint protegido
- Sin mocks de DB en tests — usar `activia_trace_test` real
- Pydantic schemas con `extra='forbid'`
- Sin hard delete — soft delete siempre
