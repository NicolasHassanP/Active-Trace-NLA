# Tasks — C-06 estructura-academica

> Governance: MEDIO (lógica de dominio / catálogos). El seed del permiso `estructura:gestionar` toca RBAC (CRÍTICO): surfacear ese alta para revisión del usuario antes de implementar la migración.
> Strict TDD en cada task con lógica: test que falla → código mínimo → triangulación → refactor. Tests con DB real (`activia_trace_test`, sin mocks). Pydantic v2 con `extra='forbid'`. snake_case. ≤500 LOC/archivo. Soft delete siempre. Identidad/tenant SIEMPRE desde el JWT.
> ⚠️ Migración **005** (la 004 ya está ocupada por audit_event). `down_revision="004"`.
> ⚠️ Antes de apply: confirmar OQ-1 (Dictado fuera de scope) con el usuario. OQ-2 y OQ-3 ya están resueltas (ver design.md).

## 1. Enum de estado compartido (D2)

- [ ] 1.1 RED: test de que `EstadoEstructura(str, enum.Enum)` contiene `activa` e `inactiva` y rechaza un valor arbitrario
- [ ] 1.2 GREEN: crear el enum `EstadoEstructura` en `backend/app/models/estructura.py` (o `core/enums.py` si se comparte)
- [ ] 1.3 Triangulación: verificar que el enum es uniforme entre tenants (constante del sistema, no por tenant)

## 2. Modelo `Carrera` (D3)

- [ ] 2.1 RED: test de que `Carrera` tiene `id`, `tenant_id`, `codigo`, `nombre`, `estado`, `created_at`, `updated_at`, `deleted_at`
- [ ] 2.2 GREEN: definir `Carrera` en `backend/app/models/estructura.py` componiendo `TenantScopedBase` (UUID + Tenant + Timestamp + SoftDelete)
- [ ] 2.3 Triangulación: test de que `estado` por defecto es `activa` y que `deleted_at` arranca nulo

## 3. Modelo `Materia` (D3)

- [ ] 3.1 RED: test de que `Materia` tiene `id`, `tenant_id`, `codigo`, `nombre`, `estado`, timestamps, `deleted_at`, y NO tiene `carrera_id` (catálogo plano, ADR-006)
- [ ] 3.2 GREEN: definir `Materia` en `backend/app/models/estructura.py` sobre `TenantScopedBase`
- [ ] 3.3 Triangulación: test de defaults (`estado=activa`, `deleted_at` nulo)

## 4. Modelo `Cohorte` (D3, D5, PA-07)

- [ ] 4.1 RED: test de que `Cohorte` tiene `id`, `tenant_id`, `carrera_id` (NOT NULL), `nombre`, `anio` (NOT NULL, integer), `vig_desde` (NOT NULL, date), `vig_hasta` (nullable date — NULL = abierta), `estado`, timestamps, `deleted_at`
- [ ] 4.2 GREEN: definir `Cohorte` sobre `TenantScopedBase` con FK obligatoria `carrera_id` → `Carrera`; `anio` y `vig_desde` declarados NOT NULL en el modelo y en la DDL
- [ ] 4.3 Triangulación: test de que `vig_hasta` admite nulo (cohorte abierta), `carrera_id` es obligatorio, y que `anio`/`vig_desde` sin valor causan error de validación

## 5. Migración 005 (D1, D4, D5, D10)

- [ ] 5.1 Crear `backend/alembic/versions/005_create_estructura_academica.py` con `revision="005"`, `down_revision="004"`
- [ ] 5.2 `upgrade()`: crear enum `estado_estructura` idempotente (patrón DO/EXCEPTION de 003)
- [ ] 5.3 `upgrade()`: `CREATE TABLE carrera` y `CREATE TABLE materia` con `tenant_id` FK RESTRICT, `estado`, timestamps y `deleted_at`
- [ ] 5.4 `upgrade()`: `CREATE TABLE cohorte` con `carrera_id` FK RESTRICT NOT NULL, `anio` NOT NULL (integer), `vig_desde` NOT NULL (date), `vig_hasta` nullable (date — NULL = cohorte abierta), `estado`, timestamps, `deleted_at`
- [ ] 5.5 `upgrade()`: índices únicos parciales `ux_carrera_tenant_codigo` y `ux_materia_tenant_codigo` `(tenant_id, codigo) WHERE deleted_at IS NULL`; `ux_cohorte_tenant_carrera_nombre (tenant_id, carrera_id, nombre) WHERE deleted_at IS NULL`; índice `ix_cohorte_tenant_carrera (tenant_id, carrera_id)`
- [ ] 5.6 `upgrade()`: seed idempotente del permiso `estructura:gestionar` + grant a ADMIN (scope global), patrón de seed de RBAC en 003 — **CHECKPOINT: surfacear a usuario (toca RBAC)**
- [ ] 5.7 `downgrade()`: drop `cohorte` (antes de `carrera` por la FK), `materia`, `carrera`, drop enum, revertir seed del permiso/grant
- [ ] 5.8 Test de migración: aplicar upgrade/downgrade contra la DB de test y verificar que las tablas existen/no existen

## 6. Índices únicos parciales — unicidad sobre filas no borradas (D4)

- [ ] 6.1 RED: test de que crear dos carreras con el mismo `codigo` (no borradas) en el mismo tenant falla a nivel DB
- [ ] 6.2 RED: test de que crear dos materias con el mismo `codigo` (no borradas) en el mismo tenant falla a nivel DB
- [ ] 6.3 RED: test de que crear dos cohortes con el mismo `(carrera_id, nombre)` (no borradas) en el mismo tenant falla a nivel DB
- [ ] 6.4 GREEN: confirmar que los índices parciales de 5.5 cubren los tres casos
- [ ] 6.5 Triangulación: test de que tras baja lógica (deleted_at set) se puede recrear el mismo código/nombre

