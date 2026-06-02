## Context

C-01 dejó el esqueleto Clean Architecture y reservó los slots `core/security.py`, `core/tenancy.py`, `core/dependencies.py` (con comentarios `RESERVADO → C-03`). C-02 (gobernanza CRÍTICA) construyó la base de persistencia: `Tenant` raíz, mixins (`UUIDMixin`/`TimestampMixin`/`SoftDeleteMixin`/`TenantMixin`/`TenantScopedBase`), `TenantScopedRepository[ModelT]` cuyo `tenant_id` es **estado inyectado** (no parámetro de método), soft delete transversal y AES-256 (`encrypt`/`decrypt` + `EncryptedString` TypeDecorator). C-02 dejó explícito un cabo suelto que C-03 cierra: el `tenant_id` real proviene del JWT, y la **búsqueda por email se resuelve con un hash determinista separado del campo cifrado** (el `EncryptedString` usa nonce aleatorio, no es buscable por igualdad).

C-03 (gobernanza **CRÍTICA** — auth) construye el flujo de autenticación propio (ADR-001): login email+password con Argon2id, access token JWT de 15 min + refresh con rotación, 2FA TOTP opcional, recuperación de contraseña, rate limiting y la dependency `get_current_user`. Es el primer eslabón del camino crítico y la fuente única de identidad/tenant/roles para todo el resto del sistema.

Restricciones de contrato (no negociables): identidad/tenant/roles **solo** desde el JWT verificado; passwords con Argon2id; secretos/PII en reposo con AES-256; multi-tenancy row-level; Pydantic `extra='forbid'`; snake_case; flujo Routers→Services→Repositories→Models; soft delete; identidad por UUID interno (el legajo nunca es credencial); ≤500 LOC/archivo; una migración por cambio de schema; Strict TDD con PostgreSQL efímero real.

## Goals / Non-Goals

**Goals:**

- Login email+password con verificación Argon2id y emisión de access token JWT (15 min) + refresh con rotación; claims mínimos `sub`/`tenant_id`/`roles`/`exp`.
- Rotación de refresh con invalidación del token usado y **detección de reuse** (un refresh ya consumido se rechaza y revoca la familia/sesión).
- Logout que revoca la sesión de refresh activa.
- 2FA TOTP opcional por usuario: enrolamiento + verificación, con **gate** entre credenciales válidas y emisión de sesión.
- Recuperación de contraseña: `forgot` (token de un solo uso, expiración corta) + `reset` (consume el token, invalida los anteriores, setea nuevo hash).
- Rate limiting 5/60s por (IP + email) en login y forgot, fail-closed.
- Dependency `get_current_user` que deriva identidad/tenant/roles del JWT verificado, y conexión del `tenant_id` real al `TenantScopedRepository` vía `core/tenancy.py`.
- Tabla(s) de auth-owned con la identidad mínima para autenticar, lookup por email-hash determinista, secretos en reposo cifrados.

**Non-Goals:**

- Entidad `Usuario` completa (perfil, legajo, datos académicos) → **C-07**. C-03 entrega solo el subconjunto de identidad necesario para autenticar.
- Catálogo rol×permiso, `require_permission`, matriz RBAC → **C-04**. C-03 emite los `roles` en el token como snapshot, pero no resuelve permisos.
- Audit log de los eventos de auth → **C-05** (C-03 deja los eventos identificables para que C-05 los consuma).
- Impersonación (ADR-004), Moodle SSO de alumnos (Fase 2), envío real de email del token de recuperación (C-03 genera y persiste el token; el despacho usa el contrato del worker de comunicaciones, módulo posterior — en C-03 se deja un puerto de envío mockeable).

## Decisions

### D1 — Tabla `auth_identity` auth-owned, reconciliada por `Usuario` en C-07

C-03 necesita verificar una password contra **algo**, pero la entidad `Usuario` es C-07. Decisión: crear una tabla **`auth_identity`** que contiene el subconjunto mínimo de identidad para autenticar, no el perfil completo. Campos: `id` (UUID PK — es el `sub`/`user_id` del token), `tenant_id` (FK, indexada, hereda `TenantScopedBase`), `email_encrypted` (`EncryptedString`, AES-256), `email_hash` (deterministic HMAC-SHA256, **único por tenant**, indexado, para lookup), `password_hash` (Argon2id), `roles` (JSONB array de strings — snapshot; la matriz fina llega en C-04), `is_active` (bool), `totp_secret_encrypted` (`EncryptedString`, nullable), `totp_enabled` (bool), + timestamps + soft delete.

