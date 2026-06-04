## ADDED Requirements

### Requirement: Vista de mis equipos del usuario autenticado

El sistema SHALL exponer una vista de solo lectura que devuelva, para el usuario autenticado, todas sus asignaciones agrupadas, incluyendo materia, carrera, cohorte, rol, comisiones, ventana de vigencia y `estado_vigencia` derivado (RN-10). La identidad del usuario SHALL provenir exclusivamente del JWT verificado, nunca de un parámetro de la petición. La vista SHALL exigir el permiso `equipos:ver`; sin ese permiso el sistema SHALL responder 403 (fail-closed).

#### Scenario: Docente ve sus equipos
- **WHEN** un PROFESOR con `equipos:ver` solicita su vista de mis equipos
- **THEN** el sistema devuelve únicamente sus propias asignaciones del tenant del JWT, cada una con su `estado_vigencia` derivado

#### Scenario: Estado vigente y vencido derivado
- **WHEN** una asignación del usuario tiene `hasta` anterior a hoy y otra tiene `hasta` nulo
- **THEN** la primera se reporta como Vencida y la segunda como Vigente, sin almacenar el estado

#### Scenario: Acceso sin permiso es denegado
- **WHEN** un usuario sin `equipos:ver` solicita la vista de mis equipos
- **THEN** el sistema responde 403 sin ejecutar la consulta

#### Scenario: La vista no expone equipos de otro usuario
- **WHEN** el usuario A solicita su vista de mis equipos
- **THEN** la respuesta no incluye asignaciones cuyo `usuario_id` sea distinto de A

### Requirement: Consulta de equipo agrupado por contexto académico

El sistema SHALL permitir consultar las asignaciones de un equipo identificado por la tripleta `(materia_id, carrera_id, cohorte_id)`, devolviendo cada integrante con su docente, rol, comisiones, vigencia y `responsable_id`. La consulta SHALL admitir filtros opcionales por rol y por `responsable_id`. SHALL exigir `equipos:ver` y SHALL estar siempre limitada al tenant del JWT.

#### Scenario: Consulta de equipo de una materia
- **WHEN** un COORDINADOR con `equipos:ver` consulta el equipo de una `(materia, carrera, cohorte)`
- **THEN** el sistema devuelve todas las asignaciones activas de esa tripleta en el tenant del JWT

#### Scenario: Filtro por rol
- **WHEN** la consulta de equipo incluye un filtro de rol PROFESOR
- **THEN** la respuesta incluye solo las asignaciones con rol PROFESOR de ese equipo

#### Scenario: Consulta no cruza tenants
- **WHEN** un COORDINADOR del tenant A consulta un equipo
- **THEN** la respuesta nunca incluye asignaciones del tenant B

### Requirement: Asignación masiva de docentes a un equipo

El sistema SHALL permitir asignar múltiples docentes a una combinación `materia × carrera × cohorte × rol` en una sola operación, con una vigencia (`desde`, `hasta`) y comisiones comunes, y un `responsable_id` opcional común aplicado a todas las asignaciones del lote (RN-11). La operación SHALL exigir `equipos:asignar` y SHALL ser atómica: si alguna asignación es inválida, el sistema SHALL NO persistir ninguna. Todos los `usuario_id` y referencias de contexto SHALL pertenecer al tenant del JWT; cualquier referencia de otro tenant SHALL ser rechazada.

#### Scenario: Alta masiva exitosa
- **WHEN** un COORDINADOR con `equipos:asignar` asigna tres docentes a una `(materia, carrera, cohorte)` con rol y vigencia
- **THEN** el sistema crea las tres asignaciones en el tenant del JWT y devuelve el resumen del lote

#### Scenario: Atomicidad ante referencia inválida
- **WHEN** uno de los `usuario_id` del lote no existe en el tenant
- **THEN** el sistema rechaza la operación completa (422) y no persiste ninguna asignación del lote

#### Scenario: Responsable de otro tenant es rechazado
- **WHEN** el `responsable_id` del lote pertenece a otro tenant
- **THEN** la operación es rechazada y no se crea ninguna asignación

#### Scenario: Alta masiva sin permiso es denegada
- **WHEN** un usuario sin `equipos:asignar` invoca la asignación masiva
- **THEN** el sistema responde 403 sin crear asignaciones

