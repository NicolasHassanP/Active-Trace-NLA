## ADDED Requirements

### Requirement: Crear y asignar una tarea a otro docente (F8.2, FL-05)
El sistema SHALL permitir a un usuario con `tareas:gestionar` (roles COORDINADOR, ADMIN) crear una `Tarea` para otro docente, con `asignado_a` (Usuario que resuelve), `descripcion`, `materia_id` opcional, y el par opcional `contexto_id`/`contexto_tipo`. El estado inicial de toda tarea creada SHALL ser `Pendiente`. El `tenant_id` y el `asignado_por` SHALL resolverse desde la sesión autenticada (JWT), NUNCA desde el body, la URL ni un header. Los bodies de request SHALL rechazar campos desconocidos (`extra='forbid'`) y NO SHALL aceptar ningún campo de identidad del actor (`tenant_id`, `asignado_por`, `autor_id`). La creación de una tarea SHALL registrarse en el log de auditoría con acción `TAREA_ASIGNAR`.

#### Scenario: COORDINADOR crea y asigna una tarea
- **WHEN** un COORDINADOR con `tareas:gestionar` crea una tarea con `asignado_a` válido y `descripcion`
- **THEN** la tarea se persiste bajo el tenant del actor con estado `Pendiente` y `asignado_por` igual al actor autenticado
- **AND** se registra una entrada de auditoría con acción `TAREA_ASIGNAR`

#### Scenario: Usuario sin permiso no puede crear tareas
- **WHEN** un usuario sin `tareas:gestionar` intenta crear una tarea
- **THEN** el sistema retorna HTTP 403 y no crea ninguna tarea

#### Scenario: La identidad viene de la sesión, no del body
- **WHEN** el body de creación contiene un `tenant_id` o `asignado_por` distinto del usuario autenticado
- **THEN** la tarea se crea bajo el tenant del usuario autenticado, `asignado_por` es el actor de la sesión, y los valores del body se ignoran o se rechazan como campos desconocidos

### Requirement: Coherencia del contexto polimórfico (contexto_id + contexto_tipo)
El sistema SHALL tratar `contexto_id` y `contexto_tipo` como una referencia blanda polimórfica opcional: ambos SHALL ser null o ambos SHALL estar presentes. El sistema SHALL rechazar un request donde sólo uno de los dos esté presente. `contexto_id` NO SHALL tener FK física; `contexto_tipo` es un discriminador textual (por ejemplo `"Encuentro"`, `"Coloquio"`, `"Alumno"`). `materia_id` es una FK explícita aparte a `materia`, opcional e independiente del par de contexto.

#### Scenario: contexto_id sin contexto_tipo es rechazado
- **WHEN** se crea una tarea con `contexto_id` presente y `contexto_tipo` null
- **THEN** el sistema retorna HTTP 422 y no crea ninguna tarea

#### Scenario: contexto_tipo sin contexto_id es rechazado
- **WHEN** se crea una tarea con `contexto_tipo` presente y `contexto_id` null
- **THEN** el sistema retorna HTTP 422 y no crea ninguna tarea

#### Scenario: Ambos campos de contexto presentes es aceptado
- **WHEN** se crea una tarea con `contexto_id` y `contexto_tipo` ambos presentes
- **THEN** la tarea se persiste con la referencia de contexto registrada

#### Scenario: Ambos campos de contexto ausentes es aceptado
- **WHEN** se crea una tarea sin `contexto_id` ni `contexto_tipo`
- **THEN** la tarea se persiste con `contexto_id` y `contexto_tipo` en null

### Requirement: Mis tareas — self-service del asignado (F8.1)
El sistema SHALL permitir a cualquier usuario autenticado (sin requerir `tareas:gestionar`) listar las tareas donde es `asignado_a`, vía `GET /tareas/mias`. La consulta SHALL estar acotada al tenant de la sesión y SHALL excluir tareas con `deleted_at` no nulo. El usuario SHALL ver únicamente sus propias tareas asignadas, nunca tareas de terceros ni de otros tenants.

#### Scenario: El asignado lista sus tareas sin permiso de gestión
- **WHEN** un docente sin `tareas:gestionar` consulta `GET /tareas/mias`
- **THEN** el sistema retorna únicamente las tareas donde el docente es `asignado_a`, dentro de su tenant

#### Scenario: Mis tareas no expone tareas de otros usuarios
- **WHEN** existen tareas asignadas a otros docentes del mismo tenant
- **THEN** `GET /tareas/mias` no las incluye en la respuesta del docente actual

