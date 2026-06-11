## Purpose
Gestión de comunicaciones salientes multi-tenant: encolado masivo con plantillas, máquina de estados, aprobación humana opcional y worker asíncrono de despacho.
## Requirements
### Requirement: Modelo de comunicación saliente con destinatario cifrado
El sistema SHALL persistir cada comunicación saliente como un registro `Comunicacion` scoped al tenant, con el `destinatario` (email del alumno) cifrado en reposo con AES-256, y SHALL agrupar los envíos de una misma acción masiva bajo un `lote_id` común. El registro SHALL incluir asunto, cuerpo, estado, materia, usuario que lo originó (`enviado_por`), `enviado_at` (nullable) y detalle de error (nullable). El sistema SHALL aplicar soft delete; NUNCA borrado físico.

#### Scenario: El destinatario se persiste cifrado
- **WHEN** se crea una `Comunicacion` con destinatario `alumno@ejemplo.com`
- **THEN** el valor almacenado en la columna `destinatario` NO es texto plano legible
- **AND** al leer el registro vía el repositorio, el destinatario se descifra y devuelve `alumno@ejemplo.com`

#### Scenario: Los envíos masivos comparten lote_id
- **WHEN** se encola un envío masivo a 3 alumnos en una sola acción
- **THEN** los 3 registros `Comunicacion` comparten el mismo `lote_id`
- **AND** cada registro queda scoped al `tenant_id` de la sesión

#### Scenario: La representación textual nunca expone el destinatario
- **WHEN** se obtiene la representación (`repr`) de una `Comunicacion`
- **THEN** el destinatario en texto plano NO aparece en esa representación

### Requirement: Máquina de estados de la comunicación (RN-15)
El sistema SHALL gobernar el ciclo de vida de cada comunicación mediante una máquina de estados con los valores Pendiente, Enviando, Enviado, Error y Cancelado. El sistema SHALL permitir ÚNICAMENTE las transiciones `Pendiente → Enviando`, `Pendiente → Cancelado`, `Enviando → Enviado` y `Enviando → Error`. Los estados Enviado, Error y Cancelado SHALL ser TERMINALES: NO tienen transición de salida (en particular, NO hay reintento automático desde Error). Cualquier otra transición SHALL ser rechazada con un error de dominio sin modificar el estado.

#### Scenario: Transición válida Pendiente a Enviando
- **WHEN** una comunicación en estado `Pendiente` transiciona a `Enviando`
- **THEN** la transición se aplica y el estado pasa a `Enviando`

#### Scenario: Transición válida Enviando a Enviado
- **WHEN** una comunicación en estado `Enviando` transiciona a `Enviado`
- **THEN** la transición se aplica y se registra `enviado_at`

#### Scenario: Transición válida Pendiente a Cancelado
- **WHEN** una comunicación en estado `Pendiente` se cancela
- **THEN** el estado pasa a `Cancelado`

#### Scenario: Transición inválida es rechazada
- **WHEN** se intenta transicionar una comunicación en estado `Enviado` a `Enviando`
- **THEN** el sistema lanza un error de transición inválida
- **AND** el estado permanece en `Enviado`

#### Scenario: No se puede cancelar una comunicación ya enviada
- **WHEN** se intenta cancelar una comunicación en estado `Enviado`
- **THEN** el sistema lanza un error de transición inválida
- **AND** el estado permanece en `Enviado`

#### Scenario: Error es estado terminal (sin reintento)
- **WHEN** se intenta transicionar una comunicación en estado `Error` a `Enviando` o `Pendiente`
- **THEN** el sistema lanza un error de transición inválida
- **AND** el estado permanece en `Error`

### Requirement: Vista previa obligatoria antes de encolar (RN-16)
El sistema SHALL ofrecer una vista previa que renderice asunto y cuerpo (con las variables de plantilla ya sustituidas) tal como los recibirá el destinatario, sin escribir en la base de datos ni encolar nada. El endpoint de preview SHALL requerir el permiso `comunicacion:enviar`. La vista previa SHALL ser el punto de validación de la plantilla: si la plantilla contiene una variable que no puede resolverse, el preview SHALL rechazar la operación con un error (no renderiza parcial ni deja marcadores literales).