**Por qué una tabla auth-owned y no esperar a `Usuario`**: C-03 está antes de C-07 en el roadmap y desbloquea el camino crítico. Acoplar auth a la entidad de perfil completa invierte la dependencia. La tabla se diseña para que C-07 la **absorba/reconcilie** (probablemente `Usuario` referenciará o se fusionará con `auth_identity` por `id` compartido). Frontera explícita: C-03 NO agrega perfil, legajo, ni relaciones académicas.

**Alternativa descartada**: meter las credenciales directamente en una tabla `Usuario` adelantada. Se descarta: viola el alcance (C-07) y arrastra decisiones de modelo de perfil que aún no corresponden.

### D2 — Lookup por email vía hash determinista HMAC-SHA256, separado del campo cifrado

El email se guarda **dos veces**: `email_encrypted` (AES-256 con nonce aleatorio, no buscable) y `email_hash` (HMAC-SHA256 del email normalizado —lowercase/trim— con clave derivada de `SECRET_KEY`). El login hace `WHERE email_hash = :h AND tenant_id = :t`. El hash es determinista (mismo email → mismo hash) pero no reversible y resistente a rainbow tables por la clave HMAC.

**Por qué HMAC y no SHA simple**: SHA del email es enumerable/atacable con diccionarios de emails; HMAC con clave secreta lo evita. Esto cierra el cabo suelto que C-02 dejó documentado.

**Unicidad**: índice único compuesto `(tenant_id, email_hash)` — un email es único dentro de un tenant, pero el mismo email puede existir en tenants distintos.

### D3 — JWT: access corto stateless, refresh opaco stateful con rotación

- **Access token**: JWT firmado HS256 con `SECRET_KEY`, claims `sub` (user_id), `tenant_id`, `roles`, `exp` (now + 15 min), `iat`, `type="access"`. **Stateless**: `get_current_user` lo verifica por firma+exp sin tocar la DB. No lleva permisos (se resuelven en C-04).
- **Refresh token**: valor **opaco** aleatorio (secrets.token_urlsafe), NO un JWT. Se persiste su **hash** (SHA-256) en la tabla `refresh_session`, junto con `auth_identity_id`, `tenant_id`, `family_id` (UUID de la familia de rotación), `expires_at` (TTL largo configurable, default 14 días), `revoked_at`, `rotated_at`. El cliente guarda el valor en claro; el servidor solo el hash.

**Por qué refresh opaco stateful y access JWT stateless**: el access corto evita golpear la DB en cada request (performance) y el refresh stateful permite **revocación real** (logout, detección de reuse) — algo imposible con un JWT puro sin lista de revocación. Es el patrón estándar recomendado.

### D4 — Rotación de refresh con detección de reuse por familia

Cada `refresh` valida el token recibido contra su hash: si está vigente y no revocado, se **marca `revoked_at`/`rotated_at`** y se emite un refresh nuevo en la **misma `family_id`**. Si llega un refresh **ya rotado/revocado** (reuse), se interpreta como robo: se **revoca toda la familia** (`family_id`) y se rechaza con 401. Logout marca `revoked_at` en la sesión activa.

**Por qué familias**: la detección de reuse es la defensa clave de la rotación; agrupar por familia permite invalidar la cadena completa ante un reuse sin afectar otras sesiones del mismo usuario (otro dispositivo).

**Alternativa descartada**: refresh JWT con jti en denylist. Más estado efímero y TTL-bound; la tabla de sesiones es más simple de auditar y consistente con soft-delete/append-only del proyecto.

### D5 — 2FA TOTP opcional con gate en el login

- **Enroll** (`/2fa/enroll`, requiere sesión válida): genera un secreto TOTP (pyotp), lo guarda **cifrado** (`EncryptedString`) con `totp_enabled=False`, y devuelve el secreto/URI para el QR. **Verify** (`/2fa/verify`): el usuario manda un código; si valida contra el secreto, `totp_enabled=True`.
- **Gate en login**: si `totp_enabled=True`, el login —tras validar credenciales con Argon2id— NO emite tokens; devuelve un **challenge de corta vida** (`mfa_token` firmado, `exp` ~5 min, `type="mfa"`) que identifica al usuario que ya pasó credenciales. El cliente reenvía `mfa_token` + código TOTP a `/login` (o `/2fa/challenge`); recién ahí, con el código válido, se emiten access+refresh.