### Requirement: Cambio de estado según la matriz de transiciones (workflow FL-05)
El sistema SHALL validar todo cambio de estado contra una matriz de transiciones legales aplicada en la capa de servicio. Transiciones legales: `Pendiente → {EnProgreso, Resuelta, Cancelada}`; `EnProgreso → {Pendiente, Resuelta, Cancelada}`; `Resuelta → {EnProgreso}` (reapertura, FL-05 §7); `Cancelada` es terminal-final (sin transiciones de salida). Una transición fuera de la matriz SHALL retornar HTTP 409. Una transición que mantiene el mismo estado (no-op) SHALL retornar HTTP 409. Todo cambio de estado válido SHALL registrarse en auditoría con acción `TAREA_CAMBIAR_ESTADO`. El `asignado_a` SHALL poder cambiar el estado de su propia tarea sin `tareas:gestionar`; un usuario con `tareas:gestionar` SHALL poder cambiar el estado de cualquier tarea del tenant.

#### Scenario: Transición legal Pendiente a EnProgreso
- **WHEN** el `asignado_a` cambia el estado de su tarea de `Pendiente` a `EnProgreso`
- **THEN** la tarea queda en `EnProgreso` y se registra una entrada de auditoría `TAREA_CAMBIAR_ESTADO`

#### Scenario: Reapertura legal Resuelta a EnProgreso
- **WHEN** un usuario con `tareas:gestionar` cambia el estado de una tarea de `Resuelta` a `EnProgreso`
- **THEN** la tarea queda en `EnProgreso` (reapertura) y se audita el cambio

#### Scenario: Transición ilegal es rechazada con 409
- **WHEN** se intenta cambiar el estado de una tarea de `Resuelta` a `Pendiente`
- **THEN** el sistema retorna HTTP 409 y el estado de la tarea no cambia

#### Scenario: Cancelada es terminal-final
- **WHEN** se intenta cambiar el estado de una tarea `Cancelada` a cualquier otro estado
- **THEN** el sistema retorna HTTP 409 y la tarea permanece `Cancelada`

#### Scenario: Transición no-op es rechazada con 409
- **WHEN** se intenta cambiar el estado de una tarea al mismo estado en que ya se encuentra
- **THEN** el sistema retorna HTTP 409 y no se registra cambio

#### Scenario: Un docente no puede cambiar el estado de una tarea ajena
- **WHEN** un docente sin `tareas:gestionar` intenta cambiar el estado de una tarea donde no es `asignado_a`
- **THEN** el sistema retorna HTTP 403 y el estado no cambia

### Requirement: Delegación de una tarea con trazabilidad (F8.2, FL-05)
El sistema SHALL permitir a un usuario con `tareas:gestionar` delegar una tarea existente reasignándola a otro docente vía `POST /tareas/{id}/delegar`. La delegación SHALL actualizar `asignado_a` al nuevo docente y SHALL sobrescribir `asignado_por` con el actor que delega. La delegación SHALL emitir una entrada de auditoría con acción `TAREA_DELEGAR` (con before/after de los asignados) y SHALL insertar un `ComentarioTarea` de sistema (`autor_id` = actor) con texto generado que refleje la delegación. La operación SHALL estar acotada al tenant del actor.

#### Scenario: Delegación reasigna y deja trazabilidad
- **WHEN** un usuario con `tareas:gestionar` delega una tarea a otro docente
- **THEN** `asignado_a` pasa a ser el nuevo docente y `asignado_por` pasa a ser el actor que delega
- **AND** se registra una entrada de auditoría `TAREA_DELEGAR`
- **AND** se inserta un comentario de sistema en el hilo de la tarea reflejando la delegación

#### Scenario: Usuario sin permiso no puede delegar
- **WHEN** un usuario sin `tareas:gestionar` intenta delegar una tarea
- **THEN** el sistema retorna HTTP 403 y la asignación no cambia

#### Scenario: No se puede delegar una tarea de otro tenant
- **WHEN** un usuario intenta delegar una tarea que pertenece a un tenant distinto
- **THEN** el sistema retorna HTTP 404 y la tarea no cambia