#### Scenario: Preview renderiza la plantilla sin encolar
- **WHEN** un usuario con permiso `comunicacion:enviar` solicita la vista previa de un mensaje con plantilla `Hola {nombre}` y variable `nombre=Ana`
- **THEN** la respuesta contiene el cuerpo renderizado `Hola Ana`
- **AND** NO se crea ningún registro `Comunicacion` en la base de datos

#### Scenario: Preview sin permiso es rechazado
- **WHEN** un usuario sin el permiso `comunicacion:enviar` solicita la vista previa
- **THEN** el sistema responde 403 (fail-closed)

#### Scenario: Preview rechaza una variable sin resolver
- **WHEN** un usuario con permiso `comunicacion:enviar` solicita la vista previa de un mensaje con plantilla `Hola {nombre}` y NO provee la variable `nombre`
- **THEN** el sistema rechaza la operación con un error
- **AND** NO devuelve un cuerpo con el marcador literal `{nombre}` ni con la variable sustituida por vacío

### Requirement: Render de plantillas con variables de sustitución
El sistema SHALL sustituir en el asunto y el cuerpo los marcadores de variable (por ejemplo `{nombre}`, `{materia}`) por los valores provistos para cada destinatario. Si la plantilla contiene un marcador para el que no se provee valor, el sistema SHALL fallar con un error de dominio (no SHALL dejar el marcador literal, no SHALL sustituir por cadena vacía, no SHALL renderizar parcialmente).

#### Scenario: Sustitución de múltiples variables
- **WHEN** se renderiza `Hola {nombre}, tu materia es {materia}` con `nombre=Ana` y `materia=Programación`
- **THEN** el resultado es `Hola Ana, tu materia es Programación`

#### Scenario: Texto sin variables se devuelve intacto
- **WHEN** se renderiza un texto sin marcadores de variable
- **THEN** el resultado es idéntico al texto de entrada

#### Scenario: Variable faltante falla fuerte
- **WHEN** se renderiza `Hola {nombre}` sin proveer la variable `nombre`
- **THEN** el sistema lanza un error de variable de plantilla faltante
- **AND** no produce ningún texto renderizado

### Requirement: Encolado masivo de comunicaciones (F3.2)
El sistema SHALL permitir a un usuario con permiso `comunicacion:enviar` encolar un envío masivo, creando un registro `Comunicacion` por destinatario en estado `Pendiente`, todos bajo un mismo `lote_id`, con asunto y cuerpo ya renderizados por destinatario. El sistema SHALL registrar un evento de auditoría `COMUNICACION_ENVIAR` al encolar. La identidad y el tenant SHALL derivarse exclusivamente de la sesión autenticada. Si la plantilla no puede resolverse para algún destinatario (variable faltante), el sistema SHALL rechazar la operación completa sin crear ningún registro del lote.

#### Scenario: Encolar crea registros Pendiente bajo un lote
- **WHEN** un usuario con permiso `comunicacion:enviar` encola un envío a 2 destinatarios
- **THEN** se crean 2 registros `Comunicacion` en estado `Pendiente`
- **AND** ambos comparten el mismo `lote_id`
- **AND** se registra un evento de auditoría `COMUNICACION_ENVIAR`

#### Scenario: Encolar sin permiso es rechazado
- **WHEN** un usuario sin permiso `comunicacion:enviar` intenta encolar un envío
- **THEN** el sistema responde 403 (fail-closed)
- **AND** no se crea ningún registro `Comunicacion`

#### Scenario: Encolar con una variable de plantilla sin resolver falla fuerte
- **WHEN** un usuario encola un envío cuya plantilla referencia una variable que no se provee para algún destinatario
- **THEN** el sistema rechaza la operación con un error
- **AND** no se crea ningún registro `Comunicacion` del lote

