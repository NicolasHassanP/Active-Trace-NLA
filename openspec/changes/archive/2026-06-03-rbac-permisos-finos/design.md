## Context

C-03 (auth-jwt-2fa, archivado) entregó `get_current_user(request) -> CurrentUser`, un value object frozen `(user_id, tenant_id, roles)` derivado **exclusivamente** del JWT verificado. El claim `roles` es un array de strings (snapshot espejo de `AuthIdentity.roles`, JSONB). El placeholder `require_permission` quedó reservado y vacío en `backend/app/core/dependencies.py`.

C-04 construye la autorización fina encima de esa identidad. El dominio (`knowledge-base/03_actores_y_roles.md` §3) exige RBAC con permisos `modulo:accion`, sin flag de superusuario, con la matriz rol × permiso §3.3 modelada **como datos administrables**, no hardcodeada. La regla de oro de identidad (§1, §3.3 de ARQUITECTURA) prohíbe leer identidad/roles/tenant de la petición.

Restricciones de plataforma vigentes:
- Clean Architecture estricta: Routers → Services → Repositories → Models. La resolución de permisos es lógica → vive en un Service; toda query → vía Repository.
- Multi-tenancy row-level: `tenant_id` en tablas de negocio; repositories filtran por tenant por defecto (`TenantScopedRepository`).
- Soft delete siempre; Pydantic `extra='forbid'`; ≤500 LOC/archivo; una sola migración Alembic por cambio de schema; snake_case.
- Tests contra PostgreSQL efímero real (asyncpg), nunca mockeando la DB. Conftest crea el schema vía `Base.metadata.create_all`, por lo que los modelos nuevos deben registrarse en `app/models/__init__.py`.

**Governance: CRÍTICO** (RBAC/seguridad). Este diseño es para revisión humana antes de implementar; toda decisión de seguridad no obvia se explicita abajo.

## Goals / Non-Goals

**Goals:**
- Catálogo `rol` / `permiso` / `rol_permiso` persistido como datos, sembrado con la matriz §3.3.
- Resolución server-side, por petición, del conjunto efectivo de permisos de un `CurrentUser` (unión de los permisos de sus roles, acotada por tenant).
- Guard `require_permission("modulo:accion")` montado sobre `get_current_user`, fail-closed (sin permiso → `403`).
- Soporte modelado del alcance `(propio)` vs. global, de forma que el endpoint consumidor pueda aplicarlo.
- Migración `003_create_rbac_tables` con seed reproducible.

**Non-Goals:**
- Vigencia temporal de asignaciones (`desde`/`hasta`, §5 KB) → C-07. C-04 resuelve permisos directamente del claim `roles`, sin `Usuario`/`Asignacion` (no existen aún).
- Aplicación row-level completa del alcance `(propio)` en cada endpoint de negocio → corresponde a cada change consumidor; C-04 sólo provee el modelo y el contrato del guard.
- UI/endpoints CRUD de administración del catálogo (alta/baja de roles y permisos por ADMIN) → quedan fuera salvo lo mínimo para sembrar y resolver. (Ver Open Question OQ-2.)
- Impersonación (`impersonacion:usar`) → su lógica de sesión es C posterior; aquí sólo se siembra el permiso.

## Decisions

### D1 — Número de migración: `003`, no `002`
CHANGES.md dice "Migración 002" para C-04, pero **002 ya está ocupada por C-03** (`002_create_auth_tables.py`, `revision="002"`, `down_revision="001"`). La migración de C-04 SHALL ser `003_create_rbac_tables.py` con `revision="003"`, `down_revision="002"`. Se sigue el estilo exacto de 002: SQL crudo vía `op.execute`, índices explícitos sobre cada FK (PostgreSQL no indexa FKs automáticamente), índice sobre `deleted_at`, `downgrade()` en orden inverso de dependencias.
**Alternativa descartada**: respetar literalmente "002" → colisión de revisión, cadena de Alembic rota. La corrección se documenta para que el revisor humano la valide y CHANGES.md se actualice al cerrar.

### D2 — Catálogo tenant-scoped desde el inicio (con seed replicado por tenant)
**Decisión**: `rol`, `permiso` y `rol_permiso` son **tenant-scoped** (heredan `TenantScopedBase`: `id`, `tenant_id`, timestamps, `deleted_at`). La matriz base §3.3 se siembra **por cada tenant existente**.
**Justificación**: la regla dura #9 (multi-tenancy row-level) y la KB (§2 nota de extensibilidad: "el conjunto de roles debe ser un catálogo administrable **por tenant**"; §3.3 nota: "catálogo rol × permiso administrable") exigen que cada institución pueda personalizar su catálogo sin afectar a otra. Un catálogo global compartido violaría el aislamiento si un tenant editara un permiso. Hacerlo tenant-scoped desde el día 0 evita una migración de retrofit dolorosa después.
**Trade-off**: duplicación del seed base en cada tenant (N filas × tenants). Es aceptable: el volumen es pequeño (7 roles, ~20 permisos) y la consistencia se garantiza con una rutina de seed idempotente reutilizable (D6). La unicidad se modela por tenant: `uq_rol_tenant_nombre (tenant_id, nombre)`, `uq_permiso_tenant_codigo (tenant_id, codigo)`, `uq_rol_permiso (tenant_id, rol_id, permiso_id)`.
**Alternativa descartada**: catálogo global base + overlay tenant-scoped opcional. Más flexible pero introduce una resolución de dos capas (merge global+tenant) y ambigüedad de edición ("¿edito el global o creo override?") — complejidad no justificada para C-04. Si en el futuro se necesita un "catálogo plantilla" compartido, se modela como datos semilla, no como tabla global. Se deja como OQ-1 para confirmación del revisor.

