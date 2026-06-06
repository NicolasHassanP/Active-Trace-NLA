## ADDED Requirements

### Requirement: Solicitud de recuperación de contraseña

El sistema SHALL exponer `POST /api/auth/forgot` que recibe un `email`. Si existe una identidad para ese email en el tenant, el sistema SHALL generar un token de un solo uso, persistir su **hash** con una expiración corta (default 30 min) y entregarlo al puerto de envío de email. La respuesta SHALL ser **uniforme** exista o no el email (no enumera usuarios).

#### Scenario: Forgot con email existente
- **WHEN** se solicita recuperación para un email que existe en el tenant
- **THEN** el sistema crea un token de recuperación (persistido por hash, con `expires_at`), lo entrega al puerto de envío y responde `200`/`202` con mensaje genérico

#### Scenario: Forgot con email inexistente
- **WHEN** se solicita recuperación para un email que no existe
- **THEN** el sistema responde con el **mismo** mensaje genérico y NO genera token

### Requirement: Reseteo de contraseña con token de un solo uso

El sistema SHALL exponer `POST /api/auth/reset` que recibe el token de recuperación y una nueva password. El sistema SHALL validar que el token coincide (por hash), está vigente y no fue usado; al aplicarlo SHALL marcar `used_at`, invalidar los demás tokens del usuario, setear el nuevo `password_hash` (Argon2id) y **revocar todas las sesiones de refresh** del usuario.

#### Scenario: Reset con token válido
- **WHEN** se presenta un token de recuperación vigente y no usado con una nueva password
- **THEN** el sistema setea el nuevo hash Argon2id, marca el token como usado y responde `200`

#### Scenario: Reuso del token de recuperación
- **WHEN** se presenta un token de recuperación que ya fue usado
- **THEN** el sistema responde `400`/`401` y no cambia la password

#### Scenario: Token de recuperación expirado
- **WHEN** se presenta un token cuya `expires_at` ya pasó
- **THEN** el sistema responde `400`/`401` y no cambia la password

#### Scenario: Reset revoca sesiones activas
- **WHEN** un reset se completa con éxito
- **THEN** todas las sesiones de refresh previas del usuario quedan revocadas y exigen re-login
