## ADDED Requirements

### Requirement: Identidad UUID interna en toda entidad

Toda entidad del modelo SHALL tener una clave primaria `id` de tipo UUID generada por el sistema. El UUID SHALL ser la identidad interna opaca; ningún atributo de negocio (p. ej. `legajo`) SHALL actuar como clave primaria, credencial ni selector de identidad.

#### Scenario: Generación de identidad al crear

- **WHEN** se instancia y persiste cualquier entidad del modelo
- **THEN** recibe un `id` UUID único generado por el sistema

#### Scenario: El legajo no es identidad

- **WHEN** una entidad de negocio incluye un atributo `legajo`
- **THEN** `legajo` se almacena como atributo de negocio y NO como clave primaria ni selector de identidad

### Requirement: Columna tenant_id en toda entidad de negocio

Toda entidad de negocio (toda excepto la raíz `Tenant`) SHALL incluir una columna `tenant_id` de tipo UUID, no nula, con clave foránea a `tenants.id` e indexada. `tenant_id` SHALL ser la raíz del aislamiento de datos entre instituciones.

#### Scenario: Entidad de negocio lleva tenant_id

- **WHEN** se define cualquier entidad de negocio sobre el mixin base
- **THEN** la entidad incluye una columna `tenant_id` UUID no nula con FK a `tenants.id`

### Requirement: Timestamps de auditoría automáticos

Toda entidad SHALL registrar `created_at` al crearse y `updated_at` al crearse y en cada modificación posterior. El sistema SHALL establecer estos timestamps automáticamente; `created_at` NO SHALL cambiar tras la creación.

#### Scenario: Timestamps al crear

- **WHEN** se crea una entidad
- **THEN** `created_at` y `updated_at` quedan establecidos con la fecha-hora de creación

#### Scenario: updated_at cambia al modificar

- **WHEN** se modifica y persiste una entidad existente
- **THEN** `updated_at` se actualiza a la fecha-hora de la modificación
- **AND** `created_at` permanece sin cambios

### Requirement: Campo deleted_at para borrado lógico

Toda entidad SHALL incluir un campo `deleted_at` de tipo fecha-hora nullable. Un valor nulo SHALL significar entidad activa; un valor no nulo SHALL significar entidad borrada lógicamente.

#### Scenario: Entidad activa por defecto

- **WHEN** se crea una entidad
- **THEN** su `deleted_at` es nulo (activa)