### Requirement: Hilo de comentarios por tarea
El sistema SHALL permitir agregar comentarios de texto a una tarea (`POST /tareas/{id}/comentarios`) y listar el hilo de comentarios (`GET /tareas/{id}/comentarios`), ambos acotados al tenant de la sesión y excluyendo comentarios con `deleted_at` no nulo. El `autor_id` y el `tenant_id` SHALL resolverse desde la sesión, NUNCA desde el body. El acceso a comentar y listar SHALL permitirse sólo a quien sea `asignado_a` o `asignado_por` de la tarea, o a quien tenga `tareas:gestionar`. Los comentarios son sólo texto (sin adjuntos). El sistema SHALL soportar comentarios de sistema generados por delegaciones.

#### Scenario: El asignado comenta su tarea
- **WHEN** el `asignado_a` de una tarea agrega un comentario de texto
- **THEN** el comentario se persiste con `autor_id` igual al actor de la sesión y aparece en el hilo

#### Scenario: Listado del hilo en orden cronológico
- **WHEN** un usuario con acceso lista los comentarios de una tarea con varios comentarios
- **THEN** el sistema retorna el hilo acotado al tenant, excluyendo comentarios soft-deleted

#### Scenario: Usuario sin relación ni permiso no puede ver el hilo
- **WHEN** un usuario que no es `asignado_a` ni `asignado_por` y carece de `tareas:gestionar` intenta listar los comentarios de una tarea
- **THEN** el sistema retorna HTTP 403 y no expone el hilo

#### Scenario: La identidad del autor viene de la sesión
- **WHEN** un body de comentario incluye un `autor_id` distinto del usuario autenticado
- **THEN** el comentario se crea con el `autor_id` del actor de la sesión y el valor del body se ignora o se rechaza como campo desconocido

### Requirement: Administración global de tareas con filtros (F8.3)
El sistema SHALL permitir a un usuario con `tareas:gestionar` listar todas las tareas del tenant vía `GET /tareas/admin`, con filtros opcionales por `asignado_a`, `asignado_por`, `materia_id`, `estado` y búsqueda libre `q` sobre `descripcion` mediante `ILIKE`. La consulta SHALL estar acotada al tenant de la sesión y SHALL excluir tareas con `deleted_at` no nulo. El sistema SHALL permitir el soft-delete de una tarea vía `DELETE /tareas/{id}` (requiere `tareas:gestionar`); el hard delete NO SHALL soportarse.

#### Scenario: Administración lista todas las tareas del tenant
- **WHEN** un usuario con `tareas:gestionar` consulta `GET /tareas/admin` sin filtros
- **THEN** el sistema retorna todas las tareas no eliminadas del tenant del actor

#### Scenario: Filtro combinado por estado y materia
- **WHEN** un usuario con `tareas:gestionar` consulta `GET /tareas/admin` filtrando por `estado=Pendiente` y un `materia_id`
- **THEN** el sistema retorna sólo las tareas del tenant que cumplen ambos filtros

#### Scenario: Búsqueda libre sobre descripción
- **WHEN** un usuario con `tareas:gestionar` consulta `GET /tareas/admin` con `q` que coincide parcialmente con la descripción de algunas tareas
- **THEN** el sistema retorna las tareas cuya `descripcion` coincide vía `ILIKE`, acotado al tenant

#### Scenario: Usuario sin permiso no accede a la administración global
- **WHEN** un usuario sin `tareas:gestionar` consulta `GET /tareas/admin`
- **THEN** el sistema retorna HTTP 403 y no expone tareas

#### Scenario: Soft-delete oculta la tarea de todos los listados
- **WHEN** un usuario con `tareas:gestionar` elimina una tarea
- **THEN** se setea `deleted_at` y la tarea deja de aparecer en `GET /tareas/admin` y en `GET /tareas/mias`

### Requirement: Aislamiento de tenant en tareas y comentarios
El sistema SHALL acotar toda operación sobre tareas y comentarios al `tenant_id` de la sesión autenticada. Una tarea o un comentario de otro tenant NUNCA SHALL ser visible ni accesible (lectura, cambio de estado, delegación, comentario o borrado) por un usuario de un tenant distinto.

#### Scenario: Detalle de tarea de otro tenant retorna 404
- **WHEN** un usuario intenta acceder al detalle de una tarea que pertenece a otro tenant
- **THEN** el sistema retorna HTTP 404 y no expone la tarea

#### Scenario: Cambio de estado sobre tarea de otro tenant retorna 404
- **WHEN** un usuario intenta cambiar el estado de una tarea de otro tenant
- **THEN** el sistema retorna HTTP 404 y el estado no cambia

#### Scenario: La administración global nunca cruza tenants
- **WHEN** un usuario con `tareas:gestionar` lista la administración global
- **THEN** el resultado contiene exclusivamente tareas de su propio tenant
