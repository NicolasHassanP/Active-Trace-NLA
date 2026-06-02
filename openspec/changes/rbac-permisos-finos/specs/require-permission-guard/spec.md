## ADDED Requirements

### Requirement: Guard require_permission montado sobre la identidad del JWT

El sistema SHALL proveer una dependency factory `require_permission("modulo:accion")` que se monta sobre `get_current_user`. El guard SHALL derivar identidad, tenant y roles **exclusivamente** del `CurrentUser` resuelto del JWT verificado, NUNCA de un parámetro de URL, body o header de la petición. El guard SHALL resolver los permisos efectivos del usuario mediante el servicio de autorización (no accede a la DB directamente).

#### Scenario: El guard usa la identidad del token
- **WHEN** un endpoint declara `require_permission("calificaciones:importar")` y recibe una petición autenticada
- **THEN** el guard evalúa el permiso contra los roles del JWT verificado, sin leer ningún identificador de la petición

#### Scenario: Sin sesión autenticada
- **WHEN** una petición a un endpoint protegido por `require_permission` no presenta un JWT válido
- **THEN** el sistema responde `401` (la verificación de identidad de `get_current_user` ocurre antes del chequeo de permiso)

### Requirement: Fail-closed — sin permiso explícito el acceso es 403

El sistema SHALL denegar con `403` toda petición a un endpoint protegido cuyo usuario autenticado no tenga el permiso requerido en su conjunto efectivo. No SHALL existir flag de superusuario ni atajo que conceda acceso sin el permiso explícito.

#### Scenario: Usuario sin el permiso requerido
- **WHEN** un ALUMNO accede a un endpoint protegido por `require_permission("calificaciones:importar")`
- **THEN** el sistema responde `403`

#### Scenario: Usuario con el permiso requerido
- **WHEN** un COORDINADOR accede al mismo endpoint protegido por `require_permission("calificaciones:importar")`
- **THEN** el guard permite la ejecución del endpoint

#### Scenario: Tenant sin catálogo deniega por defecto
- **WHEN** un usuario de un tenant sin catálogo sembrado accede a cualquier endpoint protegido
- **THEN** el sistema responde `403` (conjunto de permisos efectivos vacío)

### Requirement: El guard expone el alcance del permiso concedido

El sistema SHALL, cuando el permiso es concedido, exponer al endpoint el alcance efectivo del permiso (`global` o `propio`) como parte del resultado del guard, de modo que el endpoint consumidor pueda aplicar el filtro row-level "sólo mis datos" cuando el alcance es `propio`. C-04 define este contrato; la aplicación del filtro corresponde a cada endpoint consumidor.

#### Scenario: El guard devuelve el alcance propio
- **WHEN** un PROFESOR (con `atrasados:ver` scope propio) pasa el guard `require_permission("atrasados:ver")`
- **THEN** el guard concede el acceso y expone al endpoint que el alcance es propio

#### Scenario: El guard devuelve el alcance global
- **WHEN** un COORDINADOR (con `atrasados:ver` scope global) pasa el mismo guard
- **THEN** el guard concede el acceso y expone al endpoint que el alcance es global
