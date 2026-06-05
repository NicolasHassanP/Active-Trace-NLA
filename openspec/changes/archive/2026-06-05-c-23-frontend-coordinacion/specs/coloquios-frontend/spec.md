## ADDED Requirements

### Requirement: Página de coloquios con gating de rol
La aplicación SHALL ofrecer una página de coloquios accesible en `/coloquios`, guardada por `ProtectedRoute`, disponible para COORDINADOR y ADMIN (`coloquios:gestionar`). La identidad y el tenant del actor SHALL provenir exclusivamente del JWT; el cuerpo de las peticiones NUNCA SHALL incluirlos.

#### Scenario: Coordinador accede a coloquios
- **WHEN** un usuario autenticado con rol COORDINADOR navega a `/coloquios`
- **THEN** la aplicación renderiza el panel de coloquios con métricas y convocatorias

#### Scenario: Usuario sin rol habilitado es bloqueado
- **WHEN** un usuario autenticado cuyo único rol es TUTOR navega a `/coloquios`
- **THEN** la aplicación muestra la vista de acceso denegado (403)

### Requirement: Panel de métricas de coloquios
La aplicación SHALL mostrar el panel de métricas consumiendo `GET /api/v1/coloquios/metricas`: total de alumnos cargados, convocatorias activas, reservas activas y notas registradas (F7.1).

#### Scenario: Métricas exitosas
- **WHEN** la API responde 200 con las métricas
- **THEN** la aplicación muestra los cuatro indicadores

### Requirement: Listado de convocatorias
La aplicación SHALL listar las convocatorias consumiendo `GET /api/v1/coloquios/convocatorias`, mostrando materia, instancia, días disponibles, convocados, reservas activas y cupos libres (F7.4).

#### Scenario: Listado de convocatorias
- **WHEN** la API responde 200 con las convocatorias y sus métricas operativas
- **THEN** la aplicación muestra cada convocatoria con sus indicadores y acciones de gestión

### Requirement: Creación de convocatoria
La aplicación SHALL ofrecer un formulario (React Hook Form + Zod) para crear una convocatoria (materia, cohorte, tipo, instancia, días disponibles y cupos por día), enviándolo a `POST /api/v1/coloquios/convocatorias` (F7.3).

#### Scenario: Creación exitosa
- **WHEN** el usuario completa el formulario válido y la API responde 201
- **THEN** la aplicación muestra la nueva convocatoria en el listado

#### Scenario: Validación de cupos
- **WHEN** el usuario ingresa un cupo no positivo o sin días disponibles
- **THEN** la validación de Zod impide el envío y muestra el error

### Requirement: Importación de candidatos
La aplicación SHALL permitir cargar o actualizar el padrón de candidatos de una convocatoria vía `POST /api/v1/coloquios/convocatorias/{evaluacion_id}/candidatos` (F7.2).

#### Scenario: Importación de candidatos exitosa
- **WHEN** el usuario importa candidatos y la API responde 204
- **THEN** la aplicación notifica el éxito y refresca las métricas de la convocatoria

### Requirement: Cierre de convocatoria
La aplicación SHALL permitir cerrar una convocatoria vía `POST /api/v1/coloquios/convocatorias/{evaluacion_id}/cerrar`.

#### Scenario: Cierre exitoso
- **WHEN** el usuario cierra una convocatoria y la API responde 200
- **THEN** la aplicación marca la convocatoria como cerrada en el listado

### Requirement: Agenda de reservas y registro de resultados
La aplicación SHALL mostrar la agenda consolidada de reservas activas consumiendo `GET /api/v1/coloquios/agenda` y el registro de resultados de una convocatoria consumiendo `GET /api/v1/coloquios/convocatorias/{evaluacion_id}/resultados` (F7.5).

#### Scenario: Agenda de reservas
- **WHEN** la API responde 200 con la agenda de reservas activas
- **THEN** la aplicación muestra los turnos reservados ordenados

#### Scenario: Registro de resultados
- **WHEN** la API responde 200 con los resultados de una convocatoria
- **THEN** la aplicación muestra las notas registradas por alumno
