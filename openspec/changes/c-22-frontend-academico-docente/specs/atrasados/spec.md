## ADDED Requirements

### Requirement: Vista de alumnos atrasados
La aplicación SHALL ofrecer una página de alumnos atrasados, accesible en `/atrasados`, guardada por `ProtectedRoute` con los roles PROFESOR, TUTOR, COORDINADOR y ADMIN. La página SHALL consultar `GET /api/v1/analisis/atrasados` con `materia_id`, `cohorte_id` y `actividades`, y SHALL mostrar por alumno sus actividades faltantes y no aprobadas.

#### Scenario: Listado con resultados
- **WHEN** existe al menos un alumno atrasado y la API responde 200 con la lista
- **THEN** la aplicación muestra una tabla con cada alumno, sus `actividades_faltantes` y sus `actividades_no_aprobadas`

#### Scenario: Sin alumnos atrasados
- **WHEN** la API responde 200 con una lista vacía
- **THEN** la aplicación muestra un estado vacío indicando que no hay alumnos atrasados para los filtros seleccionados

#### Scenario: Usuario sin rol permitido es bloqueado
- **WHEN** un usuario autenticado cuyo único rol es FINANZAS navega a `/atrasados`
- **THEN** la aplicación muestra la vista de acceso denegado (403)

### Requirement: Filtros y paginación de la tabla de atrasados
La aplicación SHALL permitir filtrar la lista por materia, cohorte y conjunto de actividades, y SHALL paginar el resultado del lado del cliente. El `queryKey` de la consulta SHALL incluir los filtros activos para invalidar correctamente la caché.

#### Scenario: Cambio de filtros refresca la lista
- **WHEN** el usuario cambia la materia o el conjunto de actividades seleccionadas
- **THEN** la aplicación ejecuta una nueva consulta con los filtros actualizados y muestra el resultado correspondiente

#### Scenario: Navegación entre páginas
- **WHEN** el resultado supera el tamaño de página y el usuario avanza a la página siguiente
- **THEN** la aplicación muestra el siguiente subconjunto de filas sin volver a pedir datos a la API

### Requirement: Encabezado de métricas de la materia
La aplicación SHALL consultar `GET /api/v1/analisis/reporte-materia` y mostrar como encabezado las métricas consolidadas (total de alumnos, total de atrasados, tasa de aprobación), manejando el caso `sin_datos`.

#### Scenario: Métricas disponibles
- **WHEN** la API responde con `sin_datos=false`
- **THEN** la aplicación muestra el total de alumnos, total de atrasados y la tasa de aprobación

#### Scenario: Sin datos suficientes
- **WHEN** la API responde con `sin_datos=true`
- **THEN** la aplicación muestra un indicador de que aún no hay datos suficientes en lugar de métricas vacías o erróneas

### Requirement: Selección de alumnos para comunicar
La aplicación SHALL permitir seleccionar uno o más alumnos atrasados de la tabla y propagar sus correos como destinatarios hacia el flujo de composición de comunicaciones.

#### Scenario: Selección de alumnos habilita la acción de comunicar
- **WHEN** el usuario marca al menos un alumno atrasado en la tabla
- **THEN** la aplicación habilita la acción de "Comunicar a seleccionados" con los emails de los alumnos marcados

#### Scenario: Sin selección la acción permanece deshabilitada
- **WHEN** no hay ningún alumno seleccionado
- **THEN** la acción de comunicar permanece deshabilitada
