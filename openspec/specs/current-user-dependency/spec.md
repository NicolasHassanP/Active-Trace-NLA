## ADDED Requirements

### Requirement: Dependency get_current_user resuelve identidad desde el JWT

El sistema SHALL proveer una dependency `get_current_user` que extrae el `Authorization: Bearer <jwt>`, verifica la firma, la expiración y que `type=="access"`, y devuelve un value object con `user_id`, `tenant_id` y `roles` tomados **exclusivamente** del token verificado. La dependency SHALL NOT consultar la DB para resolver la identidad (el access token es stateless).

#### Scenario: Token válido resuelve CurrentUser
- **WHEN** una request presenta un access token válido y vigente
- **THEN** `get_current_user` devuelve `user_id`, `tenant_id` y `roles` decodificados del token

#### Scenario: Sin header Authorization
- **WHEN** una request protegida no presenta `Authorization: Bearer`
- **THEN** el sistema responde `401`

#### Scenario: Token expirado
- **WHEN** una request presenta un access token cuya expiración ya pasó
- **THEN** el sistema responde `401`

#### Scenario: Token de tipo incorrecto
- **WHEN** se presenta un token bien firmado pero con `type` distinto de `access` (p. ej. un `mfa_token`)
- **THEN** el sistema responde `401`

### Requirement: El tenant del repository proviene del CurrentUser

El sistema SHALL construir el `TenantScopedRepository` usando el `tenant_id` obtenido del `CurrentUser` (derivado del token), nunca de un parámetro de la request. Esto conecta la fuente de tenant real (JWT) al mecanismo de scope que C-02 dejó preparado.

#### Scenario: El scope del repository usa el tenant del token
- **WHEN** un endpoint autenticado construye un repository vía la factory de tenancy
- **THEN** el repository queda scopeado al `tenant_id` del token y no a ningún `tenant_id` recibido en la request

#### Scenario: Aislamiento entre tenants se preserva
- **WHEN** un usuario del tenant A presenta su token e intenta operar pasando un `tenant_id` del tenant B en la request
- **THEN** las operaciones quedan scopeadas al tenant A (el del token) y no acceden a datos del tenant B
