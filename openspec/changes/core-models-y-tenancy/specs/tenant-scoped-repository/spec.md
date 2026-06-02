## ADDED Requirements

### Requirement: Scope de tenant siempre activo en el repository

El sistema SHALL proveer un repository genérico para entidades de negocio cuyo scope de tenant esté SIEMPRE activo. El repository SHALL recibir el `tenant_id` en su construcción y conservarlo como estado interno. Toda operación de lectura SHALL filtrar por ese `tenant_id` de forma automática. El `tenant_id` NO SHALL pasarse como parámetro de cada método ni derivarse de ningún dato de la petición.

#### Scenario: Lectura filtrada por tenant

- **WHEN** un repository scoped al tenant A ejecuta una operación de listado o búsqueda
- **THEN** la consulta incluye automáticamente la condición `tenant_id = A`

#### Scenario: El scope se inyecta, no se deriva de la petición

- **WHEN** se construye el repository
- **THEN** el `tenant_id` se provee en la construcción y queda como estado del repository
- **AND** ningún método de lectura acepta `tenant_id` como parámetro

### Requirement: Aislamiento de datos entre tenants

El repository SHALL garantizar que un repository scoped a un tenant NUNCA devuelva datos de otro tenant. Una búsqueda por identidad de un registro perteneciente a otro tenant SHALL devolver un resultado vacío, no el registro ajeno.

#### Scenario: Un tenant no ve datos de otro tenant

- **WHEN** existen registros de los tenants A y B y se usa un repository scoped al tenant A para listar
- **THEN** sólo se devuelven registros del tenant A
- **AND** ningún registro del tenant B aparece en el resultado

#### Scenario: Búsqueda por id de registro ajeno

- **WHEN** un repository scoped al tenant A busca por `id` un registro que pertenece al tenant B
- **THEN** el resultado es vacío (no se devuelve el registro del tenant B)

### Requirement: Asignación de tenant al crear

Al crear o persistir una entidad a través del repository, el sistema SHALL fijar el `tenant_id` de la entidad desde el scope del repository, ignorando cualquier `tenant_id` provisto por el llamador.

#### Scenario: Tenant fijado desde el scope al crear

- **WHEN** se crea una entidad mediante un repository scoped al tenant A
- **THEN** la entidad persistida tiene `tenant_id = A` independientemente de cualquier valor de tenant entrante