### Requirement: El PROFESOR solo comunica a destinatarios de sus comisiones (scope propio)
Cuando el usuario que encola tiene el permiso `comunicacion:enviar` con scope `propio` (rol PROFESOR), el sistema SHALL validar que cada destinatario pertenezca a una comisión donde ese usuario tiene una `Asignacion` vigente. Si algún destinatario cae fuera de ese scope, el sistema SHALL rechazar el encolado sin crear el lote.

#### Scenario: PROFESOR encola a destinatario de su comisión
- **WHEN** un PROFESOR con `comunicacion:enviar` scope `propio` encola a un destinatario de una comisión donde tiene `Asignacion` vigente
- **THEN** el encolado se realiza y se crean los registros `Comunicacion`

#### Scenario: PROFESOR no puede encolar fuera de sus comisiones
- **WHEN** un PROFESOR con scope `propio` intenta encolar a un destinatario de una comisión donde NO tiene `Asignacion` vigente
- **THEN** el sistema rechaza la operación
- **AND** no se crea ningún registro `Comunicacion` del lote

### Requirement: Aprobación humana de envíos masivos (RN-17, F3.3)
El sistema SHALL leer el flag `aprobacion_comunicacion_requerida` desde la configuración del tenant (tabla `tenant_config`, clave/valor por tenant). Cuando ese flag está activo para el tenant, el sistema SHALL mantener los mensajes masivos en estado `Pendiente` y NO habilitarlos para el worker hasta que un usuario con permiso `comunicacion:aprobar` los apruebe. Cuando el flag está inactivo (o no existe configuración para el tenant), los mensajes SHALL quedar elegibles para el worker directamente. La aprobación y la cancelación SHALL poder aplicarse al lote completo o a un destinatario individual. La cancelación SHALL transicionar el mensaje a `Cancelado`.

#### Scenario: Con aprobación requerida, el lote queda pendiente de aprobación
- **WHEN** el tenant tiene `aprobacion_comunicacion_requerida=true` en `tenant_config` y se encola un envío masivo
- **THEN** los mensajes quedan en `Pendiente` y NO son elegibles para el worker hasta ser aprobados

#### Scenario: Sin aprobación requerida, el lote es elegible directamente
- **WHEN** el tenant tiene `aprobacion_comunicacion_requerida=false` (o no tiene configuración) y se encola un envío masivo
- **THEN** los mensajes quedan elegibles para el worker sin paso de aprobación

#### Scenario: Aprobar un lote habilita sus mensajes para el worker
- **WHEN** un usuario con permiso `comunicacion:aprobar` aprueba un lote en estado `Pendiente`
- **THEN** los mensajes del lote quedan habilitados para despacho por el worker

#### Scenario: Cancelar un lote transiciona sus mensajes a Cancelado
- **WHEN** un usuario con permiso `comunicacion:aprobar` cancela un lote en estado `Pendiente`
- **THEN** todos los mensajes del lote pasan a estado `Cancelado`

#### Scenario: Aprobar o cancelar un destinatario individual
- **WHEN** un aprobador cancela un único destinatario de un lote `Pendiente`
- **THEN** solo ese mensaje pasa a `Cancelado`
- **AND** el resto del lote permanece en `Pendiente`

#### Scenario: Aprobar sin permiso es rechazado
- **WHEN** un usuario sin permiso `comunicacion:aprobar` intenta aprobar un lote
- **THEN** el sistema responde 403 (fail-closed)

### Requirement: Worker asíncrono de despacho
El sistema SHALL proveer un worker asíncrono que, mediante polling sobre la tabla `comunicacion`, consuma las comunicaciones habilitadas para despacho en estado `Pendiente`, las transicione a `Enviando`, intente el envío a través de la interfaz `EmailSender` y las transicione a `Enviado` (registrando `enviado_at`) o a `Error` (registrando el detalle del fallo). El worker SHALL ignorar los mensajes que requieren aprobación y aún no fueron aprobados. El estado `Error` SHALL ser terminal: el worker NUNCA SHALL reintentar automáticamente un mensaje en `Error`.

