## ADDED Requirements

### Requirement: Ruta y acceso a la bandeja de mensajería

El sistema SHALL exponer la página de bandeja de mensajería interna en la ruta protegida `/mensajes`, accesible para los roles PROFESOR, TUTOR, COORDINADOR y ADMIN. El acceso final a los datos lo gobierna el backend mediante el permiso `inbox:usar` (fail-closed → 403); el frontend gatea la visibilidad y el acceso a la ruta por rol.

#### Scenario: Usuario con rol habilitado accede a la bandeja

- **WHEN** un usuario autenticado con rol PROFESOR, TUTOR, COORDINADOR o ADMIN navega a `/mensajes`
- **THEN** el sistema renderiza la `InboxPage` sin redirigir a 404 ni a login

#### Scenario: Usuario sin rol habilitado no accede a la ruta

- **WHEN** un usuario autenticado cuyo rol no está en el conjunto habilitado intenta acceder a `/mensajes`
- **THEN** el sistema niega el acceso a la página mediante el guard de ruta protegida

### Requirement: Ítem de navegación "Mensajes"

El catálogo de navegación SHALL incluir un ítem con label "Mensajes", ícono `mail`, grupo `TRABAJO` y path `/mensajes`, visible únicamente para los roles PROFESOR, TUTOR, COORDINADOR y ADMIN.

#### Scenario: El ítem aparece para un rol habilitado

- **WHEN** se construye el nav para un usuario con rol COORDINADOR
- **THEN** el resultado incluye el ítem "Mensajes" con path `/mensajes` en el grupo `TRABAJO`

#### Scenario: El ítem no aparece para un rol no habilitado

- **WHEN** se construye el nav para un usuario cuyo único rol es ALUMNO
- **THEN** el resultado NO incluye el ítem "Mensajes"

### Requirement: Listado de hilos de la bandeja

La `InboxPage` SHALL listar los hilos del usuario autenticado obtenidos desde `GET /api/v1/inbox`, mostrando para cada hilo su asunto (o un texto sustituto cuando no tiene asunto), el contador de mensajes no leídos y el timestamp del último mensaje. El listado SHALL obtenerse exclusivamente a través de un hook de TanStack Query sobre el service.

#### Scenario: Se muestran los hilos del usuario

- **WHEN** la bandeja se carga y el endpoint devuelve uno o más hilos
- **THEN** el sistema renderiza un ítem por hilo con su asunto, contador de no leídos y timestamp del último mensaje

#### Scenario: Hilo con mensajes no leídos

- **WHEN** un hilo tiene `no_leidos` mayor que cero
- **THEN** el sistema muestra un indicador visible con la cantidad de no leídos para ese hilo

#### Scenario: Bandeja vacía

- **WHEN** el endpoint devuelve una lista vacía de hilos
- **THEN** el sistema muestra un estado vacío informativo en lugar de la lista

### Requirement: Vista de un hilo individual

Al seleccionar un hilo, la `InboxPage` SHALL obtener sus mensajes desde `GET /api/v1/inbox/{hilo_id}` y mostrarlos en orden cronológico, indicando para cada mensaje su cuerpo, su timestamp y si el mensaje fue enviado por el usuario autenticado (comparando `remitente_id` con la identidad de la sesión, nunca con un dato de la petición). La apertura del hilo SHALL refrescar el contador de no leídos del listado.

#### Scenario: Se abren los mensajes de un hilo

- **WHEN** el usuario selecciona un hilo de la lista
- **THEN** el sistema obtiene y muestra los mensajes del hilo en orden cronológico

#### Scenario: Distinción de mensajes propios

- **WHEN** un mensaje del hilo tiene `remitente_id` igual a la identidad del usuario autenticado
- **THEN** el sistema lo presenta diferenciado de los mensajes de la contraparte

#### Scenario: Abrir un hilo actualiza el contador de no leídos

- **WHEN** el usuario abre un hilo que tenía mensajes no leídos y la lectura se confirma server-side
- **THEN** el sistema refresca el listado de hilos para reflejar el contador de no leídos actualizado

### Requirement: Iniciar un nuevo hilo

La `InboxPage` SHALL ofrecer un formulario, validado con React Hook Form y Zod, para iniciar un hilo nuevo enviando `destinatario_id`, `asunto` opcional y `cuerpo` a `POST /api/v1/inbox`. El `cuerpo` SHALL ser obligatorio y no vacío. La identidad del remitente y el tenant NUNCA SHALL viajar en el body — se atribuyen server-side desde el JWT. Al crearse el hilo, el listado de hilos SHALL refrescarse.

#### Scenario: Creación exitosa de un hilo

- **WHEN** el usuario completa `destinatario_id` y un `cuerpo` no vacío y envía el formulario
- **THEN** el sistema llama a `POST /api/v1/inbox` con esos datos y, ante éxito, refresca el listado de hilos

#### Scenario: Cuerpo vacío bloquea el envío

- **WHEN** el usuario intenta enviar el formulario con el `cuerpo` vacío o solo espacios
- **THEN** la validación cliente impide el envío y muestra un mensaje de error en el campo `cuerpo`

#### Scenario: Destinatario inválido

- **WHEN** el backend responde 404 por destinatario inexistente en el tenant
- **THEN** el sistema muestra el error de dominio al usuario sin romper la página

#### Scenario: Hilo duplicado

- **WHEN** el backend responde 409 porque ya existe un hilo 1:1 con ese destinatario
- **THEN** el sistema muestra el error de dominio indicando el conflicto

### Requirement: Responder dentro de un hilo

La vista de hilo SHALL ofrecer un formulario, validado con React Hook Form y Zod, para responder enviando `asunto` y `cuerpo` a `POST /api/v1/inbox/{hilo_id}/responder`. Tanto `asunto` como `cuerpo` SHALL ser obligatorios y no vacíos. Al responder con éxito, los mensajes del hilo y el listado de hilos SHALL refrescarse.

#### Scenario: Respuesta exitosa

- **WHEN** el usuario completa `asunto` y `cuerpo` no vacíos en un hilo abierto y envía
- **THEN** el sistema llama a `POST /api/v1/inbox/{hilo_id}/responder` y, ante éxito, refresca los mensajes del hilo y el listado

#### Scenario: Campos vacíos bloquean la respuesta

- **WHEN** el usuario intenta enviar la respuesta con `asunto` o `cuerpo` vacío
- **THEN** la validación cliente impide el envío y muestra el error en el campo correspondiente

### Requirement: Acceso a la API solo vía service tipado y cliente centralizado

Todo acceso a los endpoints de `/api/v1/inbox` SHALL realizarse a través de un service de la feature `mensajeria` que use el cliente HTTP centralizado (`@/shared/services/api`) y normalice los errores de dominio. Los tipos del contrato SHALL espejar los schemas del backend sin usar `any`.

#### Scenario: El service usa el cliente centralizado

- **WHEN** cualquier función del service de mensajería realiza una petición HTTP
- **THEN** la petición se emite a través del cliente Axios centralizado, sin instanciar clientes ad-hoc ni incluir identidad/tenant en el body

#### Scenario: Tipado sin `any`

- **WHEN** se define el contrato de request/response de mensajería en el frontend
- **THEN** los tipos reflejan `InboxHiloRead`, `MensajeRead`, `HiloCreate` y `RespuestaCreate` sin recurrir a `any`
