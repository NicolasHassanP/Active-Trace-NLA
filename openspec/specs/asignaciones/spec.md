# asignaciones Specification

## Purpose
TBD - created by archiving change usuarios-y-asignaciones. Update Purpose after archive.
## Requirements
### Requirement: Asignación vincula usuario, rol y contexto académico

El sistema SHALL modelar una `Asignacion` que vincule un `Usuario` con un `rol` (PROFESOR, TUTOR, COORDINADOR, NEXO, ADMIN, FINANZAS) dentro de un contexto académico opcional (`materia_id`, `carrera_id`, `cohorte_id`, `comisiones`). Los identificadores de contexto SHALL admitir nulo cuando el rol es de alcance global del tenant.

#### Scenario: Asignación con contexto de materia
- **WHEN** se asigna a un usuario el rol PROFESOR sobre una materia, carrera y cohorte
- **THEN** la asignación se crea vinculando usuario, rol y ese contexto

#### Scenario: Asignación de rol global sin materia
- **WHEN** se asigna a un usuario un rol de alcance de tenant sin materia
- **THEN** la asignación se crea con `materia_id` nulo

### Requirement: Multi-rol por usuario

El sistema SHALL permitir que un mismo usuario tenga múltiples asignaciones con distintos roles, contextos y períodos simultáneamente.

#### Scenario: Usuario con dos roles activos
- **WHEN** un usuario recibe una asignación PROFESOR y otra COORDINADOR vigentes
- **THEN** ambas asignaciones coexisten y son consultables

### Requirement: Vigencia temporal y estado derivado

Cada `Asignacion` SHALL tener una ventana de vigencia `desde` (obligatoria) y `hasta` (nullable; nulo = abierta). El sistema SHALL derivar `estado_vigencia` a partir de las fechas y NO SHALL almacenarlo. Una asignación SHALL considerarse **vigente** cuando `desde <= hoy` Y (`hasta` es nulo O `hasta >= hoy`); en caso contrario, **vencida**.

#### Scenario: Asignación vigente
- **WHEN** `desde` es anterior o igual a hoy y `hasta` es nulo o futuro
- **THEN** `estado_vigencia` se deriva como Vigente

#### Scenario: Asignación vencida
- **WHEN** `hasta` es anterior a hoy
- **THEN** `estado_vigencia` se deriva como Vencida

#### Scenario: Asignación aún no iniciada
- **WHEN** `desde` es posterior a hoy
- **THEN** `estado_vigencia` se deriva como Vencida (no vigente todavía)

### Requirement: Asignación vencida no otorga permisos pero se conserva

El sistema SHALL ejercer los permisos de una asignación únicamente mientras esté vigente. Una asignación vencida SHALL NO otorgar acceso, pero SHALL conservarse en el histórico (nunca se borra al vencer) para auditoría y clonado entre períodos.

#### Scenario: Vencida no autoriza
- **WHEN** se evalúan los permisos efectivos de un usuario cuya única asignación está vencida
- **THEN** esa asignación no aporta permisos

#### Scenario: Vencida permanece en el histórico
- **WHEN** una asignación pasa de vigente a vencida por el paso del tiempo
- **THEN** el registro permanece almacenado y consultable como histórico

### Requirement: Jerarquía de responsable

El sistema SHALL modelar la jerarquía docente mediante `responsable_id`, una referencia (self-FK) al `Usuario` que supervisa al asignado. SHALL admitir nulo (sin responsable).

#### Scenario: Asignación con responsable
- **WHEN** se crea una asignación indicando un usuario responsable del mismo tenant
- **THEN** la asignación queda vinculada a ese responsable

#### Scenario: Responsable de otro tenant es rechazado
- **WHEN** se intenta indicar como responsable un usuario de otro tenant
- **THEN** la operación es rechazada

### Requirement: CRUD de asignaciones protegido por equipos:asignar

El sistema SHALL exponer la creación, consulta, edición y baja de asignaciones bajo `/api/v1/asignaciones`, exigiendo el permiso `equipos:asignar`. Sin ese permiso, el sistema SHALL responder 403 (fail-closed). El `tenant_id` SHALL derivarse del JWT verificado, nunca del body.

#### Scenario: Acceso sin permiso es denegado
- **WHEN** un usuario sin `equipos:asignar` invoca una operación de asignaciones
- **THEN** el sistema responde 403 sin ejecutar la operación

#### Scenario: Gestión con permiso
- **WHEN** un COORDINADOR o ADMIN con `equipos:asignar` crea o edita una asignación
- **THEN** la operación se ejecuta en el tenant del JWT

### Requirement: Aislamiento multi-tenant de asignaciones

El sistema SHALL impedir que un usuario de un tenant lea o modifique asignaciones de otro tenant, y SHALL impedir que una asignación referencie usuario o contexto de otro tenant.

#### Scenario: Listado no cruza tenants
- **WHEN** un COORDINADOR del tenant A lista asignaciones
- **THEN** la respuesta nunca incluye asignaciones del tenant B

