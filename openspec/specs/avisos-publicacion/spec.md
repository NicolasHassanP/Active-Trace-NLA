## Requirements

### Requirement: Endpoint de lista de gestión para COORDINADOR y ADMIN
El sistema SHALL exponer el endpoint `GET /api/v1/avisos/gestion` que retorna la lista completa (`List[AvisoRead]`) de todos los avisos no eliminados del tenant del actor, sin aplicar el filtro de audiencia. Este endpoint SHALL estar restringido al permiso `avisos:publicar` (COORDINADOR, ADMIN) con comportamiento fail-closed: cualquier rol sin ese permiso SHALL recibir 403. La identidad y el tenant del actor SHALL provenir exclusivamente del JWT (nunca de parámetros de URL, body o cabeceras). Cada ítem SHALL incluir el campo `ack_count` derivado en tiempo de consulta (sin columna denormalizada). El resultado SHALL ordenarse por `created_at DESC` (más reciente primero). El endpoint SHALL excluir los avisos con soft-delete activo.

**Motivación**: C-15 solo expuso un feed filtrado por audiencia (`GET /avisos`), lo que impide a un COORDINADOR ver los avisos dirigidos a otros segmentos de audiencia (ej. avisos PorRol ALUMNO). OQ-1 de C-23 identificó este gap como bloqueante para el panel de gestión del coordinador.

#### Scenario: Coordinador obtiene todos los avisos del tenant
- **GIVEN** un usuario autenticado con permiso `avisos:publicar`
- **AND** el tenant tiene dos avisos: uno `Global` y uno `PorRol/ALUMNO`
- **WHEN** el usuario llama `GET /api/v1/avisos/gestion`
- **THEN** la respuesta contiene ambos avisos (incluyendo el dirigido a ALUMNO, que no está en el feed de audiencia del coordinador)
- **AND** cada aviso incluye el campo `ack_count` con el conteo correcto

#### Scenario: Usuario sin avisos:publicar recibe 403
- **GIVEN** un usuario autenticado cuyo rol es ALUMNO o TUTOR (sin `avisos:publicar`)
- **WHEN** el usuario llama `GET /api/v1/avisos/gestion`
- **THEN** el sistema responde 403 Forbidden

#### Scenario: Aislamiento de tenant
- **GIVEN** dos tenants A y B, cada uno con al menos un aviso
- **WHEN** un coordinador del tenant A llama `GET /api/v1/avisos/gestion`
- **THEN** la respuesta solo contiene los avisos del tenant A
- **AND** los avisos del tenant B no aparecen

#### Scenario: Avisos con soft-delete excluidos
- **GIVEN** el tenant tiene un aviso activo y un aviso con soft-delete
- **WHEN** el coordinador llama `GET /api/v1/avisos/gestion`
- **THEN** solo el aviso activo aparece en la respuesta

#### Scenario: ack_count correcto en lista de gestión
- **GIVEN** un aviso con dos confirmaciones de lectura registradas
- **WHEN** el coordinador llama `GET /api/v1/avisos/gestion`
- **THEN** ese aviso aparece con `ack_count = 2`
