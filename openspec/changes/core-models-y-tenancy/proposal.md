## Why

El cimiento (C-01) dejó el esqueleto Clean Architecture y los slots `core/security.py`, `core/tenancy.py` y `core/exceptions.py` reservados, pero todavía no existe ninguna entidad del dominio ni el mecanismo que garantiza las dos invariantes raíz del producto: el aislamiento multi-tenant (ADR-002, row-level) y el cifrado en reposo de PII (AES-256). Sin la entidad `Tenant`, un mixin base común (UUID + `tenant_id` + timestamps + soft delete) y un repository genérico que filtre por tenant **por defecto**, ningún modelo de negocio posterior (C-03 auth, C-04 RBAC, C-05 audit, C-06 estructura académica) puede construirse de forma segura. Este change materializa esa base transversal de persistencia.

## What Changes

- **Modelo `Tenant`** raíz del sistema: tabla `tenants` con `id` (UUID PK), `nombre`, `estado` y los campos del mixin de auditoría. Es la única entidad sin `tenant_id` (es la raíz del aislamiento, no un dato aislado).
- **Mixin base de persistencia** reutilizable que aporta a toda entidad de negocio: `id` (UUID, PK), `tenant_id` (UUID, FK → `tenants.id`, indexado), `created_at`, `updated_at` (timestamps automáticos) y `deleted_at` (nullable, soft delete). Se descompone en piezas combinables (identidad UUID, columna de tenant, timestamps, soft delete).
- **Repository genérico tenant-scoped** (`repositories/base.py`): clase base parametrizada por modelo cuyas operaciones de lectura filtran SIEMPRE por `tenant_id` y excluyen filas con `deleted_at` no nulo por defecto. El scope de tenant se inyecta en la construcción del repository, nunca se toma de un parámetro de la query. Un acceso sin scope de tenant es un bug que falla en code review.
- **Soft delete transversal**: las entidades nunca se borran físicamente; `delete()` marca `deleted_at`. Las consultas por defecto excluyen lo borrado; existe un camino explícito (`include_deleted=True`) para auditoría/recuperación.
- **Utilidad de cifrado AES-256** en `core/security.py` (slot reservado por C-01): helpers `encrypt`/`decrypt` que cifran/descifran atributos `[cifrado]` (DNI, CUIL, CBU, alias CBU, email PII) usando `ENCRYPTION_KEY` (32 chars, ya en el contrato de `Settings`). El texto plano nunca se persiste ni aparece en logs. Se expone como un `TypeDecorator` de SQLAlchemy para cifrado/descifrado transparente a nivel columna.
- **Migración Alembic 001 (`tenant`)**: primera migración de dominio que crea la tabla `tenants`. Establece la convención de **una migración por cambio de schema**.
- Se establecen las **convenciones base de modelos** que heredarán todos los changes siguientes (snake_case en columnas, UUID como identidad interna, `legajo` nunca como PK).

No hay cambios BREAKING: no existen modelos de dominio previos que romper. C-01 reservó los slots que este change rellena, sin reorganizar el árbol.

## Capabilities

### New Capabilities

- `tenant-model`: la entidad raíz `Tenant` (tabla `tenants`), su identidad UUID, atributos y su rol como raíz del aislamiento multi-tenant.
- `base-entity-mixin`: el mixin base de persistencia que aporta identidad UUID, columna `tenant_id`, timestamps `created_at`/`updated_at` y el campo `deleted_at` a toda entidad de negocio.
- `tenant-scoped-repository`: el repository genérico cuyo scope de tenant está siempre activo; toda lectura filtra por `tenant_id` por defecto y el scope se inyecta, nunca se deriva de la petición.
- `soft-delete`: la semántica de borrado lógico transversal — `delete()` marca `deleted_at`, las consultas por defecto excluyen lo borrado, y existe un camino explícito para incluirlo.
- `pii-encryption`: la utilidad de cifrado AES-256 en reposo para atributos `[cifrado]`, con cifrado/descifrado transparente a nivel columna y prohibición de texto plano en logs.
- `initial-migration`: la migración Alembic 001 que crea la tabla `tenants` y fija la convención de una migración por cambio de schema.

### Modified Capabilities

<!-- Ninguna: las capabilities de C-01 (database-connection, app-scaffold, etc.) no cambian sus requisitos; este change añade entidades y mecanismos sobre el cimiento existente, sin alterar su contrato. -->

## Impact

- **Nuevo código**: `backend/app/models/tenant.py`, `backend/app/models/mixins.py` (mixin base), `backend/app/repositories/base.py` (repository genérico), `backend/app/core/security.py` (helper AES-256 + `TypeDecorator`), `backend/alembic/versions/001_*.py` (migración tenant).
- **Aprovecha lo de C-01**: usa la `Base` declarativa, `build_engine`/`build_session_factory` de `core/database.py`, `Settings.ENCRYPTION_KEY` de `core/config.py`, y `env.py` async de Alembic. No reinventa engine, Base ni session factory.
- **Tests nuevos** (DB real/efímera, sin mocks de DB): aislamiento multi-tenant (un tenant no ve datos de otro), soft delete (lo borrado se excluye por defecto, se incluye con flag), cifrado round-trip (encrypt→decrypt recupera el original; el valor en columna está cifrado), timestamps del mixin.
- **Habilita**: a C-03 (auth, que usará el modelo Usuario sobre este mixin + el helper de cifrado para PII), C-04 (RBAC), C-05 (audit log) y C-06 (estructura académica) — todos heredan el mixin y el repository tenant-scoped.
- **Governance**: **CRÍTICO** — toca multi-tenancy y core-models. Este change es propuesta y diseño; la implementación requiere aprobación humana explícita.
