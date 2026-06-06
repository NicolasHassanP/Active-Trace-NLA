> **Modo Strict TDD**: cada comportamiento sigue RED (test que falla) → GREEN (mínimo) → TRIANGULATE (≥2 casos: happy + edge) → REFACTOR. Tests contra PostgreSQL efímero real (asyncpg), NUNCA mockeando la DB. Antes de modificar cualquier archivo de C-01/C-02/C-03 correr el SAFETY NET (suite existente como baseline). Governance CRÍTICO: este change requiere aprobación humana del diseño antes de escribir código.

## 0. Pre-requisitos y SAFETY NET

- [x] 0.1 ✅ OQ-4 RESUELTA (usuario, 2026-06-02): NEXO se siembra como `Rol` válido con un único permiso base `avisos:confirmar` (scope `global`), todo lo demás fail-closed; su set completo se difiere a PA-25. Documentado en design.md (D6 + OQ-4).
- [x] 0.2 ✅ OQ-1 RESUELTA: catálogo tenant-scoped (sin catálogo global). OQ-2 RESUELTA: seed de tenants futuros fuera de C-04 (provisioning posterior). OQ-3 RESUELTA: sin cache en C-04.
- [x] 0.3 SAFETY NET: correr la suite completa existente (`pytest backend/tests/`) y capturar baseline "{N} passing". Si algo falla, reportar como pre-existing failure y NO corregirlo.
- [x] 0.4 Verificar que existe la base de test (`TEST_DATABASE_URL`) y que el conftest crea el schema vía `Base.metadata.create_all`.

## 1. Modelos RBAC (rol, permiso, rol_permiso)

- [x] 1.1 RED: test en `backend/tests/test_rbac_models.py` que importa `Rol`, `Permiso`, `RolPermiso` desde `app.models.rbac` (aún no existen) y afirma sus columnas (`tenant_id`, `id`, timestamps, `deleted_at`) y el enum `permiso_scope`.
- [x] 1.2 GREEN: crear `backend/app/models/rbac.py` con `Rol` (`nombre`, `descripcion`), `Permiso` (`codigo`, `modulo`, `accion`, `descripcion`), `RolPermiso` (`rol_id`, `permiso_id`, `scope` enum `permiso_scope` default `'global'`), todos heredando `TenantScopedBase`. Aplicar los `UniqueConstraint` de D7. (≤500 LOC.)
- [x] 1.3 GREEN: registrar los modelos en `backend/app/models/__init__.py` (SAFETY NET sobre ese archivo) para que `Base.metadata` los conozca.
- [x] 1.4 TRIANGULATE: persistir un `Rol` y un `Permiso` en el tenant de test (happy) y afirmar que un segundo `Rol` con el mismo `(tenant_id, nombre)` viola la unicidad (edge); afirmar que el mismo `nombre` en otro tenant SÍ persiste.
- [x] 1.5 TRIANGULATE: persistir un `RolPermiso` con `scope='propio'` y otro con `scope='global'`; afirmar el default `'global'` y el rechazo de un duplicado `(tenant_id, rol_id, permiso_id)`.
- [x] 1.6 REFACTOR: limpiar nombres/constantes; correr tests → verdes.

## 2. Migración 003 + seed de la matriz §3.3

- [x] 2.1 RED: test en `backend/tests/test_rbac_migration.py` que aplica `upgrade()` de `003` sobre la base de test y afirma que existen las tablas `rol`, `permiso`, `rol_permiso`, sus índices (`tenant_id`, `deleted_at`, FKs) y el enum `permiso_scope`.
- [x] 2.2 GREEN: crear `backend/alembic/versions/003_create_rbac_tables.py` (`revision="003"`, `down_revision="002"`) siguiendo el estilo exacto de `002`: SQL crudo `op.execute`, índices explícitos por FK + `deleted_at`, `downgrade()` en orden inverso eliminando enum incluido.
- [x] 2.3 RED: test que, tras el seed, afirma que un tenant existente tiene los 7 roles del dominio y que `COORDINADOR` tiene `comunicacion:aprobar` (global) y `PROFESOR` tiene `calificaciones:importar` (propio).
- [x] 2.4 GREEN: implementar el seed idempotente dentro de `upgrade()` (rutina reutilizable, `INSERT ... ON CONFLICT DO NOTHING` por las claves únicas de D2), derivando los pares `(rol, permiso, scope)` literalmente de la matriz §3.3. NEXO se siembra con un único `rol_permiso` → `avisos:confirmar` (scope `global`), por la resolución de OQ-4 (resto fail-closed, diferido a PA-25).
- [x] 2.5 TRIANGULATE: afirmar idempotencia (correr el seed dos veces → sin duplicados, edge); que el alcance `(propio)` se sembró correctamente para PROFESOR/TUTOR donde la matriz lo marca (happy + edge); y que **NEXO tiene exactamente un permiso `avisos:confirmar` y ningún otro** (OQ-4, edge fail-closed).
- [x] 2.6 TRIANGULATE: afirmar que `downgrade()` elimina las tres tablas y el enum sin afectar las tablas de auth (C-03).
- [x] 2.7 REFACTOR: extraer la matriz a una estructura de datos legible dentro de la migración; correr tests → verdes.

