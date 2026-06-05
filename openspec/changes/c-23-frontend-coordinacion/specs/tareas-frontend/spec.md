## ADDED Requirements

### Requirement: Página de tareas internas con gating de rol
La aplicación SHALL ofrecer una página de tareas accesible en `/tareas`, guardada por `ProtectedRoute`. La vista de "mis tareas" SHALL estar disponible para TUTOR, PROFESOR, COORDINADOR y ADMIN. El panel de administración (vista global con filtros, alta y cambio de estado) SHALL estar disponible solo para COORDINADOR y ADMIN. La identidad del actor SHALL provenir exclusivamente del JWT; el cuerpo de las peticiones NUNCA SHALL incluir identidad ni tenant.

#### Scenario: Coordinador accede al panel de administración de tareas
- **WHEN** un usuario autenticado con rol COORDINADOR navega a `/tareas`
- **THEN** la aplicación renderiza el panel de administración con filtros y acciones de alta y cambio de estado

#### Scenario: Docente accede solo a sus tareas
- **WHEN** un usuario autenticado cuyo único rol es PROFESOR navega a `/tareas`
- **THEN** la aplicación muestra la vista de "mis tareas" sin el panel de administración

### Requirement: Vista de mis tareas
La aplicación SHALL listar las tareas asignadas al usuario consumiendo `GET /api/v1/tareas/mias`, y SHALL permitir abrir el detalle de una tarea vía `GET /api/v1/tareas/{tarea_id}`.

#### Scenario: Listado de mis tareas
- **WHEN** la API responde 200 con las tareas del usuario
- **THEN** la aplicación muestra las tareas con su estado y contexto académico

### Requirement: Panel de administración de tareas con filtros
La aplicación SHALL mostrar la vista global de tareas consumiendo `GET /api/v1/tareas/admin`, con filtros por docente asignado, docente asignador, materia, estado y búsqueda libre.

#### Scenario: Filtrado del panel de administración
- **WHEN** el coordinador aplica filtros y la API responde 200 con las tareas filtradas
- **THEN** la aplicación muestra el listado filtrado

### Requirement: Alta de tarea
La aplicación SHALL ofrecer un formulario (React Hook Form + Zod) para crear una tarea (materia, docente asignado, descripción y criterio de cierre), enviándolo a `POST /api/v1/tareas`. La tarea creada SHALL aparecer en estado inicial Abierta.

#### Scenario: Alta de tarea exitosa
- **WHEN** el coordinador completa el formulario válido y la API responde 201
- **THEN** la aplicación muestra la nueva tarea en estado Abierta y notifica el éxito

#### Scenario: Validación de formulario de tarea
- **WHEN** el usuario intenta crear una tarea sin docente asignado o sin descripción
- **THEN** la validación de Zod impide el envío y muestra los errores en los campos

### Requirement: Delegación de tarea
La aplicación SHALL permitir delegar una tarea a otro docente vía `POST /api/v1/tareas/{tarea_id}/delegar`, dejando trazabilidad del nuevo asignado.

#### Scenario: Delegación exitosa
- **WHEN** el usuario delega una tarea y la API responde 200 con la tarea actualizada
- **THEN** la aplicación refleja el nuevo docente asignado

### Requirement: Workflow de estados y comentarios
La aplicación SHALL permitir cambiar el estado de una tarea vía `PATCH /api/v1/tareas/{tarea_id}/estado` y gestionar comentarios del hilo vía `GET /api/v1/tareas/{tarea_id}/comentarios` y `POST /api/v1/tareas/{tarea_id}/comentarios`.

#### Scenario: Cambio de estado exitoso
- **WHEN** el usuario cambia el estado de una tarea y la API responde 200 con la tarea actualizada
- **THEN** la aplicación muestra el nuevo estado

#### Scenario: Alta de comentario en el hilo
- **WHEN** el usuario agrega un comentario y la API responde 201
- **THEN** la aplicación muestra el comentario en el hilo de la tarea

#### Scenario: Estado de transición inválido rechazado
- **WHEN** la API responde con error al intentar un cambio de estado no permitido por el workflow
- **THEN** la aplicación muestra el mensaje de error y conserva el estado anterior
