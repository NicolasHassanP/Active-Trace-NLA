## ADDED Requirements

### Requirement: Lectura de auditoría protegida por permiso

El sistema SHALL exponer la lectura de eventos de auditoría únicamente a usuarios con el permiso `auditoria:ver`. Las solicitudes sin ese permiso SHALL ser rechazadas con 403 (fail-closed).

#### Scenario: Usuario con permiso accede a la auditoría

- **WHEN** un usuario con el permiso `auditoria:ver` solicita la lista de eventos de auditoría
- **THEN** el sistema devuelve los eventos del tenant según su alcance

#### Scenario: Usuario sin permiso es rechazado

- **WHEN** un usuario sin el permiso `auditoria:ver` solicita la lista de eventos de auditoría
- **THEN** el sistema responde 403 y no devuelve ningún evento

### Requirement: Alcance row-level de la lectura de auditoría

La lectura de auditoría SHALL respetar el alcance del permiso del usuario: con alcance `propio`, el sistema SHALL devolver únicamente los eventos cuyo actor real es el usuario actual; con alcance global, SHALL devolver todos los eventos del tenant.

#### Scenario: Alcance propio devuelve solo eventos propios

- **WHEN** un usuario cuyo permiso `auditoria:ver` tiene alcance `propio` consulta la auditoría
- **THEN** el sistema devuelve solo los eventos cuyo actor real es ese usuario

#### Scenario: Alcance global devuelve todos los eventos del tenant

- **WHEN** un usuario cuyo permiso `auditoria:ver` tiene alcance global consulta la auditoría
- **THEN** el sistema devuelve todos los eventos del tenant, independientemente del actor

### Requirement: Respuesta de auditoría con contrato estricto

La respuesta de lectura de auditoría SHALL exponer los campos del evento mediante un esquema de salida que rechaza campos no declarados (`extra='forbid'`) y SHALL soportar paginación.

#### Scenario: Respuesta paginada con esquema estricto

- **WHEN** un usuario autorizado consulta la auditoría con parámetros de paginación
- **THEN** el sistema devuelve la página solicitada de eventos validada contra el esquema de salida, sin campos adicionales no declarados
