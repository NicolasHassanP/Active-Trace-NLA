## ADDED Requirements

### Requirement: Migración Alembic 001 que crea la tabla tenants

El sistema SHALL incluir una migración Alembic (001) que cree la tabla `tenants` con sus columnas (`id` UUID PK, `nombre`, `estado`, `created_at`, `updated_at`, `deleted_at`) y los índices correspondientes. La migración SHALL ser aplicable (`upgrade`) y reversible (`downgrade`) sobre la configuración async de Alembic existente.

#### Scenario: Aplicar la migración crea la tabla

- **WHEN** se aplica la migración 001 sobre una base de datos sin la tabla `tenants`
- **THEN** la tabla `tenants` queda creada con sus columnas e índices

#### Scenario: Revertir la migración elimina la tabla

- **WHEN** se revierte la migración 001
- **THEN** la tabla `tenants` se elimina sin dejar el esquema en estado inconsistente

### Requirement: Una migración por cambio de schema

El sistema SHALL mantener la convención de una migración Alembic por cambio de schema. Ningún cambio de esquema SHALL aplicarse manualmente fuera de una migración versionada.

#### Scenario: Cambio de schema vía migración versionada

- **WHEN** se requiere un cambio en el esquema de la base de datos
- **THEN** el cambio se materializa en una nueva migración Alembic versionada, no en una edición manual del esquema