## 3. Repository del catálogo (tenant-scoped)

- [x] 3.1 RED: test en `backend/tests/test_rbac_repository.py` que construye `RbacRepository` con `tenant_id` y afirma que `get_roles_with_permissions(role_names)` devuelve los `RolPermiso` (con scope) de los roles indicados, scopeados al tenant.
- [x] 3.2 GREEN: crear `backend/app/repositories/rbac_repository.py` construido sobre `TenantScopedRepository` / la factory de tenancy; una query con JOIN `rol → rol_permiso → permiso` filtrando por `(tenant_id, rol.nombre IN names, deleted_at IS NULL)`.
- [x] 3.3 TRIANGULATE: afirmar aislamiento entre tenants (un repo del tenant A no devuelve filas del tenant B, edge) y que un `role_name` inexistente devuelve conjunto vacío para ese rol (edge).
- [x] 3.4 REFACTOR: limpiar la query; correr tests → verdes.

## 4. AuthorizationService — resolución de permisos efectivos

- [x] 4.1 RED: test en `backend/tests/test_authorization_service.py` que llama `AuthorizationService.resolve_effective_permissions(current_user)` y afirma la **unión** de permisos de ["PROFESOR", "COORDINADOR"].
- [x] 4.2 GREEN: crear `backend/app/services/authorization_service.py` que, vía `RbacRepository`, reúne los `RolPermiso` de los `current_user.roles` y devuelve un conjunto de `PermissionGrant(codigo, scope)`. Sin acceso directo a DB (sólo repository). (≤500 LOC.)
- [x] 4.3 TRIANGULATE: rol desconocido en el claim → se ignora, no falla, no concede (fail-closed, edge); tenant sin catálogo → conjunto vacío (edge).
- [x] 4.4 TRIANGULATE: alcance — PROFESOR solo → `calificaciones:importar` propio (happy); PROFESOR+COORDINADOR → mismo código resuelve a global (global prevalece, edge).
- [x] 4.5 TRIANGULATE: afirmar que un `roles` enviado en body/header NO altera la resolución (sólo cuenta `current_user.roles`).
- [x] 4.6 REFACTOR: extraer la regla "global prevalece sobre propio" a un helper puro testeado; correr tests → verdes.

## 5. Guard require_permission (dependency de FastAPI)

- [x] 5.1 SAFETY NET: re-correr `backend/tests/test_current_user_dependency.py` antes de tocar `dependencies.py`; capturar baseline.
- [x] 5.2 RED: test en `backend/tests/test_require_permission.py` con un endpoint de prueba protegido por `require_permission("calificaciones:importar")`; un ALUMNO autenticado → `403`.
- [x] 5.3 GREEN: implementar `require_permission(codigo)` en `backend/app/core/dependencies.py` (reemplaza el placeholder reservado) como dependency factory que depende de `get_current_user` + `get_db`, construye `AuthorizationService` y devuelve `403` si el código no está en el conjunto efectivo; si está, devuelve el `PermissionGrant`.
- [x] 5.4 TRIANGULATE: COORDINADOR con el permiso → el endpoint ejecuta (happy); petición sin JWT válido → `401` antes del chequeo de permiso (edge); usuario de tenant sin catálogo → `403` (edge).
- [x] 5.5 TRIANGULATE: afirmar que el guard expone el alcance — PROFESOR (`atrasados:ver` propio) → grant con scope propio; COORDINADOR (global) → grant con scope global.
- [x] 5.6 TRIANGULATE: afirmar que la identidad/roles del guard provienen sólo del token, no de params/body/header de la petición.
- [x] 5.7 REFACTOR: limpiar la factory; correr tests → verdes.

## 6. Schemas y cierre

- [x] 6.1 RED/GREEN: si se exponen lecturas del catálogo, crear `backend/app/schemas/rbac.py` con Pydantic v2 `model_config = ConfigDict(extra='forbid')` y su test (rechazo de campos extra). Si NO se exponen endpoints en C-04, omitir y registrarlo. → OMITIDO: C-04 no expone endpoints CRUD del catálogo (Non-Goal explícito en design.md).
- [x] 6.2 Verificar cobertura: ≥80% líneas global, ≥90% en `authorization_service.py`, el guard y el seed (reglas de negocio de seguridad). → 95% total, 96% authorization_service, 100% rbac_repository, 100% rbac models.
- [x] 6.3 Correr la suite completa → toda verde, incluida la baseline del SAFETY NET sin regresiones. → 44 passing (C-04 tests); 3 pre-existing failures (test_current_user_dependency Settings/env issue) sin cambios respecto al baseline.
- [x] 6.4 Marcar C-04 `[x]` en `CHANGES.md` y anotar la corrección del número de migración (003, no 002).
