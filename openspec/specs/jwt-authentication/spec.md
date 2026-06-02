## ADDED Requirements

### Requirement: Login con email y password

El sistema SHALL exponer `POST /api/auth/login` que recibe `email` y `password`, normaliza el email (lowercase + trim), localiza la identidad por su hash determinista dentro del tenant, y verifica la password con **Argon2id**. Si las credenciales son válidas y el usuario no tiene 2FA activo, el sistema SHALL emitir un access token JWT y un refresh token. Las credenciales inválidas SHALL devolver `401` sin revelar si el email existe.

#### Scenario: Login exitoso sin 2FA
- **WHEN** un usuario activo sin 2FA envía email y password correctos
- **THEN** el sistema verifica la password con Argon2id y responde `200` con `access_token`, `refresh_token` y `token_type="bearer"`

#### Scenario: Password incorrecta
- **WHEN** un usuario existente envía una password incorrecta
- **THEN** el sistema responde `401` con un mensaje genérico y NO emite tokens

#### Scenario: Email inexistente
- **WHEN** se envía un email que no corresponde a ninguna identidad del tenant
- **THEN** el sistema responde `401` con el mismo mensaje genérico que para password incorrecta (no enumera usuarios) y ejecuta una verificación dummy para no filtrar timing

#### Scenario: Usuario inactivo
- **WHEN** un usuario con `is_active=False` envía credenciales correctas
- **THEN** el sistema responde `401` y NO emite tokens

### Requirement: Emisión de access token JWT con claims mínimos

El access token SHALL ser un JWT firmado (HS256 con `SECRET_KEY`) con expiración de **15 minutos** y los claims mínimos `sub` (user_id UUID), `tenant_id`, `roles`, `iat`, `exp` y `type="access"`. El token SHALL NOT contener permisos (se resuelven server-side).

#### Scenario: Claims del access token
- **WHEN** se emite un access token tras un login válido
- **THEN** el token decodificado contiene `sub`, `tenant_id`, `roles`, `iat`, `exp` y `type="access"`, y `exp - iat` equivale a 15 minutos

#### Scenario: Sin permisos en el token
- **WHEN** se inspeccionan los claims de un access token emitido
- **THEN** no existe ningún claim de permisos finos; solo el snapshot de `roles`

### Requirement: Verificación de identidad solo desde el token firmado

El sistema SHALL derivar la identidad, el tenant y los roles **exclusivamente** del access token JWT verificado. Cualquier identificador presente en query string, body o headers (distinto del propio Bearer token) SHALL ser ignorado como fuente de identidad.

#### Scenario: Tampering de identidad por parámetro
- **WHEN** una request autenticada incluye un `user_id` o `tenant_id` en query/body/header distinto del del token
- **THEN** el sistema usa los valores del token verificado e ignora los de la request

#### Scenario: Firma del token alterada
- **WHEN** se presenta un JWT con la firma modificada
- **THEN** el sistema responde `401` y no resuelve ninguna identidad
