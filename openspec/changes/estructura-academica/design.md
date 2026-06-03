## Context

Tras C-01..C-05 el sistema tiene: identidad desde JWT (`get_current_user` → `CurrentUser(user_id, tenant_id, roles)`), tenancy row-level (`TenantScopedRepository` filtra por `tenant_id` y `deleted_at IS NULL`), RBAC fino (`require_permission(codigo)` → `PermissionGrant(codigo, scope)`, fail-closed) y auditoría append-only. Los mixins de modelos viven en `backend/app/models/mixins.py` (`UUIDMixin`, `TenantMixin`, `TimestampMixin`, `SoftDeleteMixin`); `TenantScopedBase` los compone para entidades de catálogo con soft-delete. Las migraciones se escriben a mano con SQL explícito y seed idempotente (patrón DO/EXCEPTION de 003); los repositories se construyen con `(model, session, tenant_id)`; los schemas usan Pydantic v2 con `extra='forbid'`; los tests usan DB real (`activia_trace_test`, sin mocks) y Strict TDD.

C-06 agrega el catálogo estructural académico. Las invariantes de dominio que constriñen el diseño (todas ya cerradas):
- **Catálogo único de materias por tenant** (ADR-006 / PA-01): una sola fuente de verdad; nada de catálogos paralelos.
- **Cohorte pertenece a UNA carrera** (PA-07): FK obligatoria `carrera_id`; unicidad `(tenant_id, carrera_id, nombre)`.
- **Materia ≠ Dictado** (ADR-006): `Materia` es definición estática del catálogo; la actividad cuelga del `Dictado`. C-06 NO construye `Dictado` (ver proposal "Decisión de scope").
- **Multi-tenancy row-level** (regla dura #9): `tenant_id` en cada tabla; repositories filtran por tenant por defecto. Unicidad e índices SIEMPRE incluyen `tenant_id`.
- **Identidad desde la sesión** (regla dura #8): `tenant_id` se deriva del JWT, jamás del body/params.
- **RBAC fail-closed** (regla dura #10): cada endpoint declara `require_permission("estructura:gestionar")`; sin grant → 403.
- **Soft delete siempre** (regla dura #13): nunca hard delete; las bajas marcan `deleted_at`.
- **Governance MEDIO**: implementar con checkpoints; el alta del grant `estructura:gestionar` toca RBAC y se surfacea para revisión.

## Goals / Non-Goals

**Goals:**
- Persistir `Carrera`, `Cohorte`, `Materia` tenant-scoped con soft-delete, cada una con su `estado` (`Activa | Inactiva`).
- Garantizar unicidad `(tenant_id, codigo)` en `Carrera` y `Materia`, y `(tenant_id, carrera_id, nombre)` en `Cohorte`, considerando SOLO filas no borradas.
- Modelar `Cohorte.carrera_id` como FK obligatoria a `Carrera` (PA-07).
- Impedir crear una cohorte abierta (estado `Activa` y `vig_hasta IS NULL`) cuando su carrera está `Inactiva`.
- Exponer ABM (crear / listar / editar / cambiar estado / baja lógica) para las tres entidades bajo `/api/v1/admin/{carreras,cohortes,materias}`, protegido por `estructura:gestionar`.
- Sembrar el permiso `estructura:gestionar` y otorgarlo a ADMIN (scope global) en la migración 005.
- Aislamiento multi-tenant verificado: ningún listado/lectura cruza tenants.

**Non-Goals:**
- NO se construye la entidad `Dictado` ni la unión carrera × cohorte × materia (Non-Goal explícito; queda para C-07+). C-06 entrega solo el catálogo estructural.
- NO se construye el ABM de padrones, equipos docentes, encuentros, calificaciones ni programas de materia (cuelgan del `Dictado`, changes posteriores).
- NO se modifica el mecanismo de RBAC ni de auth/tenancy/auditoría; C-06 solo suma un permiso al catálogo.
- NO se cargan datos semilla de carreras/cohortes/materias reales (cada tenant define su catálogo en runtime).
- NO se implementa reasignación ni migración de cohortes entre carreras (la FK `carrera_id` es estable; cambiarla es un caso de negocio fuera de scope).

## Decisions

### D1 — Migración 005, NO 004 (corrección de CHANGES.md)
CHANGES.md §C-06 dice "Migración 004", pero la 004 ya está ocupada por `audit_event` (C-05). La próxima revisión libre es **005**. `revision="005"`, `down_revision="004"`. Se sigue el estilo de 003/004: `CREATE TABLE` con SQL explícito, índices nombrados, enums idempotentes (patrón DO/EXCEPTION), seed idempotente del permiso.
**Alternativa descartada**: autogenerar con `--autogenerate` → el repo usa migraciones escritas a mano y deterministas.

### D2 — Enum de estado compartido `estado_estructura`
Las tres entidades comparten el ciclo de vida `Activa | Inactiva`. Se modela un único tipo enum PostgreSQL `estado_estructura AS ENUM ('activa', 'inactiva')` y un enum Python `EstadoEstructura(str, enum.Enum)` reutilizado por los tres modelos.
**Alternativa considerada**: un enum por entidad → duplicación innecesaria; el ciclo de vida es idéntico. Si una entidad necesitara estados propios en el futuro, se introduce su enum entonces.

### D3 — Modelos sobre `TenantScopedBase` (con soft-delete)
A diferencia de `AuditEvent` (C-05, append-only sin soft-delete), las tres entidades de catálogo SÍ admiten edición y baja lógica. Por eso componen `TenantScopedBase` completo: `UUIDMixin` + `TenantMixin` + `TimestampMixin` (`created_at`/`updated_at`) + `SoftDeleteMixin` (`deleted_at`). Esto habilita el ABM y la baja lógica (regla dura #13) y reutiliza el filtrado por defecto de `TenantScopedRepository`.

### D4 — Unicidad parcial sobre filas no borradas
La unicidad `(tenant_id, codigo)` (Carrera/Materia) y `(tenant_id, carrera_id, nombre)` (Cohorte) debe ignorar las filas con baja lógica: dar de baja una materia `PROG_I` debe permitir crear otra `PROG_I` después. Se implementa con **índice único parcial** PostgreSQL: `CREATE UNIQUE INDEX ... WHERE deleted_at IS NULL`.
**Alternativa descartada**: `UNIQUE` constraint plano sobre todas las columnas → bloquearía recrear un código tras una baja, contradiciendo soft-delete. La validación de unicidad también se chequea en el service (mensaje de error de dominio claro 409) antes de tocar la DB; el índice parcial es la defensa en profundidad.

### D5 — `Cohorte.carrera_id` FK obligatoria con FK RESTRICT (PA-07)
`carrera_id` es `NOT NULL`, FK a `carrera(id)` con `ON DELETE RESTRICT` (no hay hard delete de carrera de todos modos por soft-delete, pero el RESTRICT evita huérfanos a nivel DB). La unicidad de cohorte se scopea por `(tenant_id, carrera_id, nombre)`: la misma denominación (`AGO-2025`) puede existir en dos carreras distintas del mismo tenant, pero no dos veces en la misma carrera.
**Materializa PA-07**: alumnos de distintas carreras no se mezclan en una cohorte porque la cohorte es de una sola carrera.

### D6 — Regla "carrera inactiva no admite cohortes abiertas" en el service
Una "cohorte abierta" = estado `Activa` y `vig_hasta IS NULL`. Al crear o editar una cohorte (o al reactivarla / quitarle `vig_hasta`), el service valida que la carrera referida esté `Activa`. Si la carrera está `Inactiva`, se rechaza con error de dominio (422/409). La regla vive en `EstructuraService`, NO en el router ni en la DB (regla dura #11: lógica de negocio solo en services).
**Caso límite (OQ-2 — RESUELTO)**: al desactivar una carrera que ya tiene cohortes abiertas, el sistema BLOQUEA la desactivación con un error de dominio (HTTP 409 Conflict). El ADMIN debe cerrar o inactivar todas las cohortes abiertas de esa carrera ANTES de poder inactivarla. No hay cascada ni cierre silencioso de cohortes. Rationale: fail-closed y predecible; preserva el invariante "una carrera inactiva no admite cohortes abiertas" sin efectos laterales ocultos; alinea con la filosofía append-only / acción explícita del proyecto. La regla aplica tanto al alta/edición de cohortes (no crear cohorte abierta bajo carrera inactiva) como a la desactivación de carreras (no desactivar carrera con cohortes abiertas).

### D7 — Repositories tenant-scoped
Tres repositories (`CarreraRepository`, `CohorteRepository`, `MateriaRepository`) sobre `TenantScopedRepository`, construidos con `(model, session, tenant_id)`. Exponen `add`, `get_by_id`, `list` (con filtros opcionales: estado, y `carrera_id` para cohortes), `update`, `soft_delete`. Métodos auxiliares de unicidad: `get_by_codigo(codigo)` (Carrera/Materia) y `get_by_carrera_nombre(carrera_id, nombre)` (Cohorte), ambos scoped por tenant y filtrando `deleted_at IS NULL`. Si el archivo único superara 500 LOC se divide en uno por entidad (regla dura #15).

### D8 — `EstructuraService` con unicidad y regla carrera-inactiva
`EstructuraService(carrera_repo, cohorte_repo, materia_repo)` (o un service por entidad si crece) expone los casos de uso del ABM. Responsabilidades:
- Validar unicidad ANTES de insertar (lookup por código / por carrera+nombre) → 409 si existe.
- Aplicar la regla D6 en alta/edición de cohorte.
- Verificar que `carrera_id` referido por una cohorte exista, sea del mismo tenant y no esté borrado.
- Identidad/tenant SIEMPRE desde `CurrentUser` (regla dura #8), nunca del body.

### D9 — Endpoints ABM bajo `/api/v1/admin/...`, protegidos por `estructura:gestionar`
Routers REST por entidad:
- `GET    /api/v1/admin/carreras` · `POST /api/v1/admin/carreras` · `PATCH /api/v1/admin/carreras/{id}` · `DELETE /api/v1/admin/carreras/{id}` (baja lógica).
- Idéntico para `/cohortes` y `/materias`.
Cada ruta declara `Depends(require_permission("estructura:gestionar"))`; sin el grant → 403 (fail-closed). El cambio de estado activa/inactiva se modela como un `PATCH` (campo `estado`), no como un endpoint dedicado, para mantener el ABM uniforme. La baja lógica usa `DELETE` → `soft_delete` (marca `deleted_at`), nunca hard delete.

### D10 — Permiso `estructura:gestionar` sembrado en la migración 005
El permiso se agrega al catálogo de permisos del tenant siguiendo el patrón de la migración 003 (RBAC), con un seed idempotente que lo otorga a ADMIN con scope global. Governance: el alta del grant toca RBAC (CRÍTICO) y se surfacea en el resumen para revisión, pero no modifica el mecanismo de RBAC.
**Alternativa descartada**: crear el permiso vía endpoint en runtime → el catálogo de permisos del sistema es versionado con el código (igual que en C-05); sembrar en migración mantiene consistencia y reproducibilidad.

### D11 — Schemas Pydantic v2
Por entidad: `CarreraCreate`, `CarreraUpdate`, `CarreraRead` (y equivalentes para Cohorte y Materia). Todos con `model_config = ConfigDict(extra='forbid')`. `CohorteCreate` incluye `carrera_id` obligatorio, `anio: int` (NOT NULL, obligatorio), `vig_desde: date` (NOT NULL, obligatorio) y `vig_hasta: date | None` (nullable — None = cohorte abierta). `*Update` tienen todos los campos opcionales (PATCH parcial). Los `*Read` exponen `id`, `estado`, timestamps; nunca exponen `tenant_id` derivado de sesión como editable.

## Risks / Trade-offs

- **[Índice único parcial vs constraint plano]** → Se elige índice parcial `WHERE deleted_at IS NULL` para convivir con soft-delete. Riesgo: race condition entre el chequeo del service y el insert. Mitigación: el índice parcial en DB es la garantía dura; el service traduce el `IntegrityError` a un 409 limpio. Test de concurrencia no es obligatorio pero el camino DB queda cubierto.
- **[Regla carrera-inactiva — bloqueo bidireccional]** → Desactivar una carrera con cohortes abiertas está BLOQUEADO (OQ-2 resuelto: D6 ampliadado). El invariante "carrera inactiva no admite cohortes abiertas" se garantiza en ambas direcciones: al crear/editar cohortes Y al desactivar carreras. No hay cascada ni permisividad silenciosa. Riesgo residual: el ADMIN debe recordar cerrar cohortes antes de inactivar una carrera; el mensaje de error 409 debe ser instructivo al respecto.
- **[Scope de Dictado excluido]** → Un change posterior deberá introducir `Dictado` y posiblemente refactorizar relaciones. Riesgo bajo: las tres entidades son raíces estables; `Dictado` solo añade FKs hacia ellas.
- **[Un solo archivo de modelos/repos/routers puede crecer >500 LOC]** → Mitigación: dividir por entidad si se supera el límite (regla dura #15). Se monitorea en tasks (cierre).
- **[Materia sin vínculo a carrera en C-06]** → El catálogo de materias es plano por tenant (correcto según ADR-006: la materia se asocia a carrera/cohorte vía `Dictado`, no directamente). No es un riesgo, es la decisión de dominio; se documenta para evitar que alguien agregue un `carrera_id` a `Materia` por error.

## Migration Plan

1. Crear `backend/alembic/versions/005_create_estructura_academica.py`:
   - `revision="005"`, `down_revision="004"`.
   - `CREATE TYPE estado_estructura AS ENUM ('activa', 'inactiva')` idempotente (patrón DO/EXCEPTION de 003).
   - `CREATE TABLE carrera (...)`: `id`, `tenant_id` (FK RESTRICT), `codigo`, `nombre`, `estado` (estado_estructura), `created_at`, `updated_at`, `deleted_at` (nullable).
   - `CREATE TABLE materia (...)`: misma forma que carrera (`codigo`, `nombre`, `estado`, timestamps, soft-delete).
   - `CREATE TABLE cohorte (...)`: `id`, `tenant_id` (FK RESTRICT), `carrera_id` (FK RESTRICT, NOT NULL), `nombre`, `anio` (NOT NULL, integer), `vig_desde` (NOT NULL, date), `vig_hasta` (nullable, date — NULL = cohorte abierta), `estado`, timestamps, `deleted_at`.
   - Índices únicos parciales: `ux_carrera_tenant_codigo (tenant_id, codigo) WHERE deleted_at IS NULL`; `ux_materia_tenant_codigo (tenant_id, codigo) WHERE deleted_at IS NULL`; `ux_cohorte_tenant_carrera_nombre (tenant_id, carrera_id, nombre) WHERE deleted_at IS NULL`.
   - Índices de consulta: `ix_cohorte_tenant_carrera (tenant_id, carrera_id)`.
   - Seed idempotente del permiso `estructura:gestionar` + grant a ADMIN (scope global), siguiendo el patrón de seed de RBAC en 003.
2. `downgrade()`: drop tablas (`cohorte` antes que `carrera` por la FK), drop enum, revertir el seed del permiso/grant. Orden inverso.
3. No hay backfill (las tablas arrancan vacías; cada tenant carga su catálogo en runtime).
4. **Rollback**: `alembic downgrade 004` elimina las tres tablas, el enum y el permiso sembrado. Las FKs son salientes desde las nuevas tablas; no afecta tablas previas.

## Open Questions

- **OQ-1 (scope Dictado)**: ¿`Dictado` debe entrar en C-06 o queda para C-07+? **Propuesta**: queda fuera (CHANGES.md no lo lista; depende de los módulos de actividad). Requiere confirmación del usuario antes de apply.
- **OQ-2 (carrera-inactiva con cohortes abiertas)** — **RESUELTA**: al desactivar una carrera que ya tiene cohortes abiertas, el sistema **BLOQUEA** la desactivación con HTTP 409 Conflict. El ADMIN debe cerrar/inactivar todas las cohortes abiertas de la carrera antes de poder inactivarla. Sin cascada, sin permisividad silenciosa. Ver D6 y Risks para el detalle.
- **OQ-3 (campos de Cohorte)** — **RESUELTA**: `anio` es NOT NULL (entero), `vig_desde` es NOT NULL (fecha de inicio de vigencia), `vig_hasta` es nullable (NULL = cohorte abierta). Basis: KB §E2 lista `anio` como campo propio; HU-22 marca `nombre`, `año` y `fecha de inicio` (`vig_desde`) como obligatorios; F5.2 los lista por separado. La DDL y los schemas Pydantic reflejan esta decisión.
- **OQ-4 (scope del permiso)** — **RESUELTA**: `estructura:gestionar` se otorga a ADMIN con scope global únicamente. COORDINADOR no recibe ningún grant de lectura sobre el catálogo en C-06 (F5.1/F5.2 son ADMIN-only); la lectura para otros roles se resuelve cuando esos módulos la necesiten. El seed ADMIN-only es suficiente para C-06.
