## ADDED Requirements

### Requirement: Página de encuentros (coordinación/admin) con gating de rol
La aplicación SHALL ofrecer una página de encuentros accesible en `/encuentros`, guardada por `ProtectedRoute`, disponible para COORDINADOR y ADMIN (vista transversal, F6.5). La identidad y el tenant del actor SHALL provenir exclusivamente del JWT.

#### Scenario: Coordinador accede a la vista transversal de encuentros
- **WHEN** un usuario autenticado con rol COORDINADOR navega a `/encuentros`
- **THEN** la aplicación renderiza la vista de instancias de encuentros del tenant

#### Scenario: Usuario sin rol habilitado es bloqueado
- **WHEN** un usuario autenticado cuyo único rol es FINANZAS navega a `/encuentros`
- **THEN** la aplicación muestra la vista de acceso denegado (403)

### Requirement: Vista transversal de instancias de encuentros
La aplicación SHALL listar las instancias de encuentros consumiendo `GET /api/v1/encuentros/instancias`, mostrando estado, materia, horario, enlace de videoconferencia y enlace de grabación cuando exista, con filtros disponibles según el contrato del endpoint.

#### Scenario: Listado de instancias
- **WHEN** la API responde 200 con las instancias de encuentros
- **THEN** la aplicación muestra cada instancia con su estado y enlaces

#### Scenario: Sin instancias en el período
- **WHEN** la API responde 200 con una lista vacía
- **THEN** la aplicación muestra un estado vacío informativo

### Requirement: Registro y consulta de guardias
La aplicación SHALL mostrar el registro de guardias consumiendo `GET /api/v1/guardias`, con filtros de consulta, y SHALL permitir exportar el registro consumiendo `GET /api/v1/guardias/export`, disparando la descarga del archivo.

#### Scenario: Consulta filtrada de guardias
- **WHEN** el coordinador aplica filtros y la API responde 200 con las guardias
- **THEN** la aplicación muestra el listado filtrado

#### Scenario: Exportación del registro de guardias
- **WHEN** el coordinador solicita exportar y la API responde con el archivo adjunto
- **THEN** la aplicación dispara la descarga del archivo
