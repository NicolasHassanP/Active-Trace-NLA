## ADDED Requirements

### Requirement: Página de monitor general con gating de rol
La aplicación SHALL ofrecer una página de monitor general de actividades accesible en `/monitor`, guardada por `ProtectedRoute`, disponible solo para COORDINADOR y ADMIN (F2.7, F2.9). La identidad y el tenant del actor SHALL provenir exclusivamente del JWT.

#### Scenario: Coordinador accede al monitor
- **WHEN** un usuario autenticado con rol COORDINADOR navega a `/monitor`
- **THEN** la aplicación renderiza el monitor general de actividades

#### Scenario: Usuario sin rol habilitado es bloqueado
- **WHEN** un usuario autenticado cuyo único rol es PROFESOR navega a `/monitor`
- **THEN** la aplicación muestra la vista de acceso denegado (403)

### Requirement: Filtros transversales del monitor
La aplicación SHALL mostrar el estado de actividades del tenant consumiendo `GET /api/v1/analisis/monitor`, con filtros por materia, regional, comisión, búsqueda libre por alumno, estado de actividad, criterio de clasificación y rango de fechas (F2.9). Los filtros SHALL formar parte de la `queryKey` de TanStack Query para una invalidación de caché correcta.

#### Scenario: Aplicación de filtros
- **WHEN** el coordinador aplica filtros y la API responde 200 con las filas del monitor
- **THEN** la aplicación muestra las filas filtradas y mantiene los filtros en la URL/estado

#### Scenario: Limpieza de filtros
- **WHEN** el coordinador limpia la selección de filtros
- **THEN** la aplicación restablece el listado al estado por defecto

### Requirement: Exportación del monitor
La aplicación SHALL ofrecer la acción de exportar el resultado del monitor según el contrato de exportación disponible en el backend de análisis, disparando la descarga del archivo en el navegador.

#### Scenario: Exportación exitosa
- **WHEN** el coordinador solicita exportar y la API responde con el archivo adjunto
- **THEN** la aplicación dispara la descarga del archivo
