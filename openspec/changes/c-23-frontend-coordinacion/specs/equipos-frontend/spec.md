## ADDED Requirements

### Requirement: Página de equipos docentes con gating de rol
La aplicación SHALL ofrecer una página de equipos docentes accesible en `/equipos`, guardada por `ProtectedRoute`. La gestión (asignación masiva, clonado, vigencia general, exportación) SHALL estar disponible solo para los roles COORDINADOR y ADMIN (`equipos:asignar`). La vista de "mis equipos" SHALL estar disponible para PROFESOR, TUTOR, NEXO, COORDINADOR y ADMIN (`equipos:ver`). La identidad y el tenant del actor SHALL provenir exclusivamente del JWT; el cuerpo de las peticiones NUNCA SHALL incluirlos.

#### Scenario: Coordinador accede a la gestión de equipos
- **WHEN** un usuario autenticado con rol COORDINADOR navega a `/equipos`
- **THEN** la aplicación renderiza la vista de equipos con las acciones de gestión (asignación masiva, clonado, vigencia, export)

#### Scenario: Usuario sin permiso de gestión solo ve sus equipos
- **WHEN** un usuario autenticado cuyo único rol es PROFESOR navega a `/equipos`
- **THEN** la aplicación muestra la vista de "mis equipos" sin las acciones de gestión

#### Scenario: Usuario sin rol habilitado es bloqueado
- **WHEN** un usuario autenticado cuyo único rol es FINANZAS navega a `/equipos`
- **THEN** la aplicación muestra la vista de acceso denegado (403)

### Requirement: Vista de mis equipos
La aplicación SHALL listar las asignaciones del usuario autenticado consumiendo `GET /api/v1/equipos/mis-equipos`, mostrando para cada una materia, carrera, cohorte, rol, comisiones, vigencia (desde/hasta) y `estado_vigencia`. La aplicación SHALL ofrecer filtros de cliente por estado, materia, rol, carrera y cohorte.

#### Scenario: Listado exitoso de mis equipos
- **WHEN** la API responde 200 con la lista de asignaciones del usuario
- **THEN** la aplicación muestra cada asignación con su `estado_vigencia` y permite filtrar el listado

#### Scenario: Usuario sin asignaciones
- **WHEN** la API responde 200 con una lista vacía
- **THEN** la aplicación muestra un estado vacío informativo sin error

### Requirement: Consulta de equipo por tripleta
La aplicación SHALL permitir consultar el equipo de una combinación materia × carrera × cohorte consumiendo `GET /api/v1/equipos` con esos tres parámetros obligatorios y filtros opcionales de rol y responsable.

#### Scenario: Consulta de equipo por tripleta
- **WHEN** el coordinador selecciona materia, carrera y cohorte y solicita el equipo
- **THEN** la aplicación llama a `GET /api/v1/equipos` con la tripleta y muestra las asignaciones devueltas

### Requirement: Asignación masiva de docentes
La aplicación SHALL ofrecer un formulario (React Hook Form + Zod) para asignar múltiples docentes a una combinación materia × carrera × cohorte × rol con vigencia, enviándolo a `POST /api/v1/equipos/asignacion-masiva`. Al responder 201 con el resumen del lote, la aplicación SHALL mostrar la cantidad de asignaciones creadas; al responder 422 (usuario o referencia inválida) SHALL mostrar el mensaje de error y no marcar el lote como creado.

#### Scenario: Asignación masiva exitosa
- **WHEN** la API responde 201 con el resumen del lote
- **THEN** la aplicación muestra el total de asignaciones creadas y refresca el equipo

#### Scenario: Asignación masiva rechazada por referencia inválida
- **WHEN** la API responde 422 por un usuario o referencia inexistente
- **THEN** la aplicación muestra el mensaje de error y no marca el lote como creado

### Requirement: Clonado de equipo entre períodos
La aplicación SHALL permitir clonar las asignaciones de un equipo origen (materia × carrera × cohorte) hacia un destino, enviando la operación a `POST /api/v1/equipos/clonar`, y SHALL mostrar el resumen de clonación (creadas / omitidas por duplicado).

#### Scenario: Clonado exitoso
- **WHEN** la API responde 201 con el resumen de clonación
- **THEN** la aplicación muestra cuántas asignaciones se crearon y cuántas se omitieron por duplicado

### Requirement: Modificación de vigencia general
La aplicación SHALL permitir actualizar las fechas (desde/hasta) de todas las asignaciones de un equipo enviando la operación a `PATCH /api/v1/equipos/vigencia-general`, y SHALL mostrar la cantidad de asignaciones afectadas.

#### Scenario: Vigencia general actualizada
- **WHEN** la API responde 200 con `{ afectadas: N }`
- **THEN** la aplicación muestra que N asignaciones fueron actualizadas

### Requirement: Exportación del equipo
La aplicación SHALL permitir exportar el equipo consultado consumiendo `GET /api/v1/equipos/exportar`, que devuelve un CSV adjunto, y SHALL disparar la descarga del archivo en el navegador.

#### Scenario: Exportación exitosa
- **WHEN** el coordinador solicita exportar el equipo y la API responde con el CSV adjunto
- **THEN** la aplicación dispara la descarga del archivo CSV
