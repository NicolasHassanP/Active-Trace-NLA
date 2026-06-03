## ADDED Requirements

### Requirement: Resolución server-side de permisos efectivos como unión de roles

El sistema SHALL resolver, server-side y por petición, el conjunto de permisos efectivos de un usuario como la **unión** de los permisos de todos sus roles, tomando los roles **exclusivamente** del claim `roles` del JWT verificado (vía `get_current_user`) y acotando la resolución al `tenant_id` del mismo token. La resolución SHALL hacerse en un servicio de autorización que accede al catálogo únicamente a través de un repository tenant-scoped. Los permisos NO SHALL leerse del token ni almacenarse en él.

#### Scenario: Unión de permisos de múltiples roles
- **WHEN** un usuario tiene en su claim `roles` los valores ["PROFESOR", "COORDINADOR"]
- **THEN** su conjunto efectivo incluye la unión de los permisos de PROFESOR y de COORDINADOR de su tenant

#### Scenario: Resolución acotada al tenant del token
- **WHEN** se resuelven los permisos de un usuario del tenant A
- **THEN** sólo se consideran los roles y permisos del tenant A, nunca los de otro tenant

#### Scenario: Identidad y roles provienen sólo del token
- **WHEN** una petición incluye un `roles` distinto en el body o en un header
- **THEN** la resolución ignora ese dato y usa únicamente el claim `roles` del JWT verificado

### Requirement: Roles desconocidos no conceden permisos (fail-closed)

El sistema SHALL ignorar cualquier nombre de rol presente en el claim `roles` que no exista como `Rol` activo del tenant. Un rol desconocido NO SHALL conceder permisos ni provocar un error que abra acceso; el resultado SHALL ser, por construcción, fail-closed.

#### Scenario: Nombre de rol inexistente se ignora
- **WHEN** el claim `roles` contiene "SUPERUSER", que no existe como Rol del tenant
- **THEN** ese nombre no aporta permisos al conjunto efectivo y la resolución no falla

#### Scenario: Usuario de un tenant sin catálogo sembrado
- **WHEN** un usuario pertenece a un tenant que aún no tiene catálogo de roles
- **THEN** su conjunto de permisos efectivos es vacío

### Requirement: Alcance propio vs. global por permiso efectivo

El sistema SHALL resolver, para cada permiso efectivo, su alcance (`global` o `propio`) tomando el alcance de la matriz `rol_permiso`. Cuando el mismo permiso proviene de varios roles con alcances distintos, el sistema SHALL otorgar el alcance **más permisivo** (`global` prevalece sobre `propio`).

#### Scenario: Alcance propio cuando sólo el rol propio lo concede
- **WHEN** un usuario es sólo PROFESOR y tiene `calificaciones:importar` con scope propio
- **THEN** su permiso efectivo `calificaciones:importar` tiene alcance propio

#### Scenario: Global prevalece sobre propio en la unión
- **WHEN** un usuario es PROFESOR (importar propio) y COORDINADOR (importar global)
- **THEN** su permiso efectivo `calificaciones:importar` tiene alcance global
