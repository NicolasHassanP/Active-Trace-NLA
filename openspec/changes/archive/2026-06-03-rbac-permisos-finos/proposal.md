## Why

C-03 dejó la identidad resuelta desde el JWT (`get_current_user` → `CurrentUser` con `user_id`, `tenant_id`, `roles`), pero los `roles` son hoy strings sin significado autorizativo: ningún endpoint puede declarar qué permiso exige, y el placeholder `require_permission` quedó reservado y vacío. Sin un modelo de autorización fino, todo endpoint de negocio que sigue (C-05 en adelante) carecería de control de acceso o lo hardcodearía por rol — violando la regla dura de RBAC `modulo:accion` fail-closed. C-04 cierra esa brecha: convierte los roles en permisos efectivos resueltos server-side por petición y entrega el guard que todo endpoint protegido usará.

## What Changes

- **Catálogo administrable rol × permiso como datos** (NO hardcodeado): tablas `rol`, `permiso` (`modulo:accion`) y la matriz de unión `rol_permiso`. La matriz de capacidades de `03_actores_y_roles.md` §3.3 se convierte en datos sembrados, no en código.
- **Seed de roles del dominio**: ALUMNO, TUTOR, PROFESOR, COORDINADOR, NEXO, ADMIN, FINANZAS, con sus permisos según la matriz §3.3.
- **Resolución de permisos efectivos server-side por petición**: a partir del claim `roles` del JWT verificado (vía `get_current_user`) → `Rol` → unión de `RolPermiso`, acotada por tenant. La vigencia de asignaciones (§5 de la KB) NO se resuelve aquí — pertenece a C-07; C-04 resuelve los permisos directamente desde el claim `roles`.
- **Guard `require_permission("modulo:accion")`** como dependency de FastAPI montada sobre `get_current_user`, declarable por endpoint. **Fail-closed**: sin el permiso explícito → `403`. Sin flag de superusuario.
- **Soporte de scope `(propio)`**: los permisos marcados como propios en la matriz (p. ej. `auditoria:ver (propio)`) se modelan de forma que el guard pueda exponer el alcance al endpoint consumidor; la aplicación row-level completa puede diferirse a los changes que consuman cada permiso, pero el modelo debe soportarla.
- **Migración Alembic** `003_create_rbac_tables` con las tres tablas + seed de la matriz base. (Corrige el número: CHANGES.md dice "002", pero 002 ya lo usó C-03.)
- **Repositories tenant-scoped** para el catálogo y un **servicio de resolución de permisos** que devuelve el conjunto efectivo de un `CurrentUser`.

## Capabilities

### New Capabilities
- `rbac-permission-catalog`: catálogo administrable de roles y permisos (`modulo:accion`) y su matriz de unión `rol_permiso`, persistido como datos por tenant y sembrado con la matriz base del dominio.
- `effective-permission-resolution`: resolución server-side, por petición, del conjunto de permisos efectivos de un usuario como unión de los permisos de sus roles (claim `roles` del JWT) acotada por tenant, incluyendo el alcance `(propio)` vs. global.
- `require-permission-guard`: dependency `require_permission("modulo:accion")` montada sobre `get_current_user`, fail-closed (sin permiso → `403`), declarada por endpoint, que nunca lee identidad/tenant/roles de la petición.

### Modified Capabilities
<!-- Ninguna capability existente cambia sus requisitos. C-04 solo añade. -->

## Impact

- **Código nuevo**: `backend/app/models/rbac.py` (Rol, Permiso, RolPermiso), `backend/app/repositories/rbac_repository.py`, `backend/app/services/authorization_service.py` (resolución de permisos efectivos), guard `require_permission` en `backend/app/core/dependencies.py` (reemplaza el placeholder reservado), `backend/app/schemas/rbac.py` (si se exponen endpoints de catálogo).
- **Migración**: `backend/alembic/versions/003_create_rbac_tables.py` (down_revision `002`) + seed de la matriz §3.3.
- **Integración con C-03**: `require_permission` se monta sobre `get_current_user` sin modificar su contrato; el claim `roles` del JWT mapea por nombre a registros `Rol`.
- **Sin dependencia de C-07**: no usa `Usuario` ni `Asignacion` (aún no existen). La vigencia temporal queda fuera de alcance.
- **Habilita** a todos los changes de negocio posteriores (C-05 en adelante) a declarar `require_permission(...)` en sus endpoints.
- **Modelos**: alta de los modelos en `backend/app/models/__init__.py` para que `Base.metadata` los registre (requerido por el conftest de tests).
