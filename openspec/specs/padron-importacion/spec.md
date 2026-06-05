## ADDED Requirements

### Requirement: Vista de importación de padrón
La aplicación SHALL ofrecer una página de importación de padrón, accesible en `/padron`, guardada por `ProtectedRoute` con los roles PROFESOR, TUTOR, COORDINADOR y ADMIN. La página SHALL permitir seleccionar la materia y la cohorte de destino antes de importar.

#### Scenario: Usuario con rol permitido accede a la vista
- **WHEN** un usuario autenticado con rol PROFESOR navega a `/padron`
- **THEN** la aplicación renderiza la vista de importación de padrón con el selector de materia y cohorte

#### Scenario: Usuario sin rol permitido es bloqueado
- **WHEN** un usuario autenticado cuyo único rol es FINANZAS navega a `/padron`
- **THEN** la aplicación muestra la vista de acceso denegado (403) y no renderiza la importación

### Requirement: Preview de archivo de padrón
La aplicación SHALL permitir subir un archivo de padrón (.xlsx o .csv) y enviarlo a `POST /api/v1/padron/preview` como multipart, mostrando las filas detectadas (`nombre`, `apellidos`, `email`, `comision`, `regional`) sin escribir en la base de datos.

#### Scenario: Preview exitoso muestra las filas
- **WHEN** el usuario sube un archivo válido y la API responde 200 con una lista de filas
- **THEN** la aplicación muestra una tabla con las filas detectadas y habilita el botón de confirmación

#### Scenario: Archivo inválido devuelve 422
- **WHEN** la API responde 422 al previsualizar el archivo
- **THEN** la aplicación muestra el mensaje de error del campo `detail` y no habilita la confirmación

### Requirement: Confirmación de importación
La aplicación SHALL permitir confirmar la importación enviando las filas previsualizadas junto con `materia_id` y `cohorte_id` a `POST /api/v1/padron/activar`, y SHALL reflejar el resultado (versión activa y total de filas) al usuario.

#### Scenario: Activación exitosa
- **WHEN** el usuario confirma y la API responde 201 con la versión activa
- **THEN** la aplicación muestra un mensaje de éxito con el total de filas importadas y la versión queda marcada como activa

#### Scenario: Identidad nunca enviada en el payload
- **WHEN** la aplicación construye el cuerpo de la petición de activación
- **THEN** el cuerpo contiene únicamente `materia_id`, `cohorte_id` y `rows`, sin `tenant_id` ni identidad del actor

### Requirement: Sincronización on-demand desde Moodle
La aplicación SHALL permitir disparar la sincronización del padrón desde Moodle enviando `course_id`, `materia_id` y `cohorte_id` a `POST /api/v1/padron/sync-moodle`, y SHALL distinguir entre los estados de error 503 (Moodle no configurado) y 502 (Moodle no disponible).

#### Scenario: Sincronización exitosa
- **WHEN** el usuario dispara la sincronización y la API responde 201 con la nueva versión activa
- **THEN** la aplicación muestra el total de filas sincronizadas y marca la versión como activa

#### Scenario: Moodle no configurado en el entorno
- **WHEN** la API responde 503 al sincronizar
- **THEN** la aplicación muestra un aviso informativo (no un error crítico) indicando que la integración con Moodle no está configurada

#### Scenario: Moodle no disponible
- **WHEN** la API responde 502 al sincronizar
- **THEN** la aplicación muestra un error indicando que Moodle no está disponible y ofrece reintentar

### Requirement: Vaciado del padrón activo
La aplicación SHALL permitir vaciar el padrón activo de una materia×cohorte mediante `DELETE /api/v1/padron/vaciar` con `materia_id` y `cohorte_id` como query params, solicitando confirmación previa al usuario.

#### Scenario: Vaciado exitoso
- **WHEN** el usuario confirma el vaciado y la API responde 204
- **THEN** la aplicación refleja que ya no hay padrón activo para esa materia×cohorte

#### Scenario: Sin padrón activo
- **WHEN** la API responde 404 al vaciar
- **THEN** la aplicación informa que no existía un padrón activo para vaciar

#### Scenario: Vaciado de versión ajena sin permiso
- **WHEN** la API responde 403 al vaciar (un PROFESOR intenta vaciar una versión cargada por otro)
- **THEN** la aplicación muestra un mensaje de acceso denegado y no altera el estado mostrado
