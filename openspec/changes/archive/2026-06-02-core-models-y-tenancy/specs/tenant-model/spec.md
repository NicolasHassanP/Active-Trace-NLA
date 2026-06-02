## ADDED Requirements

### Requirement: Entidad raíz Tenant

El sistema SHALL definir una entidad `Tenant` (tabla `tenants`) como raíz del modelo multi-tenant. Cada institución SHALL corresponder a exactamente un `Tenant`. `Tenant` SHALL tener identidad UUID interna (`id`), un nombre legible, un estado de ciclo de vida y los campos de auditoría (`created_at`, `updated_at`, `deleted_at`). `Tenant` SHALL ser la única entidad del modelo que NO lleva la columna `tenant_id`, porque es la raíz del aislamiento y no un dato aislado.

#### Scenario: Creación de un tenant

- **WHEN** se crea un `Tenant` con nombre y estado válidos
- **THEN** se persiste con un `id` UUID generado por el sistema
- **AND** sus campos `created_at` y `updated_at` quedan establecidos

#### Scenario: El tenant no lleva columna tenant_id

- **WHEN** se inspecciona el esquema de la tabla `tenants`
- **THEN** la tabla NO contiene una columna `tenant_id` (es la raíz, no una entidad aislada por tenant)

### Requirement: Identidad del tenant por UUID interno

El sistema SHALL identificar a cada `Tenant` exclusivamente por su `id` UUID interno. Ningún atributo de negocio (nombre, código u otro) SHALL usarse como clave de identidad del tenant.

#### Scenario: Identidad por UUID

- **WHEN** se referencia un `Tenant` desde otra entidad
- **THEN** la referencia se realiza por su `id` UUID, nunca por su nombre u otro atributo de negocio
