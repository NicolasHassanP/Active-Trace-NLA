## ADDED Requirements

### Requirement: Catálogo único de materias por tenant

El sistema SHALL mantener un catálogo único de materias por tenant, donde cada materia es la definición estática del catálogo (código y nombre) y pertenece a exactamente un tenant. El `tenant_id` SHALL derivarse de la sesión, nunca de la entrada. El sistema SHALL permitir crear, listar, editar y dar de baja lógica materias.

#### Scenario: Crear una materia en el catálogo

- **WHEN** un usuario con permiso `estructura:gestionar` crea una materia con un código y un nombre
- **THEN** el sistema persiste la materia con `tenant_id` del usuario, estado `Activa` por defecto, y la devuelve con su identificador

#### Scenario: Listar materias solo del propio tenant

- **WHEN** un usuario del tenant A lista las materias
- **THEN** el sistema devuelve únicamente materias cuyo `tenant_id` es el del tenant A, y nunca materias del tenant B

#### Scenario: Baja lógica de una materia

- **WHEN** un usuario con permiso da de baja una materia existente
- **THEN** el sistema la marca como borrada lógicamente (no la elimina físicamente) y deja de devolverla en los listados por defecto

#### Scenario: La materia no se asocia directamente a carrera ni cohorte

- **WHEN** se crea una materia en el catálogo
- **THEN** la materia no requiere ni admite una asociación directa a carrera o cohorte, porque esa relación se establece a través de la instancia de dictado en un módulo posterior

### Requirement: Unicidad de código de materia por tenant

El sistema SHALL garantizar que el par (tenant, código) de materia sea único entre las materias no borradas del tenant. Dar de baja una materia SHALL liberar su código para reutilización.

#### Scenario: Rechazo de código duplicado en el mismo tenant

- **WHEN** un usuario intenta crear una materia con un código que ya existe (no borrado) en su tenant
- **THEN** el sistema rechaza la operación con un error de conflicto y no crea la materia

#### Scenario: Mismo código permitido en tenants distintos

- **WHEN** un usuario del tenant A crea una materia con código `PROG_I` y un usuario del tenant B crea otra materia con código `PROG_I`
- **THEN** el sistema acepta ambas, porque la unicidad se evalúa por tenant

#### Scenario: Reutilización de código tras baja lógica

- **WHEN** una materia con código `PROG_I` fue dada de baja lógicamente y un usuario crea una nueva materia con código `PROG_I` en el mismo tenant
- **THEN** el sistema acepta la nueva materia

### Requirement: Estado activa/inactiva de la materia

El sistema SHALL permitir cambiar el estado de una materia entre `Activa` e `Inactiva`.

#### Scenario: Inactivar una materia

- **WHEN** un usuario con permiso cambia el estado de una materia a `Inactiva`
- **THEN** el sistema persiste el nuevo estado y la materia queda marcada como inactiva

### Requirement: Gestión del catálogo de materias protegida por permiso

Toda operación de ABM sobre materias SHALL requerir el permiso `estructura:gestionar`. Sin ese permiso el sistema SHALL responder con denegación de acceso (fail-closed).

#### Scenario: Acceso denegado sin permiso

- **WHEN** un usuario sin el permiso `estructura:gestionar` intenta crear, editar o dar de baja una materia
- **THEN** el sistema responde con 403 y no realiza la operación
