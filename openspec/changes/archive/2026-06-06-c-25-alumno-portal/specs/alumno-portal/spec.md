## ADDED Requirements

### Requirement: Consulta del estado académico propio del alumno

El sistema SHALL exponer el endpoint `GET /api/v1/alumno/estado-academico` que devuelve el estado académico del alumno autenticado, protegido por el permiso `academico:ver_propio`. La identidad (`user_id`) y el `tenant_id` del alumno SHALL derivarse exclusivamente del JWT verificado; el endpoint MUST NOT aceptar ningún identificador de alumno por URL, query, body ni header.

#### Scenario: Alumno autenticado consulta su estado académico
- **WHEN** un usuario con rol ALUMNO y permiso `academico:ver_propio` hace `GET /api/v1/alumno/estado-academico`
- **THEN** el sistema responde 200 con sus materias inscriptas, sus calificaciones propias, el estado de entregas por actividad, el porcentaje de avance y sus coloquios reservados

#### Scenario: Usuario sin el permiso recibe 403
- **WHEN** un usuario autenticado sin el permiso `academico:ver_propio` hace `GET /api/v1/alumno/estado-academico`
- **THEN** el sistema responde 403 (fail-closed) y no devuelve datos académicos

#### Scenario: Petición sin sesión válida recibe 401
- **WHEN** se hace `GET /api/v1/alumno/estado-academico` sin un token de acceso válido
- **THEN** el sistema responde 401 y no devuelve datos

### Requirement: Aislamiento por tenant y por identidad del alumno

El estado académico devuelto SHALL contener únicamente datos del alumno autenticado dentro de su propio tenant. El sistema SHALL resolver las materias y calificaciones a través de las entradas de padrón cuyo `usuario_id` coincide con el `user_id` del JWT, y los coloquios a través de las reservas cuyo `alumno_id` coincide con ese mismo `user_id`, siempre filtrando por `tenant_id`.

#### Scenario: No se filtran datos de otros alumnos
- **WHEN** un alumno consulta su estado académico
- **THEN** el sistema NUNCA incluye calificaciones, materias ni reservas pertenecientes a otro alumno

#### Scenario: No se filtran datos de otro tenant
- **WHEN** un alumno de un tenant consulta su estado académico
- **THEN** el sistema NUNCA incluye datos de otro tenant, aun si existiera un registro con el mismo `usuario_id` en otro tenant

#### Scenario: Entrada de padrón sin cuenta reconciliada no aparece
- **WHEN** existe una entrada de padrón del alumno cuyo `usuario_id` aún no está vinculado a su cuenta
- **THEN** esa materia no se incluye en la respuesta, porque el vínculo identidad↔padrón no está establecido

### Requirement: Materias inscriptas con calificaciones y estado de entregas

Por cada materia en la que el alumno figura en un padrón activo, el sistema SHALL devolver el identificador y nombre de la materia, la lista de sus calificaciones (actividad, nota y aprobado) y la clasificación de estado de entrega de cada actividad.

#### Scenario: Materia con calificaciones cargadas
- **WHEN** el alumno tiene calificaciones cargadas en una materia
- **THEN** la respuesta lista cada actividad con su nota (numérica o textual) y su estado de aprobación

#### Scenario: Clasificación del estado de entrega por actividad
- **WHEN** una calificación tiene `aprobado = true`
- **THEN** la actividad se clasifica como `aprobada`
- **WHEN** una calificación tiene nota (numérica o textual) pero `aprobado = false`
- **THEN** la actividad se clasifica como `con_nota`
- **WHEN** una calificación no tiene nota numérica ni textual
- **THEN** la actividad se clasifica como `sin_entrega`

#### Scenario: Materia sin calificaciones
- **WHEN** el alumno figura en el padrón de una materia pero aún no tiene calificaciones
- **THEN** la materia aparece con lista de calificaciones vacía y avance 0%

### Requirement: Porcentaje de avance derivado

El sistema SHALL calcular el porcentaje de avance por materia como la proporción de actividades aprobadas sobre el total de actividades calificadas del alumno en esa materia, y un avance global ponderado por la cantidad de actividades. El porcentaje SHALL derivarse en la consulta y MUST NOT persistirse.

#### Scenario: Avance por materia
- **WHEN** el alumno tiene 4 actividades calificadas en una materia, 3 de ellas aprobadas
- **THEN** el avance de esa materia es 75%

#### Scenario: Avance con cero actividades
- **WHEN** el alumno no tiene actividades calificadas en una materia
- **THEN** el avance de esa materia es 0% y no genera división por cero

#### Scenario: Avance global ponderado
- **WHEN** el alumno tiene actividades calificadas en varias materias
- **THEN** el avance global se calcula sobre el total de actividades aprobadas dividido por el total de actividades calificadas

### Requirement: Coloquios reservados del alumno

El sistema SHALL devolver las reservas de evaluación activas del alumno autenticado, incluyendo la materia, la instancia, la fecha del turno y la franja horaria cuando exista. Las reservas canceladas MUST NOT incluirse.

#### Scenario: Alumno con una reserva activa
- **WHEN** el alumno tiene una reserva de evaluación en estado `Activa`
- **THEN** la respuesta incluye esa reserva con materia, instancia, fecha y franja

#### Scenario: Reserva cancelada excluida
- **WHEN** el alumno tiene una reserva en estado `Cancelada`
- **THEN** esa reserva NO aparece en la respuesta

#### Scenario: Alumno sin reservas
- **WHEN** el alumno no tiene reservas activas
- **THEN** la lista de coloquios reservados está vacía

### Requirement: Pantalla "Mi cursada" exclusiva del rol ALUMNO

El frontend SHALL ofrecer la página `/mi-cursada`, accesible únicamente para el rol ALUMNO, que presenta el estado académico del alumno: indicadores de avance, materias cursadas con sus notas y estado de entregas, y los coloquios reservados. La página SHALL aparecer en la navegación bajo un grupo `MI CURSADA` visible sólo para el rol ALUMNO.

#### Scenario: Alumno ve "Mi cursada" en la navegación
- **WHEN** un usuario con rol ALUMNO entra a la aplicación
- **THEN** la navegación muestra el grupo `MI CURSADA` con el ítem "Mi cursada" que enlaza a `/mi-cursada`

#### Scenario: Rol no ALUMNO no ve la entrada ni accede a la página
- **WHEN** un usuario sin el rol ALUMNO inspecciona la navegación o intenta abrir `/mi-cursada`
- **THEN** el ítem `MI CURSADA` no aparece y el acceso a la ruta es denegado

#### Scenario: Estados vacíos
- **WHEN** el alumno aún no tiene materias o coloquios reservados
- **THEN** la página muestra estados vacíos claros en lugar de tablas vacías sin contexto
