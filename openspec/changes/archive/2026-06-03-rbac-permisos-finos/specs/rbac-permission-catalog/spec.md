## ADDED Requirements

### Requirement: Catálogo administrable de roles, permisos y su matriz como datos

El sistema SHALL persistir el catálogo de autorización como datos en tres tablas tenant-scoped: `rol`, `permiso` (con código `modulo:accion`) y la matriz de unión `rol_permiso`. La matriz de capacidades por rol NO SHALL estar hardcodeada en código; SHALL ser administrable por tenant. Cada tabla SHALL llevar `tenant_id`, timestamps y `deleted_at` (soft delete), heredando el `TenantScopedBase` del proyecto.

#### Scenario: Las tres tablas existen tras la migración
- **WHEN** se aplica la migración `003_create_rbac_tables`
- **THEN** existen las tablas `rol`, `permiso` y `rol_permiso`, cada una con `tenant_id`, `id` UUID, `created_at`, `updated_at` y `deleted_at`

#### Scenario: Un permiso se expresa como modulo:accion
- **WHEN** se inserta un `permiso` con `codigo = "calificaciones:importar"`
- **THEN** el registro persiste `modulo = "calificaciones"` y `accion = "importar"` junto al código completo

#### Scenario: El catálogo es administrable (no hardcodeado)
- **WHEN** se da de alta un nuevo `rol` con un conjunto de `rol_permiso` para un tenant
- **THEN** ese rol y sus permisos quedan disponibles para la resolución de permisos sin requerir cambios de código

### Requirement: Unicidad y aislamiento por tenant del catálogo

El sistema SHALL garantizar unicidad por tenant: `rol.nombre` único por `(tenant_id, nombre)`, `permiso.codigo` único por `(tenant_id, codigo)` y `rol_permiso` único por `(tenant_id, rol_id, permiso_id)`. El mismo nombre de rol o código de permiso SHALL poder coexistir en tenants distintos sin colisionar. Las consultas al catálogo SHALL filtrar por `tenant_id` por defecto.

#### Scenario: Mismo rol en dos tenants no colisiona
- **WHEN** el tenant A y el tenant B crean cada uno un rol "PROFESOR"
- **THEN** ambos registros coexisten, cada uno scopeado a su tenant

#### Scenario: Rol duplicado dentro del mismo tenant es rechazado
- **WHEN** un tenant intenta crear un segundo rol activo con `nombre = "PROFESOR"`
- **THEN** la operación falla por violación de unicidad `(tenant_id, nombre)`

#### Scenario: Una consulta del catálogo de un tenant no devuelve filas de otro
- **WHEN** se listan los roles scopeados al tenant A
- **THEN** el resultado no incluye ningún rol del tenant B

### Requirement: Seed reproducible de la matriz base del dominio

El sistema SHALL sembrar, por cada tenant existente al momento de la migración, los roles del dominio (ALUMNO, TUTOR, PROFESOR, COORDINADOR, NEXO, ADMIN, FINANZAS) y sus permisos según la matriz de capacidades de la base de conocimiento (§3.3). El seed SHALL ser idempotente: ejecutarlo sobre una base con datos parciales no SHALL duplicar filas ni fallar. Los nombres de rol sembrados SHALL coincidir exactamente con los valores que el JWT transporta en el claim `roles`.

#### Scenario: Roles del dominio quedan sembrados por tenant
- **WHEN** se aplica la migración sobre un tenant existente
- **THEN** ese tenant tiene los roles ALUMNO, TUTOR, PROFESOR, COORDINADOR, NEXO, ADMIN y FINANZAS

#### Scenario: La matriz de capacidades queda sembrada como rol_permiso
- **WHEN** se aplica la migración
- **THEN** el rol COORDINADOR tiene `comunicacion:aprobar` con scope global, y el rol PROFESOR tiene `calificaciones:importar` con scope propio

#### Scenario: El seed es idempotente
- **WHEN** la rutina de seed se ejecuta dos veces sobre el mismo tenant
- **THEN** no se crean filas duplicadas en `rol`, `permiso` ni `rol_permiso`