### Requirement: Clonación de equipo entre cohortes

El sistema SHALL permitir clonar un equipo origen identificado por `(materia_id, carrera_id, cohorte_id)` hacia un destino `(materia_id, carrera_id, cohorte_id)`, duplicando las asignaciones vigentes del origen y reescribiendo sus fechas con la vigencia del destino (RN-12). La clonación SHALL omitir las asignaciones que ya existirían en el destino para el mismo usuario, rol y contexto, evitando duplicados, y SHALL devolver un resumen con la cantidad clonada y la cantidad omitida. SHALL exigir `equipos:asignar` y operar dentro del tenant del JWT.

#### Scenario: Clonación entre cohortes
- **WHEN** un COORDINADOR con `equipos:asignar` clona el equipo de una cohorte origen a una cohorte destino con nueva vigencia
- **THEN** el sistema crea en el destino una asignación por cada asignación vigente del origen con las fechas del destino

#### Scenario: Clonación omite duplicados
- **WHEN** el equipo destino ya tiene una asignación para un usuario, rol y contexto que también existe en el origen
- **THEN** esa asignación se omite y el resumen reporta la cantidad clonada y la omitida

#### Scenario: Clonación de equipo vacío
- **WHEN** el equipo origen no tiene asignaciones vigentes
- **THEN** el sistema no crea ninguna asignación y devuelve un resumen con cero clonadas

### Requirement: Modificación de vigencia general del equipo

El sistema SHALL permitir actualizar la ventana de vigencia (`desde`, `hasta`) de todas las asignaciones de un equipo identificado por `(materia_id, carrera_id, cohorte_id)` en una sola operación. La operación SHALL exigir `equipos:asignar`, SHALL aplicar el cambio solo a asignaciones del tenant del JWT y SHALL devolver la cantidad de asignaciones afectadas.

#### Scenario: Cambio de vigencia en bloque
- **WHEN** un COORDINADOR con `equipos:asignar` modifica la vigencia general de un equipo
- **THEN** todas las asignaciones activas de ese equipo quedan con la nueva `desde`/`hasta` y el sistema reporta cuántas se actualizaron

#### Scenario: Vigencia general sin permiso es denegada
- **WHEN** un usuario sin `equipos:asignar` intenta modificar la vigencia general
- **THEN** el sistema responde 403 sin modificar asignaciones

### Requirement: Exportación del equipo docente

El sistema SHALL permitir exportar un equipo identificado por `(materia_id, carrera_id, cohorte_id)` como un archivo descargable en formato CSV, incluyendo por cada asignación el docente, rol, materia, carrera, cohorte, comisiones, vigencia y `estado_vigencia` derivado. La exportación SHALL exigir `equipos:ver` y SHALL limitarse al tenant del JWT.

#### Scenario: Exportación de equipo
- **WHEN** un COORDINADOR con `equipos:ver` exporta un equipo
- **THEN** el sistema devuelve un archivo CSV con una fila por asignación activa del equipo en el tenant del JWT

#### Scenario: Exportación sin permiso es denegada
- **WHEN** un usuario sin `equipos:ver` solicita exportar un equipo
- **THEN** el sistema responde 403 sin generar el archivo

### Requirement: Auditoría de operaciones de equipo en bloque

El sistema SHALL registrar en el log de auditoría cada operación de equipo en bloque — asignación masiva, clonación y modificación de vigencia general — con el actor (derivado del JWT), el tenant, el contexto del equipo afectado y el resultado (cantidades). Estas acciones SHALL usar las claves de catálogo `EQUIPOS_ASIGNACION_MASIVA`, `EQUIPOS_CLONAR` y `EQUIPOS_VIGENCIA_GENERAL`.

#### Scenario: Asignación masiva auditada
- **WHEN** se ejecuta una asignación masiva exitosa
- **THEN** se registra un evento de auditoría `EQUIPOS_ASIGNACION_MASIVA` con el actor del JWT, el tenant y la cantidad creada

#### Scenario: Clonación auditada
- **WHEN** se ejecuta una clonación de equipo
- **THEN** se registra un evento de auditoría `EQUIPOS_CLONAR` con el actor del JWT, el equipo origen y destino y las cantidades clonada y omitida
