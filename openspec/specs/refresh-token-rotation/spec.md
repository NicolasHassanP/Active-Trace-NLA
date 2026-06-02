## ADDED Requirements

### Requirement: Refresh token opaco persistido por hash

El refresh token SHALL ser un valor opaco aleatorio (no un JWT). El sistema SHALL persistir únicamente su **hash** (SHA-256) en una sesión de refresh con `auth_identity_id`, `tenant_id`, `family_id`, `expires_at`, `revoked_at` y `rotated_at`. El valor en claro SHALL existir solo en el cliente.

#### Scenario: Persistencia por hash
- **WHEN** se emite un refresh token
- **THEN** la fila de sesión almacena el hash del token, nunca el valor en claro

### Requirement: Rotación del refresh token

El sistema SHALL exponer `POST /api/auth/refresh` que recibe un refresh token vigente, lo **invalida** (marca `rotated_at`/`revoked_at`) y emite un par nuevo (access + refresh) dentro de la **misma `family_id`**.

#### Scenario: Rotación exitosa
- **WHEN** se presenta un refresh token vigente y no revocado
- **THEN** el sistema marca la sesión como rotada, emite un nuevo access y un nuevo refresh en la misma familia, y responde `200`

#### Scenario: Refresh expirado
- **WHEN** se presenta un refresh token cuya `expires_at` ya pasó
- **THEN** el sistema responde `401` y no emite tokens

### Requirement: Detección de reuse de refresh token

Si se presenta un refresh token **ya rotado o revocado** (reuse), el sistema SHALL interpretarlo como compromiso y revocar **toda la familia** (`family_id`), rechazando la operación con `401`.

#### Scenario: Reuse de un token ya rotado
- **WHEN** se presenta un refresh token que ya fue usado para rotar
- **THEN** el sistema revoca todas las sesiones de su `family_id` y responde `401`

#### Scenario: Tras reuse, el token nuevo legítimo también queda invalidado
- **WHEN** se detecta reuse y se revoca la familia, y luego se intenta usar el refresh más reciente de esa familia
- **THEN** el sistema responde `401` (la familia completa quedó revocada)

### Requirement: Logout revoca la sesión

El sistema SHALL exponer `POST /api/auth/logout` que revoca (marca `revoked_at`) la sesión de refresh activa presentada.

#### Scenario: Logout invalida el refresh
- **WHEN** un usuario hace logout con su refresh token vigente
- **THEN** la sesión queda revocada y un refresh posterior con ese token responde `401`