### D3 — El claim `roles` (string) mapea por nombre a `Rol.nombre`
El JWT lleva `roles: ["PROFESOR", "COORDINADOR"]` (snapshot de `AuthIdentity.roles`). La resolución hace: por cada nombre del claim, buscar el `Rol` activo del tenant con `nombre == claim` → reunir sus `RolPermiso` → unión de `Permiso.codigo`. Los nombres de rol del seed SHALL coincidir exactamente con los valores que C-03 escribe en el claim (ALUMNO, TUTOR, PROFESOR, COORDINADOR, NEXO, ADMIN, FINANZAS, en mayúsculas).
**Gotcha de seguridad**: un nombre de rol en el claim que no exista como `Rol` del tenant SHALL ser ignorado (no concede permisos), nunca causar error que abra acceso. Fail-closed por construcción.
**Alternativa descartada**: poner permisos directamente en el JWT — explícitamente prohibido por ARQUITECTURA §3.1 ("los permisos se resuelven server-side en cada petición, nunca se almacenan en el token").

### D4 — Representación del alcance `(propio)` como columna en `rol_permiso`
La marca `(propio)` de la matriz §3.3 es **por par rol×permiso**, no por permiso (p. ej. PROFESOR tiene `calificaciones:importar (propio)` pero COORDINADOR lo tiene global). Por tanto el alcance se modela como columna en la tabla de unión: `rol_permiso.scope` enum `('global', 'propio')`, default `'global'`.
**Contrato del guard**: `require_permission("modulo:accion")` resuelve, para el usuario, el **alcance más permisivo** de ese permiso entre todos sus roles (si algún rol lo tiene `global`, gana `global`; si sólo lo tiene `propio`, el alcance efectivo es `propio`). El guard SHALL exponer ese alcance al endpoint (devolviendo un objeto `PermissionGrant(codigo, scope)` que el endpoint inyecta), para que el endpoint consumidor pueda aplicar el filtro row-level "sólo mis datos" cuando `scope == 'propio'`. C-04 define y testea el contrato; la aplicación efectiva del filtro vive en cada endpoint consumidor.
**Alternativa descartada**: codificar el alcance en el string del permiso (`calificaciones:importar:propio`) → multiplica el catálogo, rompe la semántica `modulo:accion` y obliga a que cada endpoint conozca ambas variantes. Peor.

### D5 — Resolución en un `AuthorizationService`, guard como dependency delgada
La unión de permisos es lógica de negocio → `AuthorizationService.resolve_effective_permissions(current_user) -> set[PermissionGrant]`, que usa un `RbacRepository` tenant-scoped (construido con `current_user.tenant_id` vía la factory de tenancy). El guard `require_permission(codigo)` es una **dependency factory** de FastAPI: depende de `get_current_user` + `get_db`, construye el service, resuelve los permisos efectivos y:
- si el `codigo` no está en el conjunto efectivo → `HTTPException(403)` (mapeo de ARQUITECTURA §3: "Sin permiso (authz) → 403"),
- si está → devuelve el `PermissionGrant` (con su `scope`) para que el endpoint lo use.
El guard NUNCA lee tenant/roles/identidad de la petición; todo viene de `get_current_user`. Sin lógica de negocio en el router; sin acceso directo a DB desde el service (siempre vía repository).
**Nota de performance**: la resolución hace 1–2 queries por petición (roles del tenant por nombre + sus permisos, resoluble con un único JOIN). Aceptable; cachear se difiere (los permisos cambian raramente, pero el cache de autorización es delicado — fuera de alcance, OQ-3).

### D6 — Seed reproducible e idempotente dentro de la migración `003`
La matriz §3.3 se siembra en `upgrade()` de `003`, en una rutina idempotente que, **por cada tenant existente**, inserta los `permiso` faltantes, los `rol` faltantes y los `rol_permiso` faltantes (con su `scope`). Se implementa con SQL parametrizado / `INSERT ... ON CONFLICT DO NOTHING` sobre las claves únicas de D2, de modo que correr la migración sobre una base con datos parciales no duplique ni falle. Los pares `(rol, permiso, scope)` se derivan literalmente de la matriz §3.3.
**NEXO (OQ-4 resuelta)**: se siembra como `Rol` válido con un **único** `rol_permiso` → `avisos:confirmar` (scope `global`), como base mínima fail-closed. Su set completo de articulación se difiere a la resolución de **PA-25** (change posterior). El resto de roles (ALUMNO…FINANZAS) se siembran con su columna completa de §3.3.
**Gotcha**: el seed depende de que existan tenants. Para tenants creados **después** de esta migración, el catálogo base debe sembrarse en el alta del tenant (gancho de provisioning) — se anota como dependencia para el change de gestión de tenants/usuarios; C-04 sólo cubre el seed de los tenants presentes al migrar. (OQ-2.)

