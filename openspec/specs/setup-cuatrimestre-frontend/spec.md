## ADDED Requirements

### Requirement: Página de setup de cuatrimestre con gating de rol
La aplicación SHALL ofrecer un flujo guiado de inicio de cuatrimestre accesible en `/setup-cuatrimestre`, guardado por `ProtectedRoute`, disponible para COORDINADOR y ADMIN (FL-03). La identidad y el tenant del actor SHALL provenir exclusivamente del JWT.

#### Scenario: Coordinador accede al setup
- **WHEN** un usuario autenticado con rol COORDINADOR navega a `/setup-cuatrimestre`
- **THEN** la aplicación renderiza el flujo guiado con sus pasos secuenciales

#### Scenario: Usuario sin rol habilitado es bloqueado
- **WHEN** un usuario autenticado cuyo único rol es PROFESOR navega a `/setup-cuatrimestre`
- **THEN** la aplicación muestra la vista de acceso denegado (403)

### Requirement: Orquestación de pasos del setup
El flujo guiado SHALL orquestar los pasos de FL-03 reutilizando las acciones de las capacidades existentes, sin duplicar su lógica: (1) crear/seleccionar cohorte (estructura académica existente), (2) clonar equipo (`POST /api/v1/equipos/clonar`), (3) ajustar asignaciones (`POST /api/v1/equipos/asignacion-masiva`), (4) ajustar vigencias (`PATCH /api/v1/equipos/vigencia-general`), (5) cargar programas (`POST /api/v1/programas`), (6) cargar fechas de evaluaciones (`POST /api/v1/fechas-academicas`), (7) publicar aviso de bienvenida (`POST /api/v1/avisos`). Cada paso SHALL indicar su estado (pendiente / completado) y SHALL permitir avanzar solo cuando el paso anterior necesario esté resuelto.

#### Scenario: Avance secuencial del flujo
- **WHEN** el coordinador completa un paso del setup con éxito
- **THEN** la aplicación marca el paso como completado y habilita el siguiente

#### Scenario: Error en un paso no avanza el flujo
- **WHEN** un paso del setup falla (la API responde con error)
- **THEN** la aplicación muestra el error, conserva el paso como pendiente y no avanza al siguiente

#### Scenario: Publicación del aviso de bienvenida
- **WHEN** el coordinador completa el paso final y publica el aviso de bienvenida con éxito (201)
- **THEN** la aplicación marca el flujo como completado
