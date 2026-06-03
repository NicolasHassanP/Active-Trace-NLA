## Why

activia-trace organiza toda la actividad académica alrededor de tres entidades raíz del catálogo del tenant: **Carrera** (programa), **Cohorte** (camada de ingreso de una carrera) y **Materia** (unidad del catálogo único). Hoy, tras C-01..C-04, el sistema tiene identidad (JWT), tenancy row-level, RBAC fino y auditoría (C-05), pero NO existe ninguna estructura académica sobre la que colgar padrones, equipos docentes, encuentros, calificaciones ni liquidaciones. C-06 es uno de los forks del GATE 4 y está en el **camino crítico** (`C-04 → C-06 → C-07 → ...`): sin Carrera/Cohorte/Materia no se puede modelar ningún `Dictado` ni asignación posterior.

El dominio de estas tres entidades ya está **cerrado** por decisiones previas, lo que desbloquea C-06:
- **ADR-006** (Materia + Dictado): `Materia` es la definición única y estática del catálogo del tenant. La actividad (calificaciones, equipos, encuentros, coloquios) cuelga del `Dictado` (instancia de la materia en una `carrera × cohorte`), NO de la `Materia`.
- **PA-07** (cerrada): una `Cohorte` pertenece exclusivamente a UNA carrera (FK obligatoria `carrera_id`); alumnos de distintas carreras no se mezclan en una cohorte.
- **PA-01** (cerrada vía ADR-006): el catálogo de materias es único por tenant; no hay catálogos paralelos.

C-06 entrega el **catálogo estructural** (las tres entidades y su ABM administrativo). El `Dictado` y la actividad que cuelga de él quedan para changes posteriores (ver "Decisión de scope — Dictado" más abajo).

## What Changes

- **Modelo `Carrera`** (tabla `carrera`, migración 005): tenant-scoped, soft-delete, con `codigo` (único por tenant) y `nombre`, estado `Activa | Inactiva`.
- **Modelo `Cohorte`** (tabla `cohorte`, migración 005): tenant-scoped, soft-delete, FK obligatoria `carrera_id`, `nombre`, `anio`, `vig_desde`, `vig_hasta` (nullable = abierta), estado `Activa | Inactiva`. Único `(tenant_id, carrera_id, nombre)`.
- **Modelo `Materia`** (tabla `materia`, migración 005): tenant-scoped, soft-delete, `codigo` (único por tenant), `nombre`, estado `Activa | Inactiva`.
- **Permiso RBAC `estructura:gestionar`** (rol ADMIN): se agrega al catálogo de permisos sembrado (alta del grant). Cada endpoint de ABM lo exige; fail-closed (403 sin permiso).
- **ABM `Carrera`**: `GET/POST/PATCH /api/v1/admin/carreras` (+ `/{id}`) — crear, listar, editar, cambiar estado activa/inactiva, baja lógica.
- **ABM `Cohorte`**: `GET/POST/PATCH /api/v1/admin/cohortes` (+ `/{id}`) — crear (con `carrera_id`), listar, editar, cambiar estado, baja lógica.
- **ABM `Materia`**: `GET/POST/PATCH /api/v1/admin/materias` (+ `/{id}`) — crear, listar, editar, cambiar estado, baja lógica.
- **Reglas de negocio**:
  - Unicidad `(tenant_id, codigo)` en `Carrera` y `Materia` (sobre filas no borradas).
  - Unicidad `(tenant_id, carrera_id, nombre)` en `Cohorte` (sobre filas no borradas).
  - Una carrera inactiva NO admite crear cohortes abiertas (cohorte con `vig_hasta IS NULL` y estado `Activa`).
- **Repositories tenant-scoped** para las tres entidades, filtrando por `tenant_id` y `deleted_at IS NULL` por defecto.
- **Services** con la lógica de unicidad y la regla carrera-inactiva.
- **Schemas Pydantic v2** (`extra='forbid'`) de request/response para las tres entidades.

## Capabilities

