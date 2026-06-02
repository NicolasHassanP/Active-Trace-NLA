## ADDED Requirements

### Requirement: Endpoint de salud de la aplicación

El sistema SHALL exponer un endpoint `GET /health` que reporte el estado de liveness de la aplicación. La respuesta SHALL ser `200 OK` con un cuerpo JSON que incluya al menos un campo de estado de la app cuando la aplicación está en funcionamiento.

#### Scenario: La aplicación está viva

- **WHEN** un cliente envía `GET /health`
- **THEN** el sistema responde `200 OK`
- **AND** el cuerpo es JSON e incluye un campo de estado (p. ej. `"status": "ok"`)

### Requirement: Readiness de la base de datos en el health-check

El endpoint `GET /health` SHALL reportar el estado de readiness de la conexión a la base de datos. Cuando la base de datos es alcanzable, el campo correspondiente SHALL indicar disponibilidad; cuando no lo es, el endpoint SHALL reflejar el fallo sin tumbar el proceso.

#### Scenario: Base de datos alcanzable

- **WHEN** un cliente envía `GET /health` y la base de datos responde a una verificación de conexión
- **THEN** la respuesta incluye un campo de readiness de base de datos que indica que está disponible

#### Scenario: Base de datos inalcanzable

- **WHEN** un cliente envía `GET /health` y la verificación de conexión a la base de datos falla
- **THEN** el endpoint refleja la indisponibilidad de la base de datos en su respuesta
- **AND** el proceso de la aplicación no se cae por el fallo de la verificación
