## ADDED Requirements

### Requirement: ABM de carreras tenant-scoped

El sistema SHALL permitir crear, listar, editar y dar de baja lógica carreras, donde cada carrera pertenece a exactamente un tenant y se identifica por un código corto y un nombre. El `tenant_id` de la carrera SHALL derivarse de la sesión del usuario (JWT), nunca de la entrada de la petición.

#### Scenario: Crear una carrera

- **WHEN** un usuario con el permiso `estructura:gestionar` crea una carrera con un código y un nombre
- **THEN** el sistema persiste la carrera con `tenant_id` igual al del usuario, estado `Activa` por defecto, y la devuelve con su identificador

#### Scenario: Listar carreras solo del propio tenant

- **WHEN** un usuario del tenant A lista las carreras
- **THEN** el sistema devuelve únicamente carreras cuyo `tenant_id` es el del tenant A, y nunca carreras del tenant B

#### Scenario: Baja lógica de una carrera

- **WHEN** un usuario con permiso da de baja una carrera existente
- **THEN** el sistema marca la carrera como borrada lógicamente (no la elimina físicamente) y deja de devolverla en los listados por defecto

### Requirement: Unicidad de código de carrera por tenant

El sistema SHALL garantizar que el par (tenant, código) de carrera sea único entre las carreras no borradas del tenant. Dar de baja una carrera SHALL liberar su código para reutilización.

#### Scenario: Rechazo de código duplicado en el mismo tenant

- **WHEN** un usuario intenta crear una carrera con un código que ya existe (no borrado) en su tenant
- **THEN** el sistema rechaza la operación con un error de conflicto y no crea la carrera

#### Scenario: Mismo código permitido en tenants distintos

- **WHEN** un usuario del tenant A crea una carrera con código `TUPAD` y un usuario del tenant B crea otra carrera con código `TUPAD`
- **THEN** el sistema acepta ambas, porque la unicidad se evalúa por tenant

#### Scenario: Reutilización de código tras baja lógica

- **WHEN** una carrera con código `TUPAD` fue dada de baja lógicamente y un usuario crea una nueva carrera con código `TUPAD` en el mismo tenant
- **THEN** el sistema acepta la nueva carrera

### Requirement: Estado activa/inactiva de la carrera

El sistema SHALL permitir cambiar el estado de una carrera entre `Activa` e `Inactiva`. Una carrera `Inactiva` no admite nuevas inscripciones ni la apertura de nuevas cohortes abiertas. El sistema SHALL bloquear la desactivación de una carrera si esta tiene cohortes abiertas (estado `Activa` y `vig_hasta IS NULL`), respondiendo con un error de conflicto que instruya al ADMIN a cerrar las cohortes primero.

#### Scenario: Inactivar una carrera sin cohortes abiertas

- **WHEN** un usuario con permiso cambia el estado de una carrera a `Inactiva` y esa carrera no tiene cohortes abiertas (ninguna cohorte con estado `Activa` y `vig_hasta` nulo)
- **THEN** el sistema persiste el nuevo estado y la carrera queda marcada como inactiva

#### Scenario: Bloqueo de inactivación con cohortes abiertas

- **WHEN** un usuario con permiso intenta cambiar el estado de una carrera a `Inactiva` y esa carrera tiene al menos una cohorte abierta (estado `Activa` y `vig_hasta` nulo)
- **THEN** el sistema rechaza la operación con un error de conflicto (HTTP 409) indicando que deben cerrarse las cohortes abiertas antes de inactivar la carrera, y la carrera permanece en estado `Activa`

### Requirement: Gestión de carreras protegida por permiso

Toda operación de ABM sobre carreras SHALL requerir el permiso `estructura:gestionar`. Sin ese permiso el sistema SHALL responder con denegación de acceso (fail-closed).

#### Scenario: Acceso denegado sin permiso

- **WHEN** un usuario sin el permiso `estructura:gestionar` intenta crear, editar o dar de baja una carrera
- **THEN** el sistema responde con 403 y no realiza la operación