### New Capabilities
- `career-management`: ABM de carreras tenant-scoped con código único por tenant, estado activa/inactiva y baja lógica, protegido por `estructura:gestionar`.
- `cohort-management`: ABM de cohortes tenant-scoped, cada una perteneciente a exactamente una carrera (PA-07), con unicidad `(tenant, carrera, nombre)` y la regla de carrera-inactiva, protegido por `estructura:gestionar`.
- `subject-catalog`: ABM del catálogo único de materias del tenant (ADR-006/PA-01), con código único por tenant, estado y baja lógica, protegido por `estructura:gestionar`.

### Modified Capabilities
<!-- Ninguna capability existente cambia sus requisitos de comportamiento. C-06 agrega un permiso (`estructura:gestionar`) al catálogo RBAC pero no altera la mecánica de RBAC ni de auth/tenancy. -->

## Impact

- **Migración**: nueva `005_create_estructura_academica.py` con `revision="005"`, `down_revision="004"`. ⚠️ **CHANGES.md menciona "Migración 004" para C-06, pero la 004 ya está ocupada por `audit_event` (C-05)**. La numeración real existente es: 001 tenants, 002 auth, 003 rbac, 004 audit_event. C-06 es la **005**. Crea las tablas `carrera`, `cohorte`, `materia` + el seed/grant del permiso `estructura:gestionar`.
- **Modelos**: nuevo `backend/app/models/estructura.py` (`Carrera`, `Cohorte`, `Materia`), componiendo los mixins existentes (`UUIDMixin`, `TenantMixin`, `TimestampMixin`, `SoftDeleteMixin`).
- **Repositories**: nuevo `backend/app/repositories/estructura_repository.py` (o uno por entidad si supera 500 LOC) sobre `TenantScopedRepository`.
- **Services**: nuevo `backend/app/services/estructura_service.py` con unicidad y regla carrera-inactiva.
- **Schemas**: nuevo `backend/app/schemas/estructura.py` (Pydantic v2, `extra='forbid'`).
- **API**: nuevos routers `backend/app/api/v1/routers/admin_carreras.py`, `admin_cohortes.py`, `admin_materias.py` (o un `admin_estructura.py` agrupado) + registro en el agregador v1.
- **RBAC**: el permiso `estructura:gestionar` se suma al catálogo de permisos del tenant (grant a ADMIN, scope global).
- **Dependencias**: ninguna librería nueva; reutiliza SQLAlchemy 2.0 async, Pydantic v2, FastAPI, JWT/RBAC ya existentes. **Depende de C-04 (done)**.
- **Governance**: dominio **MEDIO** (lógica de dominio / catálogos). Implementar con checkpoints; surfacear decisiones no obvias. (El permiso toca RBAC, que es CRÍTICO: el alta del grant `estructura:gestionar` debe revisarse, pero no modifica el mecanismo de RBAC.)
- **Scope de commits**: `materias` (el scope conventional-commit más cercano a estructura académica; las carreras/cohortes comparten dominio de catálogo).

## Decisión de scope — Dictado (PARA REVISIÓN DEL USUARIO)

CHANGES.md §C-06 lista el scope como **SOLO** `Carrera`, `Cohorte`, `Materia`. ADR-006 define además la entidad `Dictado` (instancia de una materia en `carrera × cohorte`), de la que cuelga toda la actividad académica.

**Decisión tomada: `Dictado` queda FUERA de C-06.** Justificación:
1. CHANGES.md es autoritativo sobre el scope y no lista `Dictado`.
2. `Dictado` no es estructura de catálogo: es la unión operativa carrera × cohorte × materia sobre la que se montan padrón, equipos, encuentros y calificaciones. Su diseño correcto depende de cómo esos módulos posteriores lo consuman (C-07+).
3. Incluirlo ahora obligaría a anticipar decisiones de los módulos de actividad, ampliando el blast radius de un change MEDIO de catálogo.

C-06 deja el catálogo (Carrera/Cohorte/Materia) listo para que un change posterior (C-07+) introduzca `Dictado` con sus FKs a las tres entidades. **Si el usuario prefiere incluir `Dictado` en C-06**, debe confirmarlo explícitamente; en ese caso se ampliaría el scope, la migración y los tests. Ver Open Questions OQ-1.
