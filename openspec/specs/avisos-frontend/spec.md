## ADDED Requirements

### Requirement: Página de avisos con gating de rol
La aplicación SHALL ofrecer una página de avisos accesible en `/avisos`, guardada por `ProtectedRoute`. Las acciones de gestión (alta, edición, baja) SHALL estar disponibles solo para COORDINADOR y ADMIN (`avisos:publicar`). La bandeja de avisos y la confirmación de lectura SHALL estar disponibles para cualquier usuario autenticado. La identidad del actor SHALL provenir exclusivamente del JWT; el cuerpo de las peticiones NUNCA SHALL incluir identidad ni tenant.

#### Scenario: Coordinador accede a la gestión de avisos
- **WHEN** un usuario autenticado con rol COORDINADOR navega a `/avisos`
- **THEN** la aplicación renderiza la lista de avisos con las acciones de alta, edición y baja

#### Scenario: Usuario sin permiso solo ve la bandeja
- **WHEN** un usuario autenticado cuyo único rol es TUTOR navega a `/avisos`
- **THEN** la aplicación muestra la bandeja de avisos y la confirmación de lectura, sin acciones de gestión

### Requirement: Alta de aviso con scope, severidad, vigencia y ack
La aplicación SHALL ofrecer un formulario (React Hook Form + Zod) para crear un aviso con alcance (global / materia / cohorte), contexto (materia y/o cohorte cuando aplique), roles destinatarios, severidad, título, cuerpo, ventana de visibilidad (inicio/fin), orden de prioridad, estado activo/inactivo y `requiere_ack`, enviándolo a `POST /api/v1/avisos`. La validación de Zod SHALL exigir contexto coherente con el alcance (materia/cohorte obligatorios si el alcance no es global).

#### Scenario: Alta de aviso exitosa
- **WHEN** el usuario completa el formulario válido y la API responde 201 con el aviso creado
- **THEN** la aplicación muestra el aviso en la lista y notifica el éxito

#### Scenario: Validación de alcance no global sin contexto
- **WHEN** el usuario elige alcance por materia o cohorte sin seleccionar el contexto correspondiente
- **THEN** la validación de Zod impide el envío y muestra el error en el campo de contexto

### Requirement: Edición y baja de aviso
La aplicación SHALL permitir editar un aviso existente vía `PUT /api/v1/avisos/{aviso_id}` y darlo de baja (soft-delete) vía `DELETE /api/v1/avisos/{aviso_id}`, manejando el 404 cuando el aviso no existe o no pertenece al tenant.

#### Scenario: Edición exitosa
- **WHEN** el usuario edita un aviso y la API responde 200 con el aviso actualizado
- **THEN** la aplicación refleja los cambios en la lista

#### Scenario: Baja exitosa
- **WHEN** el usuario da de baja un aviso y la API responde 204
- **THEN** la aplicación quita el aviso de la lista activa y notifica el éxito

### Requirement: Bandeja de avisos y confirmación de lectura
La aplicación SHALL mostrar la bandeja de avisos del usuario consumiendo `GET /api/v1/avisos` (feed completo) y `GET /api/v1/avisos/pendientes` (avisos con `requiere_ack` no confirmados), respetando el orden devuelto por la API. Para los avisos pendientes, la aplicación SHALL permitir confirmar la lectura vía `POST /api/v1/avisos/{aviso_id}/ack`, manejando 403 (fuera de ventana / inactivo) y 404 (inexistente).

#### Scenario: Confirmación de lectura exitosa
- **WHEN** el usuario confirma la lectura de un aviso pendiente y la API responde 200
- **THEN** la aplicación quita el aviso de la bandeja de pendientes

#### Scenario: Aviso fuera de ventana al confirmar
- **WHEN** la API responde 403 al confirmar un aviso fuera de su ventana de visibilidad
- **THEN** la aplicación muestra el mensaje de error y no marca el aviso como confirmado
