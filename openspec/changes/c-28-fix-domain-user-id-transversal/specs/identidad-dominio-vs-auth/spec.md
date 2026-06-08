## ADDED Requirements

### Requirement: Identidad de dominio se resuelve vía resolve_domain_user_id
El sistema SHALL traducir `auth_identities.id` (el `sub` del JWT, expuesto como `CurrentUser.user_id`) a `usuario.id` mediante `resolve_domain_user_id(current_user, db)` antes de persistir o filtrar cualquier columna que sea FK a `usuario.id`.

#### Scenario: Escritura de FK de dominio usa usuario.id
- **WHEN** un endpoint persiste un registro con una columna FK a `usuario.id` (p. ej. `tarea.asignado_por`, `comunicacion.enviado_por`, `padron_version.cargado_por`, `acknowledgment_aviso.usuario_id`)
- **THEN** el valor escrito SHALL ser el `usuario.id` resuelto por `resolve_domain_user_id`, nunca `current_user.user_id` directo

#### Scenario: Filtro de scope "propio" usa usuario.id
- **WHEN** un endpoint filtra registros de dominio por el actor con scope `propio` (p. ej. `importado_por`, `Asignacion.usuario_id`)
- **THEN** el predicado de filtro SHALL usar el `usuario.id` resuelto, de modo que el scope matchee los registros reales del actor

#### Scenario: Identidad de dominio inexistente falla cerrado
- **WHEN** `resolve_domain_user_id` no encuentra un `usuario` activo cuyo `auth_identity_id` sea el del JWT en el tenant actual
- **THEN** el sistema SHALL responder 500 (inconsistencia de datos) en lugar de escribir/filtrar con un identificador inválido

### Requirement: Prohibido persistir o filtrar current_user.user_id en columnas de dominio
El sistema SHALL NOT usar `current_user.user_id` como valor para columnas que referencian `usuario.id`, ni como fallback (`domain_user_id or current_user.user_id`). El parámetro `domain_user_id` SHALL ser requerido (no opcional con default) en los services que escriben o filtran FKs de dominio.

#### Scenario: Service exige domain_user_id explícito
- **WHEN** un service de dominio recibe la identidad del actor para una operación de escritura/filtro de FK
- **THEN** la firma SHALL exigir `domain_user_id: uuid.UUID` sin default ni fallback a `current_user.user_id`

#### Scenario: Ningún router escribe auth_identity_id en columna de dominio
- **WHEN** se audita un router de escritura de dominio
- **THEN** no SHALL existir ninguna ruta de código que pase `current_user.user_id` a un parámetro que termine en una columna FK a `usuario.id`

### Requirement: Identidad de auditoría es una excepción documentada
El sistema SHALL almacenar `audit.actor_user_id` (y `impersonated_user_id`) usando `auth_identities.id` (`current_user.user_id`), por diseño (RN-41 / D5). Esta es la única excepción explícita al invariante de identidad de dominio y SHALL estar documentada.

#### Scenario: Evento de auditoría atribuye al actor del JWT
- **WHEN** se emite un evento de auditoría
- **THEN** `actor_user_id` SHALL ser el `auth_identities.id` del JWT, sin pasar por `resolve_domain_user_id`

### Requirement: El invariante de identidad está documentado para futuros agentes
El sistema SHALL documentar el invariante en `docs/ARQUITECTURA.md` y en las instrucciones de agentes (`CLAUDE.md`/KB), de modo que distinga `usuario.id` (FKs de dominio) de `auth_identities.id` (identidad/auditoría) y señale `resolve_domain_user_id` como único puente, incluyendo la excepción de auditoría.

#### Scenario: Documentación describe el puente y la excepción
- **WHEN** un agente lee `docs/ARQUITECTURA.md` o `CLAUDE.md`
- **THEN** encuentra una sección que explica cuándo usar cada identificador, cómo resolver el puente, y la excepción de `audit.actor_user_id`
