## ADDED Requirements

### Requirement: Modelo de hilos y mensajes internos

El sistema SHALL modelar la mensajería interna como `HiloMensaje` (conversación entre usuarios registrados del sistema) que agrupa uno o más `Mensaje`. Cada `Mensaje` SHALL tener `asunto`, `cuerpo`, `remitente_id` (FK → Usuario) y marca temporal de creación. Cada `HiloMensaje` y cada `Mensaje` SHALL llevar `tenant_id`. Este módulo SHALL ser independiente del módulo `comunicaciones` (emails salientes a alumnos): no comparte cola, estados de envío ni despacho externo.

#### Scenario: Mensaje se asocia a su hilo y remitente
- **WHEN** se crea un mensaje dentro de un hilo
- **THEN** el mensaje queda asociado al `hilo_id`, con `remitente_id` igual al titular del JWT y una marca temporal de creación

#### Scenario: El remitente no puede falsificarse
- **WHEN** el body de un envío incluye un `remitente_id` distinto al del JWT
- **THEN** el sistema ignora ese valor y atribuye el mensaje al titular del JWT

### Requirement: Ver la bandeja propia

El sistema SHALL exponer `GET /api/v1/inbox`, protegido por `require_permission("inbox:usar")` (fail-closed → 403), que devuelve los hilos en los que el titular del JWT participa, dentro de su tenant, ordenados por actividad reciente, con el conteo de mensajes no leídos por hilo.

#### Scenario: La bandeja solo muestra hilos propios
- **WHEN** un usuario invoca `GET /api/v1/inbox`
- **THEN** el sistema devuelve únicamente los hilos donde el titular del JWT es participante
- **AND** no incluye hilos de otros usuarios en los que no participa

#### Scenario: Conteo de no leídos por hilo
- **WHEN** un hilo tiene mensajes no leídos para el usuario
- **THEN** el listado expone la cantidad de mensajes no leídos de ese hilo para ese usuario

#### Scenario: Sin permiso de inbox se rechaza
- **WHEN** un usuario sin `inbox:usar` invoca `GET /api/v1/inbox`
- **THEN** el sistema responde 403 sin devolver hilos

### Requirement: Leer un hilo y sus mensajes

El sistema SHALL exponer `GET /api/v1/inbox/{hilo_id}` que devuelve los mensajes del hilo en orden cronológico, SOLO si el titular del JWT es participante del hilo y pertenece al mismo tenant. Al abrir el hilo, el sistema SHALL marcar como leídos para ese usuario los mensajes previamente no leídos.

#### Scenario: Participante lee el hilo
- **WHEN** un participante del hilo invoca `GET /api/v1/inbox/{hilo_id}`
- **THEN** el sistema responde 200 con los mensajes en orden cronológico
- **AND** marca como leídos para ese usuario los mensajes que estaban no leídos

#### Scenario: No participante no accede al hilo
- **WHEN** un usuario que no participa del hilo invoca `GET /api/v1/inbox/{hilo_id}`
- **THEN** el sistema responde 404 (el hilo no existe para él) y no revela su contenido

#### Scenario: Hilo de otro tenant es inaccesible
- **WHEN** un usuario invoca un `hilo_id` que pertenece a otro tenant
- **THEN** el sistema responde 404 sin filtrar información del otro tenant

### Requirement: Responder dentro de un hilo

El sistema SHALL exponer `POST /api/v1/inbox/{hilo_id}/responder`, protegido por `require_permission("inbox:usar")`, que agrega un nuevo `Mensaje` al hilo existente con el titular del JWT como remitente. Solo un participante del hilo SHALL poder responder. El schema de entrada SHALL ser Pydantic v2 con `extra='forbid'` y exigir `asunto` y `cuerpo` no vacíos.

#### Scenario: Participante responde y el mensaje se agrega al hilo
- **WHEN** un participante envía `POST /api/v1/inbox/{hilo_id}/responder` con `asunto` y `cuerpo`
- **THEN** el sistema responde 201 y el nuevo mensaje queda asociado al hilo con `remitente_id` del JWT

#### Scenario: No participante no puede responder
- **WHEN** un usuario que no participa del hilo intenta responder
- **THEN** el sistema responde 404 y no agrega el mensaje

#### Scenario: Cuerpo vacío es rechazado
- **WHEN** el body de la respuesta tiene `cuerpo` vacío
- **THEN** el sistema responde 422 y no persiste el mensaje

#### Scenario: Campo no declarado es rechazado
- **WHEN** el body incluye una clave no declarada (por ejemplo `tenant_id` o `remitente_id`)
- **THEN** el sistema responde 422 (`extra='forbid'`)

### Requirement: Iniciar un nuevo hilo

El sistema SHALL exponer `POST /api/v1/inbox`, protegido por `require_permission("inbox:usar")`, que crea un `HiloMensaje` nuevo con su primer `Mensaje` y uno o más destinatarios participantes del mismo tenant. El remitente SHALL ser el titular del JWT. Todos los destinatarios SHALL pertenecer al tenant del remitente.

#### Scenario: Creación de hilo con destinatario válido
- **WHEN** un usuario crea un hilo con un destinatario del mismo tenant, `asunto` y `cuerpo`
- **THEN** el sistema responde 201, crea el hilo con remitente y destinatario como participantes, y persiste el primer mensaje

#### Scenario: Destinatario de otro tenant es rechazado
- **WHEN** un usuario incluye como destinatario a un usuario de otro tenant
- **THEN** el sistema rechaza la operación (404/422) y no crea el hilo

### Requirement: Aislamiento por usuario y por tenant

El sistema SHALL impedir que un usuario lea, responda o descubra hilos en los que no participa, y SHALL filtrar toda consulta de mensajería por `tenant_id` por defecto. La participación en un hilo SHALL derivarse del estado almacenado, nunca de un parámetro de la petición.

#### Scenario: Aislamiento entre usuarios del mismo tenant
- **WHEN** dos usuarios del mismo tenant tienen hilos separados
- **THEN** ninguno ve los hilos del otro salvo que sean co-participantes

#### Scenario: Aislamiento entre tenants
- **WHEN** se consulta la bandeja o un hilo
- **THEN** ninguna respuesta incluye hilos ni mensajes de un tenant distinto al del JWT

### Requirement: Soft delete y trazabilidad de la mensajería

El sistema SHALL aplicar soft delete (`deleted_at`) a hilos y mensajes, sin borrado físico, preservando el histórico para auditoría. La atribución del remitente real SHALL conservarse siempre.

#### Scenario: Mensaje eliminado conserva el registro
- **WHEN** un mensaje se elimina
- **THEN** se marca `deleted_at` y nunca se borra físicamente
- **AND** queda excluido de los listados activos pero disponible para auditoría