## 7. Repositories tenant-scoped (D7)

- [ ] 7.1 RED: test de que `CarreraRepository.add` fuerza `tenant_id` al scope y `list()` filtra por tenant y `deleted_at IS NULL`
- [ ] 7.2 RED: test de aislamiento — `list()` del tenant A nunca devuelve registros del tenant B (las tres entidades)
- [ ] 7.3 GREEN: crear `backend/app/repositories/estructura_repository.py` (o uno por entidad si supera 500 LOC) sobre `TenantScopedRepository`, con `add`, `get_by_id`, `list`, `update`, `soft_delete`
- [ ] 7.4 GREEN: agregar `get_by_codigo` (Carrera/Materia) y `get_by_carrera_nombre` (Cohorte), scoped por tenant y `deleted_at IS NULL`
- [ ] 7.5 Triangulación: test de `CohorteRepository.list(carrera_id=...)` y de que `soft_delete` marca `deleted_at` sin borrar físicamente

## 8. `EstructuraService` — unicidad y regla carrera-inactiva (D6, D8)

- [ ] 8.1 RED: test de que crear una carrera/materia con código ya existente lanza error de conflicto y no persiste
- [ ] 8.2 RED: test de que crear una cohorte con `(carrera_id, nombre)` ya existente lanza conflicto
- [ ] 8.3 RED: test de que crear una cohorte referenciando una carrera de OTRO tenant es rechazado (PA-07 + aislamiento)
- [ ] 8.4 RED: test de que crear una cohorte abierta (estado activa, `vig_hasta` nulo) bajo una carrera `Inactiva` es rechazado; bajo carrera `Activa` se acepta (D6)
- [ ] 8.5 RED: test de que desactivar una carrera con al menos una cohorte abierta (estado `Activa`, `vig_hasta` nulo) lanza error de conflicto (409) y la carrera permanece activa (D6 — OQ-2 resuelto)
- [ ] 8.6 RED: test de que desactivar una carrera sin cohortes abiertas (ninguna cohorte activa con `vig_hasta` nulo) sucede correctamente
- [ ] 8.7 GREEN: crear `backend/app/services/estructura_service.py` con los casos de uso del ABM, validando unicidad, existencia/tenant de la carrera, la regla carrera-inactiva al crear/editar cohortes, y el bloqueo de desactivación de carrera con cohortes abiertas
- [ ] 8.8 Triangulación: test de edición que reactiva/quita `vig_hasta` de una cohorte cuya carrera está inactiva → rechazado
- [ ] 8.9 Refactor: extraer la verificación "cohorte abierta" (`estado == Activa and vig_hasta is None`) a un helper claro reutilizable por ambas reglas

## 9. Schemas Pydantic v2 (D11)

- [ ] 9.1 RED: test de que `CarreraCreate`/`CarreraRead` validan entrada/salida bien formada y rechazan campos no declarados (`extra='forbid'`)
- [ ] 9.2 RED: test de que `CohorteCreate` exige `carrera_id`, `anio` (int, NOT NULL) y `vig_desde` (date, NOT NULL); acepta `vig_hasta` nulo (cohorte abierta); rechaza la omisión de `anio` o `vig_desde` con ValidationError
- [ ] 9.3 GREEN: crear `backend/app/schemas/estructura.py` con `*Create`, `*Update` (campos opcionales) y `*Read` para las tres entidades, `model_config = ConfigDict(extra='forbid')`
- [ ] 9.4 Triangulación: test de que `*Read` no expone `tenant_id` como editable y refleja `estado`/timestamps

## 10. Endpoints ABM `/api/v1/admin/...` protegidos (D9)

- [ ] 10.1 RED: test de que `POST /api/v1/admin/carreras` sin `estructura:gestionar` responde 403 (fail-closed) — y equivalentes para cohortes/materias
- [ ] 10.2 RED: test de que con el permiso se puede crear/listar/editar/dar de baja cada entidad, derivando `tenant_id` del JWT
- [ ] 10.3 GREEN: crear routers `admin_carreras.py`, `admin_cohortes.py`, `admin_materias.py` (o `admin_estructura.py` agrupado) con `GET/POST/PATCH/DELETE`, cada ruta con `Depends(require_permission("estructura:gestionar"))`
- [ ] 10.4 GREEN: registrar los routers en el agregador v1
- [ ] 10.5 RED: test de que el conflicto de unicidad del service se traduce a 409; la regla carrera-inactiva al crear/editar cohortes a 422/409; y el intento de desactivar una carrera con cohortes abiertas a 409 con mensaje instructivo (no 500)
- [ ] 10.6 Triangulación: test de aislamiento de tenant en los endpoints (usuario del tenant A no ve/edita registros del tenant B) y de baja lógica vía `DELETE`

## 11. Cierre

- [ ] 11.1 Confirmar resolución de OQ-1 (Dictado fuera de scope) con el usuario y registrar la decisión aquí. (OQ-2 y OQ-3 ya están resueltas en design.md y aplicadas en los artefactos.)
- [ ] 11.2 Verificar cobertura ≥80% líneas / ≥90% reglas de negocio del módulo de estructura académica
- [ ] 11.3 Verificar que ningún archivo backend supera 500 LOC; una sola migración (005) para el cambio de schema
- [ ] 11.4 Marcar C-06 como `[x]` en `CHANGES.md`
