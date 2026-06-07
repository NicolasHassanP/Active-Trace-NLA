## ADDED Requirements

### Requirement: Consulta del historial de envíos propios del remitente
El sistema SHALL permitir que cualquier usuario con permiso `comunicacion:enviar` consulte las comunicaciones donde él fue el remitente (`enviado_por == usuario.id`), scoped al tenant. La consulta SHALL ser solo lectura y NO SHALL modificar el estado de ninguna comunicación. El sistema SHALL excluir registros con soft delete aplicado (`deleted_at IS NOT NULL`).

#### Scenario: Remitente consulta su propio historial
- **WHEN** un usuario con permiso `comunicacion:enviar` solicita su historial de envíos
- **THEN** el sistema retorna únicamente las comunicaciones donde ese usuario es el remitente (`enviado_por`)
- **AND** el resultado está scoped al tenant del usuario

#### Scenario: El historial no expone comunicaciones de otros remitentes
- **WHEN** el usuario A solicita su historial
- **THEN** ningún item del historial tiene `enviado_por` distinto al `usuario.id` de A

#### Scenario: Comunicaciones con soft delete no aparecen en el historial
- **WHEN** existen comunicaciones del usuario con `deleted_at IS NOT NULL`
- **THEN** esas comunicaciones NO aparecen en el historial retornado
