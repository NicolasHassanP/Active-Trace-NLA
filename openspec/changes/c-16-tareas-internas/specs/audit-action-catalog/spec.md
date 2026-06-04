## MODIFIED Requirements

### Requirement: Catálogo cerrado de códigos de acción

El sistema SHALL identificar cada acción auditable mediante un código del catálogo cerrado y versionado de la forma `MODULO_ACCION`. El sistema NO SHALL permitir registrar un evento de auditoría con un código de acción que no pertenezca al catálogo. El catálogo SHALL incluir los códigos del módulo de tareas internas: `TAREA_ASIGNAR` (creación/asignación de una tarea a un docente), `TAREA_DELEGAR` (reasignación de una tarea a otro docente) y `TAREA_CAMBIAR_ESTADO` (transición de estado de una tarea). El alta de un comentario en el hilo de una tarea NO SHALL auditarse por sí sola (alto volumen; el propio hilo es el registro).

#### Scenario: Código de acción válido

- **WHEN** se registra un evento con un código de acción que pertenece al catálogo (por ejemplo `IMPERSONACION_INICIO`)
- **THEN** el sistema acepta y persiste el evento

#### Scenario: Código de acción arbitrario rechazado

- **WHEN** se intenta registrar un evento con un código de acción que no pertenece al catálogo
- **THEN** el sistema rechaza la operación con un error de dominio y no persiste ningún evento

#### Scenario: Códigos de tareas internas pertenecen al catálogo

- **WHEN** se registra un evento con `TAREA_ASIGNAR`, `TAREA_DELEGAR` o `TAREA_CAMBIAR_ESTADO`
- **THEN** el sistema acepta y persiste el evento por tratarse de códigos válidos del catálogo
