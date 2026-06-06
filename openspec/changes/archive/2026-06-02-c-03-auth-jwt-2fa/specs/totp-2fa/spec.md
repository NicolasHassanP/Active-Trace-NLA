## ADDED Requirements

### Requirement: Enrolamiento de 2FA TOTP

El sistema SHALL exponer `POST /api/auth/2fa/enroll` (requiere sesión autenticada) que genera un secreto TOTP, lo persiste **cifrado** (AES-256) con `totp_enabled=False`, y devuelve el secreto y el URI `otpauth://` para el código QR. El secreto en claro SHALL NOT persistirse ni registrarse en logs.

#### Scenario: Enroll genera secreto cifrado
- **WHEN** un usuario autenticado solicita enrolar 2FA
- **THEN** el sistema genera un secreto, lo guarda cifrado con `totp_enabled=False`, y responde con el secreto y el `otpauth://` URI

### Requirement: Verificación de activación de 2FA

El sistema SHALL exponer `POST /api/auth/2fa/verify` que recibe un código TOTP; si el código valida contra el secreto enrolado (tolerancia de ±1 ventana de 30s), el sistema SHALL marcar `totp_enabled=True`.

#### Scenario: Código de activación válido
- **WHEN** el usuario envía un código TOTP correcto tras enrolar
- **THEN** el sistema activa 2FA (`totp_enabled=True`) y responde `200`

#### Scenario: Código de activación inválido
- **WHEN** el usuario envía un código TOTP incorrecto
- **THEN** el sistema responde `400`/`401` y `totp_enabled` permanece en `False`

### Requirement: Gate de 2FA entre credenciales y emisión de sesión

Cuando un usuario con `totp_enabled=True` presenta credenciales válidas en el login, el sistema SHALL NOT emitir access/refresh directamente; en su lugar SHALL devolver un **challenge** (`mfa_token` firmado, de corta vida, `type="mfa"`). El sistema SHALL emitir la sesión solo cuando se presente el `mfa_token` junto a un código TOTP válido.

#### Scenario: Login con 2FA devuelve challenge
- **WHEN** un usuario con 2FA activo envía credenciales válidas
- **THEN** el sistema responde `200` con un `mfa_token` de corta vida y `mfa_required=true`, sin access ni refresh

#### Scenario: Challenge con código TOTP válido emite sesión
- **WHEN** se presenta un `mfa_token` vigente junto a un código TOTP correcto
- **THEN** el sistema emite access + refresh y responde `200`

#### Scenario: Challenge con código TOTP inválido
- **WHEN** se presenta un `mfa_token` vigente con un código TOTP incorrecto
- **THEN** el sistema responde `401` y no emite sesión

#### Scenario: mfa_token expirado
- **WHEN** se presenta un `mfa_token` cuya expiración ya pasó
- **THEN** el sistema responde `401` y exige reiniciar el login
