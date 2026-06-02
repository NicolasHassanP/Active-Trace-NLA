## ADDED Requirements

### Requirement: Borrado lógico en lugar de borrado físico

El sistema SHALL borrar entidades de forma lógica marcando `deleted_at` con la fecha-hora del borrado. El sistema NUNCA SHALL ejecutar un borrado físico (`DELETE`) de entidades de negocio. La fila SHALL permanecer en la tabla tras el borrado lógico, preservando el historial para auditoría.

#### Scenario: Borrar marca deleted_at

- **WHEN** se borra una entidad mediante el repository
- **THEN** su `deleted_at` queda establecido con la fecha-hora del borrado
- **AND** la fila sigue existiendo físicamente en la tabla

### Requirement: Las consultas excluyen lo borrado por defecto

Las operaciones de lectura del repository SHALL excluir por defecto las entidades con `deleted_at` no nulo. Un registro borrado lógicamente NO SHALL aparecer en los resultados de lectura por defecto.

#### Scenario: Registro borrado no aparece por defecto

- **WHEN** se lista una entidad después de haberla borrado lógicamente
- **THEN** el registro borrado no aparece en el resultado

### Requirement: Camino explícito para incluir borrados

El repository SHALL ofrecer un camino explícito (p. ej. `include_deleted=True`) que incluya las entidades borradas lógicamente, para casos de auditoría o recuperación.

#### Scenario: Incluir borrados explícitamente

- **WHEN** se lista una entidad con la opción de incluir borrados activada
- **THEN** el resultado incluye los registros con `deleted_at` no nulo