#### Scenario: El worker procesa un Pendiente habilitado hasta Enviado
- **WHEN** existe una comunicación habilitada para despacho en estado `Pendiente` y el envío es exitoso
- **THEN** el worker la transiciona `Pendiente → Enviando → Enviado`
- **AND** registra `enviado_at`

#### Scenario: El worker marca Error ante fallo de envío
- **WHEN** el worker procesa una comunicación y el envío falla
- **THEN** el worker la transiciona a `Error`
- **AND** registra el detalle del error

#### Scenario: El worker no toma mensajes pendientes de aprobación
- **WHEN** existe una comunicación masiva en `Pendiente` que requiere aprobación y aún no fue aprobada
- **THEN** el worker NO la transiciona a `Enviando`
- **AND** el mensaje permanece en `Pendiente`

#### Scenario: El worker no reintenta un mensaje en Error
- **WHEN** existe una comunicación en estado `Error` y el worker ejecuta un nuevo ciclo de polling
- **THEN** el worker NO la vuelve a procesar ni reintenta el envío
- **AND** el mensaje permanece en `Error`

### Requirement: Aislamiento multi-tenant de las comunicaciones
El sistema SHALL acotar todas las operaciones sobre comunicaciones al tenant de la sesión autenticada. Una comunicación de un tenant NUNCA SHALL ser visible, despachable ni modificable desde otro tenant.

#### Scenario: No se accede a comunicaciones de otro tenant
- **WHEN** un usuario del tenant A consulta el estado de un lote creado en el tenant B
- **THEN** el sistema no devuelve esos registros (como si no existieran para el tenant A)

### Requirement: Configuración por tenant (tenant_config)
El sistema SHALL proveer una tabla `tenant_config` de settings por tenant, modelada como clave/valor (un registro por `(tenant_id, clave)`), que aloja el flag `aprobacion_comunicacion_requerida` y queda extensible a futuros flags. La lectura de un valor SHALL estar acotada al tenant de la sesión y SHALL devolver un valor por defecto cuando no existe configuración para esa clave.

#### Scenario: Un valor por clave por tenant
- **WHEN** se intenta crear una segunda fila con la misma `clave` para el mismo `tenant_id`
- **THEN** el sistema rechaza el duplicado (restricción de unicidad `(tenant_id, clave)`)

#### Scenario: Lectura con valor por defecto cuando falta la configuración
- **WHEN** se lee `aprobacion_comunicacion_requerida` para un tenant que no tiene esa fila
- **THEN** el sistema devuelve el valor por defecto definido por la lectura (no falla)

#### Scenario: La configuración de un tenant no es visible para otro
- **WHEN** el tenant A tiene una fila de `tenant_config` y un usuario del tenant B lee la misma clave
- **THEN** el usuario del tenant B NO obtiene el valor del tenant A

### Requirement: Consulta del historial de envíos propios del remitente
El sistema SHALL permitir que cualquier usuario con permiso `comunicacion:enviar` consulte las comunicaciones donde él fue el remitente (`enviado_por == usuario.id`), scoped al tenant. La consulta SHALL ser solo lectura y NO SHALL modificar el estado de ninguna comunicación. El sistema SHALL excluir registros con soft delete aplicado (`deleted_at IS NOT NULL`).

#### Scenario: Remitente consulta su propio historial
- **WHEN** un usuario con permiso `comunicacion:enviar` solicita su historial de envíos
- **THEN** el sistema retorna únicamente las comunicaciones donde ese usuario es el remitente (`enviado_por`)
- **AND** el resultado está scoped al tenant del usuario

#### Scenario: El historial no expone comunicaciones de otros remitentes
- **WHEN** el usuario A solicita su historial
- **THEN** ningún item del historial tiene `enviado_por` distinto al `usuario.id` de A

#### Scenario: Comunicaciones con soft delete no aparecen en el historial
- **WHEN** existen comunicaciones del usuario con `deleted_at IS NOT NULL`
- **THEN** esas comunicaciones NO aparecen en el historial retornado