**Por qué el gate entre credenciales y emisión**: es exactamente el punto que pide FL-01 ("luego del paso 3 y antes del paso 4"). El `mfa_token` evita re-enviar la password y acota la ventana. Tolerancia TOTP: ±1 ventana (30s) para drift de reloj.

### D6 — Recuperación de contraseña con token de un solo uso hasheado

`forgot` busca por `email_hash`; si existe, genera un token opaco aleatorio, persiste su **hash** en `password_recovery_token` (`auth_identity_id`, `tenant_id`, `token_hash`, `expires_at` ~30 min, `used_at`) y lo entrega al puerto de envío de email (mockeable en C-03). **Respuesta uniforme**: `forgot` responde igual exista o no el email (no enumera usuarios). `reset` recibe el token + nueva password: valida hash+vigencia+no usado, marca `used_at`, **invalida los demás tokens del usuario**, setea el nuevo `password_hash` Argon2id y **revoca todas las refresh sessions** del usuario (forzar re-login).

**Por qué hashear el token de recuperación**: si la DB se filtra, los tokens no son usables (mismo principio que el refresh).

### D7 — Rate limiting 5/60s por (IP + email), fail-closed

Login y forgot limitan a 5 intentos por ventana de 60s por la clave `(client_ip, email_normalizado)`. Se usa **slowapi** (sobre `limits`) con backend en memoria para el MVP single-instance (configurable a Redis cuando haya múltiples instancias). Exceder el límite → `429`. **Fail-closed**: si el backend del limitador falla, se deniega.

**Por qué IP+email y no solo IP**: solo-IP castiga NAT compartido; solo-email permite DoS dirigido. La combinación es el balance estándar contra fuerza bruta de credenciales.

**Alternativa considerada**: limiter casero con tabla en DB. Se descarta para el MVP por costo de I/O por request; slowapi es estándar y testeable.

### D8 — `get_current_user` y conexión del tenant al repository

`core/dependencies.py` implementa `get_current_user(request) -> CurrentUser` que: extrae `Authorization: Bearer <jwt>`, verifica firma+exp+`type=="access"` con `core/security.decode_access_token`, y devuelve un value object `CurrentUser(user_id, tenant_id, roles)`. **Jamás** lee identidad de query/body/header fuera del propio token firmado. `core/tenancy.py` gana una dependency `get_tenant_scoped_repository_factory` que toma `tenant_id` **del `CurrentUser`** (no de la request) y construye el `TenantScopedRepository` de C-02. Errores: sin/inválido token → 401; token bien firmado de otra cosa → 401.

**Por qué un value object y no el modelo ORM**: el token es stateless; `get_current_user` no debe golpear la DB. La identidad del request vive en el token verificado, fiel a la regla de oro.

### D9 — Ampliación de `core/security.py` (sin romper C-02)

Se añaden a `core/security.py` (respetando ≤500 LOC; si excede, partir en `core/security/` paquete con `crypto.py`, `passwords.py`, `tokens.py`): `hash_password`/`verify_password` (Argon2id vía argon2-cffi `PasswordHasher`), `encode_access_token`/`decode_access_token`/`encode_mfa_token`/`decode_mfa_token` (python-jose HS256), `email_lookup_hash` (HMAC-SHA256), `generate_opaque_token`/`hash_opaque_token`, helpers TOTP (`generate_totp_secret`, `verify_totp`). El AES-256 existente se reutiliza tal cual.

### D10 — Migración Alembic: `002_create_auth_tables`

C-02 ya creó `001_create_tenants_table`. **Decisión cerrada (OQ-2)**: auth toma **`002_create_auth_tables`** (orden cronológico real de implementación); RBAC (C-04) tomará `003`. Esta migración crea `auth_identity`, `refresh_session`, `password_recovery_token` (el secreto y email de 2FA viven como columnas de `auth_identity`). Una sola migración para todas las tablas de auth de este change.

### D11 — Estructura de archivos (Clean Architecture, ≤500 LOC c/u)

