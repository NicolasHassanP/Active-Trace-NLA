## Requirements

### Requirement: Campos obligatorios de una cohorte

El sistema SHALL exigir `nombre`, `anio` (entero) y `vig_desde` (fecha de inicio de vigencia) al crear una cohorte. El campo `vig_hasta` (fecha de fin de vigencia) SHALL ser opcional; cuando se omite (NULL) la cohorte se considera abierta. Omitir `anio` o `vig_desde` SHALL ser rechazado como error de validación.

#### Scenario: Rechazo de cohorte sin anio

- **WHEN** un usuario intenta crear una cohorte sin indicar el campo `anio`
- **THEN** el sistema rechaza la operación con un error de validación indicando que el año es obligatorio

#### Scenario: Rechazo de cohorte sin vig_desde

- **WHEN** un usuario intenta crear una cohorte sin indicar el campo `vig_desde`
- **THEN** el sistema rechaza la operación con un error de validación indicando que la fecha de inicio de vigencia es obligatoria

#### Scenario: Cohorte abierta sin vig_hasta

- **WHEN** un usuario crea una cohorte con `nombre`, `anio` y `vig_desde` pero sin indicar `vig_hasta`
- **THEN** el sistema acepta la operación y persiste la cohorte con `vig_hasta` nulo (cohorte abierta)

### Requirement: ABM de cohortes tenant-scoped pertenecientes a una carrera

El sistema SHALL permitir crear, listar, editar y dar de baja lógica cohortes. Cada cohorte SHALL pertenecer a exactamente un tenant y a exactamente una carrera de ese tenant (referencia obligatoria). El `tenant_id` SHALL derivarse de la sesión, nunca de la entrada.

#### Scenario: Crear una cohorte para una carrera

- **WHEN** un usuario con permiso `estructura:gestionar` crea una cohorte indicando una carrera, un nombre, un año (`anio`) y una fecha de inicio (`vig_desde`)
- **THEN** el sistema persiste la cohorte asociada a esa carrera, con `tenant_id` del usuario y estado `Activa` por defecto

#### Scenario: Rechazo de cohorte sin carrera

- **WHEN** un usuario intenta crear una cohorte sin indicar la carrera a la que pertenece
- **THEN** el sistema rechaza la operación porque la carrera es obligatoria

#### Scenario: Rechazo de carrera de otro tenant

- **WHEN** un usuario del tenant A intenta crear una cohorte referenciando una carrera que pertenece al tenant B
- **THEN** el sistema rechaza la operación y no crea la cohorte

#### Scenario: Listar cohortes solo del propio tenant

- **WHEN** un usuario del tenant A lista las cohortes
- **THEN** el sistema devuelve únicamente cohortes cuyo `tenant_id` es el del tenant A, y nunca cohortes del tenant B

#### Scenario: Baja lógica de una cohorte

- **WHEN** un usuario con permiso da de baja una cohorte existente
- **THEN** el sistema la marca como borrada lógicamente y deja de devolverla en los listados por defecto

### Requirement: Unicidad de cohorte por carrera dentro del tenant

El sistema SHALL garantizar que el trío (tenant, carrera, nombre) de cohorte sea único entre las cohortes no borradas. Un mismo nombre de cohorte SHALL poder existir en carreras distintas del mismo tenant.

#### Scenario: Rechazo de nombre duplicado en la misma carrera

- **WHEN** un usuario intenta crear una cohorte con un nombre que ya existe (no borrado) para la misma carrera del tenant
- **THEN** el sistema rechaza la operación con un error de conflicto

#### Scenario: Mismo nombre permitido en carreras distintas

- **WHEN** un usuario crea una cohorte `AGO-2025` en la carrera X y otra cohorte `AGO-2025` en la carrera Y del mismo tenant
- **THEN** el sistema acepta ambas, porque la unicidad incluye la carrera

### Requirement: Una carrera inactiva no admite cohortes abiertas

El sistema SHALL impedir crear o dejar abierta una cohorte (estado `Activa` y sin fecha de fin de vigencia) cuando su carrera está `Inactiva`.

#### Scenario: Rechazo de cohorte abierta bajo carrera inactiva

- **WHEN** un usuario intenta crear una cohorte abierta (sin fecha de fin de vigencia, estado activa) cuya carrera está `Inactiva`
- **THEN** el sistema rechaza la operación con un error de regla de negocio

#### Scenario: Cohorte permitida bajo carrera activa

- **WHEN** un usuario crea una cohorte abierta cuya carrera está `Activa`
- **THEN** el sistema acepta la operación

### Requirement: Gestión de cohortes protegida por permiso

Toda operación de ABM sobre cohortes SHALL requerir el permiso `estructura:gestionar`. Sin ese permiso el sistema SHALL responder con denegación de acceso (fail-closed).

#### Scenario: Acceso denegado sin permiso

- **WHEN** un usuario sin el permiso `estructura:gestionar` intenta crear, editar o dar de baja una cohorte
- **THEN** el sistema responde con 403 y no realiza la operación
