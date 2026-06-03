## ADDED Requirements

### Requirement: Catálogo cerrado de códigos de acción

El sistema SHALL identificar cada acción auditable mediante un código del catálogo cerrado y versionado de la forma `MODULO_ACCION`. El sistema NO SHALL permitir registrar un evento de auditoría con un código de acción que no pertenezca al catálogo.

#### Scenario: Código de acción válido

- **WHEN** se registra un evento con un código de acción que pertenece al catálogo (por ejemplo `IMPERSONACION_INICIO`)
- **THEN** el sistema acepta y persiste el evento

#### Scenario: Código de acción arbitrario rechazado

- **WHEN** se intenta registrar un evento con un código de acción que no pertenece al catálogo
- **THEN** el sistema rechaza la operación con un error de dominio y no persiste ningún evento

### Requirement: Versionado del catálogo de acciones

El catálogo de códigos de acción SHALL ser una constante del sistema, idéntica para todos los tenants, versionada junto con el código que emite los eventos. El catálogo NO SHALL ser administrable por tenant en tiempo de ejecución.

#### Scenario: El catálogo es uniforme entre tenants

- **WHEN** dos tenants distintos registran la misma acción
- **THEN** ambos usan el mismo conjunto de códigos válidos, sin divergencias por tenant