### D7 — Modelo de datos (resumen)
- `rol`: `TenantScopedBase` + `nombre VARCHAR(50)` (p. ej. "PROFESOR"), `descripcion VARCHAR(255) NULL`. Unique `(tenant_id, nombre)` sobre filas activas.
- `permiso`: `TenantScopedBase` + `codigo VARCHAR(100)` (`modulo:accion`), `modulo VARCHAR(50)`, `accion VARCHAR(50)`, `descripcion VARCHAR(255) NULL`. Unique `(tenant_id, codigo)`.
- `rol_permiso`: `TenantScopedBase` + `rol_id UUID FK→rol`, `permiso_id UUID FK→permiso`, `scope` enum `permiso_scope ('global','propio')` default `'global'`. Unique `(tenant_id, rol_id, permiso_id)`. Índices sobre `rol_id` y `permiso_id`.
Todas con índice en `tenant_id` y `deleted_at`, siguiendo el patrón de 002.

## Risks / Trade-offs

- **[Seed desincronizado para tenants nuevos]** → C-04 siembra sólo tenants existentes; tenants creados luego quedarían sin catálogo. Mitigación: anotar la dependencia de provisioning (OQ-2) y, en tests, cubrir explícitamente "tenant sin catálogo → usuario sin permisos → 403" (fail-closed correcto aunque incompleto).
- **[Drift entre `AuthIdentity.roles` y catálogo `Rol`]** → un nombre de rol en el JWT que no existe como `Rol` del tenant. Mitigación: D3 — se ignora silenciosamente (fail-closed), nunca concede ni rompe. Test dedicado.
- **[Performance de resolución por petición]** → 1 JOIN por request protegida. Mitigación: índices sobre las FKs y `(tenant_id, nombre)`; cache diferido (OQ-3).
- **[Aplicación incompleta del scope `(propio)`]** → C-04 sólo modela y expone el alcance; si un endpoint consumidor olvida aplicar el filtro `propio`, un usuario vería datos ajenos. Mitigación: el guard devuelve el `PermissionGrant` con scope explícito (obliga al endpoint a recibirlo) y se documenta como contrato a respetar; code review en cada change consumidor.
- **[Duplicación del catálogo por tenant]** → más filas y seed replicado. Mitigación: volumen pequeño; rutina de seed idempotente única.

## Migration Plan

1. Crear modelos `rbac.py` y registrarlos en `app/models/__init__.py` (necesario para `Base.metadata.create_all` del conftest).
2. Escribir `003_create_rbac_tables.py` (`down_revision="002"`): tres tablas + enum `permiso_scope` + índices + seed idempotente de la matriz §3.3 por tenant.
3. Repository `RbacRepository`, service `AuthorizationService`, guard `require_permission` (reemplaza el placeholder en `dependencies.py`).
4. **Rollback**: `downgrade()` elimina índices, constraints, tablas (orden inverso de FK) y el enum `permiso_scope`. Sin pérdida de datos de auth (tablas independientes).
5. Despliegue: la migración es aditiva; no toca tablas de C-01/C-02/C-03. Ningún endpoint existente cambia de comportamiento hasta que declare `require_permission`.

## Open Questions

> **Todas resueltas por el usuario (2026-06-02) antes de apply.** Se conservan con su resolución para trazabilidad.

- **OQ-1 (tenant-scoped vs. global+overlay)** — ✅ **RESUELTA: tenant-scoped (D2)**. Se confirma el catálogo tenant-scoped desde el inicio; NO se modela un "catálogo plantilla" global compartido. Si en el futuro se necesita propagar cambios a todos los tenants, se hará como datos semilla reutilizables, no como tabla global.
- **OQ-2 (seed de tenants futuros)** — ✅ **RESUELTA: fuera de C-04**. El seed del catálogo base al alta de un tenant nuevo es responsabilidad del gancho de provisioning de tenants (change posterior). C-04 sólo siembra los tenants existentes al migrar. Queda anotado como dependencia.
- **OQ-3 (cache de permisos)** — ✅ **RESUELTA: sin cache en C-04**. Se acepta resolución por petición (1 JOIN). El cache de authz se evaluará después con métricas reales.
- **OQ-4 (permisos de NEXO)** — ✅ **RESUELTA: set mínimo fail-closed**. La matriz §3.3 no detalla columna NEXO y su semántica sigue abierta en **PA-25**. C-04 siembra NEXO como `Rol` válido con un **único permiso base** —la confirmación de avisos (`avisos:confirmar`, la única capacidad atribuible sin cerrar PA-25)— y **todo lo demás fail-closed**. El conjunto real de articulación de NEXO se completará al resolver PA-25, en un change posterior. Sembrar NEXO (en vez de omitirlo) evita que un usuario con rol NEXO en el JWT no resuelva contra ningún `Rol` y obtenga 403 en todo. Ver D6.
