## ADDED Requirements

### Requirement: Vista de comunicaciones
La aplicación SHALL ofrecer una página de comunicaciones, accesible en `/comunicaciones`, guardada por `ProtectedRoute`. La composición y la bandeja de envío SHALL estar disponibles para los roles PROFESOR, TUTOR, COORDINADOR y ADMIN (`comunicacion:enviar`), mientras que las acciones de aprobación/cancelación SHALL ofrecerse a COORDINADOR y ADMIN (`comunicacion:aprobar`).

#### Scenario: Docente accede a composición y bandeja
- **WHEN** un usuario autenticado con rol PROFESOR navega a `/comunicaciones`
- **THEN** la aplicación renderiza la composición de mensajes y la bandeja de estado de lote

#### Scenario: Usuario sin rol de mensajería es bloqueado
- **WHEN** un usuario autenticado cuyo único rol es FINANZAS navega a `/comunicaciones`
- **THEN** la aplicación muestra la vista de acceso denegado (403)

### Requirement: Composición y preview de plantilla
La aplicación SHALL ofrecer un formulario (React Hook Form + Zod) con `asunto_plantilla`, `cuerpo_plantilla` y destinatarios, y SHALL permitir previsualizar el render llamando a `POST /api/v1/comunicaciones/preview`, manejando el error 422 por variable faltante.

#### Scenario: Preview exitoso
- **WHEN** el usuario solicita previsualizar y la API responde 200 con `asunto` y `cuerpo` renderizados
- **THEN** la aplicación muestra el asunto y el cuerpo renderizados

#### Scenario: Variable de plantilla faltante
- **WHEN** la API responde 422 al previsualizar por una variable sin resolver
- **THEN** la aplicación muestra el mensaje de error indicando la variable faltante y no permite encolar hasta resolverla

#### Scenario: Validación de formulario
- **WHEN** el usuario intenta previsualizar o encolar con asunto o cuerpo vacíos o sin destinatarios
- **THEN** la validación de Zod impide el envío y muestra los mensajes de error en los campos correspondientes

### Requirement: Encolado de lote
La aplicación SHALL permitir encolar un lote enviando destinatarios, plantillas y variables por destinatario a `POST /api/v1/comunicaciones/encolar`, y SHALL retener el `lote_id` devuelto para el seguimiento del estado. El cuerpo de la petición NUNCA SHALL incluir identidad ni tenant del remitente.

#### Scenario: Encolado exitoso
- **WHEN** el usuario encola y la API responde 201 con `lote_id` y `total_encolados`
- **THEN** la aplicación muestra el total de mensajes encolados y abre la bandeja de estado de ese lote

#### Scenario: Variable faltante al encolar
- **WHEN** la API responde 422 al encolar por una variable sin resolver
- **THEN** la aplicación muestra el mensaje de error y no marca el lote como encolado

### Requirement: Bandeja de estado del lote
La aplicación SHALL consultar `GET /api/v1/comunicaciones/lote/{lote_id}` y mostrar los contadores de estado (pendientes, enviados, errores, cancelados) y la lista de mensajes con su estado individual, reflejando la máquina de estados Pendiente → Enviando → Enviado/Fallido/Cancelado.

#### Scenario: Visualización de contadores
- **WHEN** la API responde con el estado del lote
- **THEN** la aplicación muestra los contadores de pendientes, enviados, errores y cancelados, y el detalle por mensaje

#### Scenario: Refresco del avance mientras hay mensajes en curso
- **WHEN** el lote tiene mensajes en estado Pendiente o Enviando
- **THEN** la aplicación refresca periódicamente el estado del lote y detiene el refresco cuando todos los mensajes alcanzan un estado terminal

### Requirement: Aprobación y cancelación de comunicaciones
La aplicación SHALL ofrecer a los aprobadores acciones para aprobar o cancelar el lote completo (`POST /aprobar-lote`, `POST /cancelar-lote`) y mensajes individuales (`POST /aprobar-individual`, `POST /cancelar-individual`), invalidando la consulta del lote tras cada acción y manejando los errores 409 (transición inválida) y 404 (mensaje inexistente).

#### Scenario: Aprobación de lote
- **WHEN** el aprobador aprueba el lote y la API responde 200 con los mensajes actualizados
- **THEN** la aplicación refresca la bandeja y muestra los mensajes como aprobados/en envío

#### Scenario: Cancelación con transición inválida
- **WHEN** la API responde 409 al cancelar porque algún mensaje no es cancelable
- **THEN** la aplicación muestra el mensaje de error sin romper la vista y mantiene el estado actual del lote

#### Scenario: Acción individual sobre mensaje inexistente
- **WHEN** la API responde 404 al aprobar o cancelar un mensaje individual
- **THEN** la aplicación muestra el error para esa fila y conserva el resto de la bandeja
