## ADDED Requirements

### Requirement: Métricas de auditoría protegidas por permiso

El sistema SHALL exponer todas las vistas de métricas de auditoría únicamente a usuarios con el permiso `auditoria:ver`. Las solicitudes sin ese permiso SHALL ser rechazadas con HTTP 403 (fail-closed) y no SHALL devolver ningún dato agregado. El `tenant_id` y la identidad del usuario SHALL resolverse exclusivamente desde la sesión autenticada (JWT), NUNCA desde la URL, el body ni un header.

#### Scenario: Usuario con permiso obtiene métricas
- **WHEN** un usuario con el permiso `auditoria:ver` solicita una vista de métricas de auditoría
- **THEN** el sistema devuelve las métricas agregadas del tenant según el alcance del permiso

#### Scenario: Usuario sin permiso es rechazado
- **WHEN** un usuario sin el permiso `auditoria:ver` solicita una vista de métricas de auditoría
- **THEN** el sistema responde HTTP 403 y no devuelve ninguna métrica

### Requirement: Acciones por día

El sistema SHALL exponer una serie temporal que agrupe la cantidad de eventos de auditoría por día calendario (`date_trunc('day', created_at)`), scoped al tenant del usuario autenticado. La agregación SHALL realizarse en la consulta SQL del repository, no en memoria. Cada elemento de la serie SHALL incluir el día y el total de acciones de ese día. La serie SHALL respetar los filtros de rango de fechas, materia y usuario cuando estén presentes.

#### Scenario: Serie temporal agrupada por día
- **WHEN** un usuario autorizado solicita las acciones por día sobre un tenant con eventos en distintas fechas
- **THEN** el sistema devuelve un elemento por día con el total de acciones de ese día, ordenado cronológicamente

#### Scenario: Acciones por día acotadas por rango de fechas
- **WHEN** un usuario autorizado solicita las acciones por día con un rango `desde`/`hasta`
- **THEN** el sistema devuelve únicamente los días dentro del rango solicitado

### Requirement: Interacciones por docente

El sistema SHALL exponer un conteo de eventos de auditoría agrupado por actor real (`actor_user_id`) y por tipo de acción (`accion`), scoped al tenant. La agregación SHALL realizarse con `GROUP BY` en SQL. Cada elemento SHALL incluir el `actor_user_id`, la `accion` y el total de ocurrencias.

#### Scenario: Conteo por docente y tipo de acción
- **WHEN** un usuario autorizado solicita las interacciones por docente sobre un tenant con eventos de varios actores y acciones
- **THEN** el sistema devuelve, por cada combinación (actor, acción), el total de ocurrencias dentro del tenant

#### Scenario: Interacciones por docente filtradas por usuario
- **WHEN** un usuario autorizado solicita las interacciones por docente filtrando por un `actor_user_id` específico
- **THEN** el sistema devuelve únicamente las interacciones de ese actor

### Requirement: Interacciones por docente y materia

El sistema SHALL exponer un conteo de eventos de auditoría agrupado por actor real y por materia, scoped al tenant. Dado que `audit_event` no posee columna `materia_id`, la materia SHALL derivarse del `entidad_id` de los eventos cuyo `entidad_tipo` es `"Materia"`; los eventos cuyo `entidad_tipo` no es `"Materia"` SHALL agruparse bajo una clave de materia nula ("sin materia"). Cada elemento SHALL incluir el `actor_user_id`, el identificador de materia (o nulo) y el total.

#### Scenario: Conteo por docente y materia derivada de entidad_id
- **WHEN** un usuario autorizado solicita las interacciones por docente×materia y existen eventos con `entidad_tipo = "Materia"`
- **THEN** el sistema agrupa por (actor, entidad_id) y devuelve el total por cada combinación docente×materia

#### Scenario: Eventos sin materia se agrupan bajo clave nula
- **WHEN** existen eventos cuyo `entidad_tipo` no es `"Materia"`
- **THEN** el sistema los agrupa bajo una clave de materia nula y los reporta separados de las materias concretas

#### Scenario: Filtro por materia acota a una materia concreta
- **WHEN** un usuario autorizado solicita las interacciones por docente×materia filtrando por un identificador de materia
- **THEN** el sistema devuelve únicamente las interacciones de los eventos cuyo `entidad_tipo = "Materia"` y `entidad_id` coincide con la materia solicitada

### Requirement: Estado de comunicaciones por docente

El sistema SHALL exponer la distribución de estados de comunicación (`ComunicacionEstado`: Pendiente, Enviando, Enviado, Error, Cancelado) agrupada por el docente que encoló el envío (`enviado_por`), scoped al tenant, computada sobre la tabla `comunicacion` con `GROUP BY enviado_por, estado`. Cada elemento SHALL incluir el identificador del docente, el estado y el total de comunicaciones en ese estado. El resultado SHALL soportar el filtro por estado.

#### Scenario: Distribución de estados por docente
- **WHEN** un usuario autorizado solicita el estado de comunicaciones por docente sobre un tenant con comunicaciones en distintos estados
- **THEN** el sistema devuelve, por cada combinación (docente, estado), el total de comunicaciones en ese estado

#### Scenario: Filtro por estado de comunicación
- **WHEN** un usuario autorizado solicita el estado de comunicaciones por docente filtrando por un estado específico (por ejemplo `Error`)
- **THEN** el sistema devuelve únicamente las combinaciones con ese estado

### Requirement: Alcance row-level de las métricas según el permiso

Todas las vistas de métricas SHALL respetar el alcance del permiso `auditoria:ver` del usuario. Con alcance `propio`, las métricas sobre `audit_event` SHALL incluir únicamente los eventos cuyo actor real es el usuario actual, y las métricas sobre `comunicacion` SHALL incluir únicamente las comunicaciones cuyo `enviado_por` es el usuario actual. Con alcance global, SHALL incluir todos los datos del tenant.

#### Scenario: Alcance propio acota las métricas al propio usuario
- **WHEN** un usuario cuyo permiso `auditoria:ver` tiene alcance `propio` solicita cualquier vista de métricas
- **THEN** el sistema devuelve únicamente las métricas derivadas de su propia actividad (eventos con su `actor_user_id` y comunicaciones con su `enviado_por`)

#### Scenario: Alcance global incluye todo el tenant
- **WHEN** un usuario cuyo permiso `auditoria:ver` tiene alcance global solicita cualquier vista de métricas
- **THEN** el sistema devuelve las métricas de todos los actores y docentes del tenant

#### Scenario: Las métricas nunca cruzan el límite del tenant
- **WHEN** existen eventos y comunicaciones de más de un tenant
- **THEN** ninguna vista de métricas incluye datos de un tenant distinto al del usuario autenticado, en ningún alcance

### Requirement: Contrato estricto de salida de métricas

Cada vista de métricas SHALL devolver su resultado mediante un esquema de salida Pydantic v2 que rechaza campos no declarados (`extra='forbid'`). Las respuestas de métricas NO SHALL exponer PII ni contenido sensible: solo identificadores, códigos de acción, estados, fechas y totales agregados.

#### Scenario: Respuesta de métricas con esquema estricto
- **WHEN** un usuario autorizado solicita cualquier vista de métricas
- **THEN** el sistema devuelve los datos validados contra el esquema de salida, sin campos adicionales no declarados y sin exponer datos personales