- `app/models/auth.py` — `AuthIdentity`, `RefreshSession`, `PasswordRecoveryToken`.
- `app/repositories/auth_identity_repository.py` — lookup por `(tenant_id, email_hash)` donde el `tenant_id` se resuelve del contexto público (subdominio / header `X-Tenant`, OQ-1 resuelta) y `refresh_session_repository.py`, `recovery_token_repository.py`.
- `app/services/auth_service.py` — orquesta login/refresh/logout/2fa/recovery (lógica de negocio, sin SQL directo).
- `app/schemas/auth.py` — DTOs Pydantic `extra='forbid'` (LoginRequest, LoginResponse, TokenPair, RefreshRequest, MfaChallenge, MfaVerify, ForgotRequest, ResetRequest, Enroll responses).
- `app/api/v1/routers/auth.py` — endpoints, sin lógica de negocio.
- `app/core/security.py` (+helpers), `app/core/dependencies.py` (`get_current_user`), `app/core/tenancy.py` (factory tenant-scoped desde CurrentUser), `app/core/config.py` (+TTLs).

## Risks / Trade-offs

- **[Login necesita resolver el tenant antes de tener una sesión]** → El `TenantScopedRepository` de C-02 exige `tenant_id` por construcción, pero en el login aún no hay token. Mitigación: el repo de lookup de login es un repo **no tenant-scoped** que busca por `(tenant_id, email_hash)` donde el `tenant_id` se obtiene del **contexto público (subdominio / header `X-Tenant`, OQ-1 resuelta)**. Es la **única** excepción al scope-por-construcción, igual que `Tenant` (la raíz) tampoco usa el repo scoped — se documenta como excepción explícita y acotada al flujo de auth previo a la sesión.
- **[Rate limiter en memoria no escala a múltiples instancias]** → Mitigación: interfaz desacoplada; backend configurable a Redis sin cambiar la lógica. MVP single-instance lo tolera.
- **[`roles` como snapshot en el token puede quedar stale si cambian antes del refresh]** → Trade-off aceptado: ventana máxima = TTL del access (15 min). C-04 puede refrescar roles en cada rotación de refresh.
- **[Detección de reuse puede dar falsos positivos con clientes que reintentan refresh por red]** → Mitigación: tolerar una pequeña gracia (reuso del token inmediatamente anterior dentro de N segundos) es una opción; el MVP es estricto (revoca familia) por seguridad. Documentado.
- **[2FA secret y email cifrados no son buscables]** → Aceptado: el lookup es por `email_hash` (D2); el secreto TOTP no necesita búsqueda.
- **[Ampliar `core/security.py` puede pasar 500 LOC]** → Mitigación: partir en paquete `core/security/` si excede (D9). Respetar la regla dura.
- **[Envío real del email de recuperación no existe aún]** → Mitigación: puerto de envío inyectable y mockeable; el token se persiste y el flujo funciona end-to-end en tests; el despacho real se conecta con el módulo de comunicaciones.

## Migration Plan

Desplegar `alembic upgrade head` aplica `002_create_auth_tables` (crea `auth_identity`, `refresh_session`, `password_recovery_token` con sus índices y el único compuesto `(tenant_id, email_hash)`). No hay datos de auth previos que migrar. Para operar, cada tenant necesita al menos un `auth_identity` (el primer ADMIN); su provisión inicial (FL-12 paso 2) **se difiere a C-07** (OQ-3) — en C-03 los tests usan fixtures de `auth_identity`, no hay seed ni endpoint de alta. Rollback: `alembic downgrade -1` elimina las tres tablas; al no haber FKs entrantes todavía (Usuario es C-07), el downgrade es limpio. Las nuevas dependencias (`pyotp`, `slowapi`) se agregan a `pyproject.toml` y se instalan en build.

## Resolved Questions

Las cuatro preguntas abiertas fueron resueltas por el usuario antes del apply:

- **OQ-1 — `tenant_id` en el login → tenant en el contexto público (subdominio / header `X-Tenant`)**. El tenant se resuelve del subdominio o del header `X-Tenant` **antes** del login; el lookup es `WHERE tenant_id = :t AND email_hash = :h`. Permite el **mismo email en distintos tenants**, consistente con el índice único compuesto `(tenant_id, email_hash)`. El repo de lookup de login recibe el `tenant_id` resuelto del contexto público (única excepción acotada al scope-por-construcción de C-02, igual que `Tenant`).
- **OQ-2 — Numeración de migración → auth toma `002`**. Orden cronológico real de implementación; RBAC (C-04) tomará `003`. Ver D10.
- **OQ-3 — Primer ADMIN → diferido a C-07**. C-03 entrega solo el motor de auth; no hay seed ni endpoint de alta. Los tests de C-03 usan **fixtures de `auth_identity`** sobre la DB efímera.
- **OQ-4 — Rate limiter → in-memory (slowapi)** para el MVP single-instance, con interfaz desacoplada para migrar a Redis cuando haya múltiples instancias. Ver D7.
