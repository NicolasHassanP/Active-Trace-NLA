## Context

Tras C-01..C-06 el sistema tiene: identidad desde JWT (`get_current_user` → `CurrentUser(user_id, tenant_id, roles)`), tenancy row-level (`TenantScopedRepository` filtra por `tenant_id` y `deleted_at IS NULL`), RBAC fino (`require_permission(codigo)`, fail-closed), auditoría append-only, y el catálogo estructural (Carrera/Cohorte/Materia). La última migración aplicada es **005** (cadena 001→002→003→004→005).

C-07 agrega la **identidad de negocio** (`Usuario`) y el **eje de autorización contextual** (`Asignacion`). Es governance **CRÍTICO** (identidad + PII bancaria/fiscal). El diseño se apoya en infraestructura ya construida y verificada, que se REUSA sin modificar:

- **`app.core.security.crypto.EncryptedString`** (C-02): `TypeDecorator` SQLAlchemy que cifra/descifra transparente con **AES-256-GCM** (nonce de 12 bytes por valor, no determinístico, autenticado). La columna en DB siempre es ciphertext; la app siempre ve plaintext. La búsqueda por igualdad sobre la columna cifrada es intencionalmente imposible.
- **`app.core.security.passwords.email_lookup_hash`** (C-03): blind index determinístico = HMAC-SHA256(SECRET_KEY, normalize(email)) → hex de 64 chars. Resistente a rainbow tables. Ya usado por `AuthIdentity.email_hash` con unicidad `(tenant_id, email_hash)`.
- **`AuthIdentity`** (C-03) ya implementa exactamente el patrón email_encrypted + email_hash que `Usuario` replicará para `email`.

Invariantes de dominio que constriñen el diseño (todas cerradas en la KB):
- **PII cifrada en reposo** (regla dura #12, ARQUITECTURA §5.4): `email`, `dni`, `cuil`, `cbu`, `alias_cbu` cifrados; nunca texto plano en logs.
- **Identidad por UUID** (regla dura #14): `legajo` es atributo de negocio, nunca PK ni credencial.
- **Unicidad `(tenant_id, email)`** (KB §E4) sobre email cifrado → requiere blind index.
- **Vigencia temporal** (KB §3 §5): vencida no autoriza, se conserva.
- **Multi-tenant row-level** (regla dura #9) e **identidad desde la sesión** (regla dura #8).
- **Soft delete siempre** (regla dura #13); unicidad vía índice parcial `WHERE deleted_at IS NULL`.
- **RBAC fail-closed** (regla dura #10).

## Goals / Non-Goals

**Goals:**
- Persistir `Usuario` tenant-scoped con soft-delete y PII cifrada AES-256 (`email`, `dni`, `cuil`, `cbu`, `alias_cbu`), reusando `EncryptedString`.
- Garantizar unicidad `(tenant_id, email)` sobre email cifrado vía columna blind index `email_hash` + índice único parcial.
- Persistir `Asignacion` tenant-scoped con soft-delete, vínculo a `Usuario`/rol/contexto, `responsable_id` self-FK, ventana `desde`/`hasta`, y `estado_vigencia` **derivado en runtime** (nunca columna).
- Exponer ABM de usuarios bajo `/api/v1/admin/usuarios` (permiso `usuarios:gestionar`) y CRUD de asignaciones bajo `/api/v1/asignaciones` (permiso `equipos:asignar`), fail-closed.
- Aislamiento multi-tenant verificado en usuarios y asignaciones (incluyendo que el `responsable_id` y el contexto sean del mismo tenant).
- Migración **006** con tablas `usuario` y `asignacion`, enum `rol_asignacion`, índices, y seed idempotente de permisos.

**Non-Goals:**
- NO se construye el ABM de equipos docentes (mis-equipos, masiva, clonar, exportar) — eso es C-08 y consume `Asignacion`.
- NO se construye `Dictado` ni se altera el catálogo estructural de C-06.
- NO se modifica el mecanismo RBAC, auth, tenancy ni auditoría; C-07 solo los consume. **El apply NO debe tocar `require_permission` ni la resolución de permisos efectivos** (OQ-4 resuelta).
- NO se implementa el cálculo de permisos efectivos por vigencia en el motor de autorización (la derivación de `estado_vigencia` se entrega SOLO como helper de dominio reusable; integrarla en `require_permission` contextual es un change posterior dedicado — OQ-4).
- NO se construye el endpoint de lectura de PII financiera completa (CBU/CUIL/DNI en claro): es una **dependencia forward** de un endpoint FINANZAS en un change posterior (OQ-3).
- NO se migran/backfillean datos de `AuthIdentity` a `Usuario` en esta migración (ver D9; el backfill, si se decide, es tarea separada y reversible).
- NO se introduce el frontend (C-21+).

## Decisions

### D1 — Migración 006, NO 005 (corrección de CHANGES.md / roadmap)
El texto del roadmap dice "Migración 005", pero está **STALE**: la 005 ya está ocupada por C-06 (estructura académica). La cadena aplicada es 001→002→003→004→005. La próxima revisión libre es **006**. La migración será `backend/alembic/versions/006_create_usuarios_asignaciones.py` con `revision="006"`, `down_revision="005"`. Se sigue el estilo de 003/005: `CREATE TABLE` con SQL explícito, índices nombrados, enums idempotentes (patrón `DO $$ ... EXCEPTION WHEN duplicate_object THEN NULL ... $$`), seed idempotente de permisos.
**Alternativa descartada**: respetar el "005" del roadmap → colisión de revisión, rompe `alembic upgrade`.

### D2 — PII cifrada con `EncryptedString` (AES-256-GCM, app-layer) — NO pgcrypto
Los cinco campos PII (`email`, `dni`, `cuil`, `cbu`, `alias_cbu`) se mapean con `EncryptedString` (cifrado/descifrado transparente en la capa ORM con AES-256-GCM, clave de `ENCRYPTION_KEY`). Es la decisión ya establecida y verificada del repo (C-02), usada por `AuthIdentity`.
**Por qué app-layer y no pgcrypto**: (a) la clave nunca vive en la DB ni viaja en queries SQL (con pgcrypto la clave aparecería en el statement → riesgo en logs de Postgres); (b) ya existe el helper, los tests y el patrón; (c) es agnóstico del motor. **Trade-off aceptado**: el cifrado no determinístico hace la PII no consultable por igualdad — para `email` se resuelve con el blind index (D3); `dni`/`cuil`/`cbu`/`alias_cbu` NO necesitan búsqueda por igualdad en C-07 (la búsqueda de usuarios es por `nombre`/`apellidos`/`legajo`, que NO son PII cifrada).
La columna en DB es `VARCHAR`/`TEXT` (el ciphertext base64url). Nunca se loguea el plaintext: los `__repr__` de los modelos excluyen PII (igual que `AuthIdentity.__repr__`).

### D3 — Unicidad `(tenant_id, email)` vía blind index determinístico `email_hash`
Como el email cifrado con AES-GCM es no determinístico (mismo input → distinto ciphertext), no se puede indexar por unicidad ni buscar por él. Se replica el patrón de `AuthIdentity`:
- Columna `email_encrypted` (`EncryptedString`) — el valor para mostrar / recuperar.
- Columna `email_hash` (`String(64)`, indexada) — `email_lookup_hash(email)` = HMAC-SHA256(SECRET_KEY, lower(strip(email))).
- **Índice único PARCIAL** `ux_usuario_tenant_email_hash ON usuario (tenant_id, email_hash) WHERE deleted_at IS NULL` → unicidad por tenant que convive con soft-delete (reuso de email tras baja).
El service valida unicidad por `email_hash` ANTES de insertar (→ 409 con mensaje de dominio claro); el índice parcial es la defensa en profundidad que traduce el `IntegrityError` a 409.
**Alternativa descartada**: cifrado determinístico (AES-SIV) para el email → reintroduce el riesgo de igualdad-de-ciphertext y exige otra primitiva; el blind index HMAC ya existe y es más seguro (no revela igualdad sin la clave).

### D4 — `estado_vigencia` DERIVADO, nunca columna
`estado_vigencia` NO es columna en `asignacion`. Se calcula con un helper puro de dominio:
`vigente := (desde <= hoy) AND (hasta IS NULL OR hasta >= hoy)`; en caso contrario `vencida`.
La fecha "hoy" se toma como `date.today()` en la zona del sistema (UTC, consistente con `TIMESTAMPTZ`/`DATE` del resto del modelo). El `*Read` schema expone `estado_vigencia` como campo computado (Pydantic `computed_field` o resuelto por el service antes de serializar).
**Por qué derivado**: evita estados obsoletos (una asignación "vence" sola al pasar el tiempo, sin job que actualice una columna). Coincide con `Calificacion.aprobado` y otras derivaciones del modelo (KB §E5 lo marca explícitamente "derivado por fechas, no almacenado").

### D5 — `Asignacion.responsable_id` referencia a `Usuario` (NO a `Asignacion`), con validación de tenant
`responsable_id` es self-FK a `usuario.id` (`ON DELETE RESTRICT`, nullable). La KB §E5 dice "FK → Usuario (quién supervisa)". El service valida que el responsable, si se indica, exista y sea del MISMO tenant. **No** se implementa detección de ciclos en C-07: la jerarquía es usuario→usuario (no asignación→asignación), poco profunda y administrada manualmente por ADMIN/COORDINADOR; un chequeo de ciclos sería sobre-ingeniería aquí. Se documenta como riesgo y queda como mejora futura si la jerarquía se vuelve transitiva.
**Alternativa considerada**: `responsable_id` → `asignacion.id` (responsable es una asignación concreta). Descartada: la KB modela la supervisión persona↔persona, no asignación↔asignación; ata el responsable a una asignación que puede vencer.

### D6 — Modelos sobre `TenantScopedBase` (con soft-delete)
`Usuario` y `Asignacion` componen `TenantScopedBase` completo (`UUIDMixin` + `TenantMixin` + `TimestampMixin` + `SoftDeleteMixin`), igual que las entidades de catálogo de C-06. Habilita ABM, baja lógica e índices únicos parciales. Repositories sobre `TenantScopedRepository`.

### D7 — Enum `rol_asignacion` (PostgreSQL + Python), idempotente
Los roles de asignación (`PROFESOR`, `TUTOR`, `COORDINADOR`, `NEXO`, `ADMIN`, `FINANZAS`) se modelan como enum PostgreSQL `rol_asignacion` y enum Python `RolAsignacion(str, enum.Enum)`, con `create_type=False` en el modelo (lo crea la migración). Se sigue el patrón de `EstadoEstructura`/`PermisoScope`. ALUMNO se excluye: una asignación es del equipo docente/administrativo (la condición de alumno se modela en el padrón, C-09).
**Conftest**: el enum `rol_asignacion` se agrega a `_ensure_schema` (creación idempotente) y a la limpieza (`DROP TYPE IF EXISTS rol_asignacion CASCADE`), igual que `estado_estructura`.

### D8 — Permisos RBAC: reuso de `usuarios:gestionar` y `equipos:asignar` (YA sembrados en 003)
Ambos permisos YA existen en el catálogo desde la migración 003 (`_PERMISOS`/`_MATRIZ`): `usuarios:gestionar` (grant a ADMIN, global) y `equipos:asignar` (grant a COORDINADOR y ADMIN, global). **C-07 NO introduce permisos nuevos.** La migración 006 incluye, por consistencia con 005, un **seed idempotente** (`ON CONFLICT DO NOTHING`) que re-asegura ambos permisos y sus grants per-tenant — útil solo para tenants creados entre 003 y 006; es no-op para los existentes. Patrón EXACTO de 005: loop `SELECT id FROM tenants WHERE deleted_at IS NULL`, `INSERT ... ON CONFLICT ON CONSTRAINT uq_permiso_tenant_codigo DO NOTHING`, grant vía `INSERT ... SELECT ... ON CONFLICT ON CONSTRAINT uq_rol_permiso DO NOTHING`.
**CHECKPOINT RBAC (CRÍTICO)**: aunque idempotente y sin permisos nuevos, el seed toca RBAC — se surfacea para revisión del usuario antes de aplicar la migración.
- `/api/v1/admin/usuarios` → `require_permission("usuarios:gestionar")` (ADMIN).
- `/api/v1/asignaciones` → `require_permission("equipos:asignar")` (COORDINADOR, ADMIN).

### D9 — Reconciliación con `AuthIdentity`: FK opcional `auth_identity_id`, sin backfill en C-07
`AuthIdentity` (C-03) se diseñó como "subconjunto mínimo de auth, a reconciliar/absorber por `Usuario` en C-07". Decisión: `Usuario` agrega una **FK nullable `auth_identity_id` → auth_identities.id** (`ON DELETE SET NULL`, único parcial por tenant cuando no nulo), que vincula el usuario de negocio con su credencial de login. En C-07:
- La columna se crea pero el **backfill/relink masivo NO se ejecuta** (no hay datos de producción aún; sería una migración de datos aparte, reversible).
- No se altera el flujo de login de C-03 (sigue resolviendo desde `AuthIdentity`).
**Por qué agregarla ahora y no diferir**: evita una segunda migración de schema sobre `usuario` más adelante (regla "una migración por cambio de schema"); deja el gancho listo para que C-08+ y un futuro change de auth-reconciliation lo poblen.
**On-delete = `SET NULL` (RESUELTO, OQ-2)**: el `Usuario` es el registro de negocio y debe sobrevivir a la eliminación de su credencial; al borrarse una `AuthIdentity`, `auth_identity_id` pasa a NULL en lugar de bloquear el borrado. Se descarta `RESTRICT` (no hay invariante en la KB que exija que una identidad nunca se desvincule).

### D10 — Repositories, Service y Schemas (patrón C-06)
- **`backend/app/repositories/usuario_repository.py`**: `UsuarioRepository` (con `get_by_email_hash(email_hash)` para unicidad) y `AsignacionRepository` (con `list(usuario_id=..., rol=..., responsable_id=...)`), ambos sobre `TenantScopedRepository`. Si supera 500 LOC se divide por entidad.
- **`backend/app/services/usuario_service.py`**: `UsuarioService` (unicidad por email_hash, alta/edición/baja, derivación nula de PII en logs) y `AsignacionService` (validación de existencia/tenant de usuario y responsable y contexto; helper de `estado_vigencia`). Excepciones de dominio mapeadas a HTTP (409 conflicto unicidad, 404 no encontrado, 422 inconsistencia, 403 lo cubre `require_permission`).
- **`backend/app/schemas/usuario.py`**: `UsuarioCreate/Update/Read`, `AsignacionCreate/Update/Read`, todos con `ConfigDict(extra='forbid')`; los `*Read` con `from_attributes=True`, sin exponer `tenant_id`, y exponiendo PII solo según el contrato cerrado de OQ-3 (ver "Contrato de `UsuarioRead`"). `AsignacionRead` incluye `estado_vigencia` computado.
- **Routers**: `admin_usuarios.py` (prefix `/admin`, tag `usuarios`) y `asignaciones.py` (prefix `/asignaciones`), registrados en el agregador v1, cada ruta con `require_permission(...)` + `get_current_user`.

### D11 — Diseño de datos de `Usuario` (set §E4 completo + `auth_identity_id`) — RESUELTO (OQ-1, OQ-2)
La tabla `usuario` incluye, en la migración 006 (sin re-migración posterior):
- **PII cifrada** (`EncryptedString`, AES-256-GCM; columna DB = ciphertext): `email_encrypted`, `dni`, `cuil`, `cbu`, `alias_cbu`.
- **Blind index**: `email_hash` (`String(64)`, indexado) = `email_lookup_hash(email)` — soporta la unicidad de D3.
- **Identidad / negocio (§E4 completo)**: `nombre`, `apellidos`, `legajo` (opcional, nunca PK/credencial), `legajo_profesional`, `banco`, `regional`, `facturador` (Boolean), `estado`.
- **Reconciliación auth**: `auth_identity_id` (UUID, nullable, FK → `auth_identities.id`, `ON DELETE SET NULL`, único parcial por tenant cuando no nulo). Sin backfill en C-07.
- **Base**: `id` (UUID), `tenant_id`, `created_at`, `updated_at`, `deleted_at` (de `TenantScopedBase`).

### Contrato de `UsuarioRead` (exposición de PII) — RESUELTO (OQ-3)
`UsuarioRead` (read del ABM general bajo `/api/v1/admin/usuarios`) expone EXACTAMENTE este conjunto de campos y ningún otro:
- `id` (UUID)
- `email` (texto plano — el ADMIN lo necesita para gestión/contacto)
- `nombre`, `apellidos`
- `legajo` (puede ser null)
- `estado`
- `asignaciones` / `roles` — resumen de asignaciones/roles del usuario (id, rol, contexto, `estado_vigencia`)
- `created_at`, `updated_at`

**Regla de enmascaramiento / exclusión**: `dni`, `cuil`, `cbu`, `alias_cbu` **NO** se serializan en texto plano. La implementación por defecto los **omite** del schema; si un consumidor exige mostrarlos, solo se permiten **enmascarados** (últimos dígitos, p. ej. `****1234`). `tenant_id` y el ciphertext crudo **NUNCA** se serializan. El plaintext de la PII financiera **tampoco** debe aparecer en logs ni mensajes de error.
**Dependencia forward**: la lectura de PII financiera completa (CBU/CUIL/DNI en claro) se difiere a un endpoint dedicado de **FINANZAS** en un change posterior; NO se construye en C-07.

### Columnas de la migración 006 (reafirmación)
La migración 006 crea `usuario` con: el set §E4 completo (PII cifrada + `nombre`/`apellidos` + atributos de negocio), `auth_identity_id` (FK SET NULL), y `email_hash` (blind index con índice único parcial `(tenant_id, email_hash) WHERE deleted_at IS NULL`). Crea `asignacion` con `desde`/`hasta` (DATE), `responsable_id` (self-FK a `usuario`), FKs de contexto, `comisiones` (JSONB) y el enum `rol_asignacion`. **`estado_vigencia` NO es columna** (derivado en runtime, D4).

## Risks / Trade-offs

- **[PII no consultable salvo email]** → Por D2, `dni`/`cuil`/`cbu`/`alias_cbu` no son buscables por igualdad. Mitigación: la UI/endpoints de búsqueda de usuarios operan sobre `nombre`/`apellidos`/`legajo` (no cifrados). Si en el futuro se requiere "buscar por DNI exacto", se agrega un blind index para ese campo (mismo patrón que email) en un change posterior. No se introduce ahora para no expandir superficie de PII determinística sin necesidad.
- **[Blind index revela igualdad bajo misma clave]** → Dos usuarios con el mismo email producen el mismo `email_hash` (es el objetivo, para unicidad). Riesgo: un atacante con acceso a la columna `email_hash` puede detectar emails iguales entre filas, pero no recuperar el email sin `SECRET_KEY`. Aceptable y estándar para blind index.
- **[`estado_vigencia` derivado depende del reloj]** → La vigencia se evalúa contra `date.today()` UTC. Trade-off: una asignación "vence" a medianoche UTC, no en la zona local del tenant. Aceptable para el MVP (consistente con el resto del modelo en UTC); si un tenant exige zona local, se parametriza después.
- **[`responsable_id` sin chequeo de ciclos]** → D5 no detecta ciclos. Riesgo bajo (jerarquía persona→persona, poco profunda, administrada por humanos). Documentado; mejora futura.
- **[FK `auth_identity_id` sin backfill]** → La columna queda nullable y vacía hasta que un change de reconciliación la pueble. Riesgo: durante un tiempo `Usuario` y `AuthIdentity` coexisten sin vínculo. Aceptable: no hay datos productivos; el login sigue funcionando vía `AuthIdentity`.
- **[Archivos >500 LOC]** → models/repos/services/routers/schemas de dos entidades con PII pueden crecer. Mitigación: dividir por entidad si se supera el límite (regla dura #15). Se vigila en el cierre de tasks.
- **[Governance CRÍTICO]** → Identidad + PII. La migración (seed RBAC, tablas con PII) y el manejo de la `ENCRYPTION_KEY` se surfacean para revisión humana antes de apply (checkpoint en tasks).

## Resolved Questions

> OQ-1..OQ-4 están **RESUELTAS** y bloqueadas en este diseño (decisión humana tomada). Apply está **DESBLOQUEADO**. OQ-5 queda como nota diferida no bloqueante.

- **OQ-1 — RESUELTA: incluir el set §E4 COMPLETO en `Usuario` ahora.** `Usuario` incluye ya TODOS los atributos de KB §E4: PII cifrada (`email`, `dni`, `cuil`, `cbu`, `alias_cbu` vía `EncryptedString`), `nombre`/`apellidos`, y los atributos de negocio (`banco`, `regional`, `legajo` opcional, `legajo_profesional`, `facturador`, `estado`). Una sola migración de schema (006), sin re-migración posterior. **Razón**: C-18 (liquidaciones) ya necesita `cbu`/`cuil`; modelarlos ahora evita una segunda migración sobre `usuario`. Ver D2 (PII) y la sección "Diseño de datos de `Usuario`" más abajo.
- **OQ-2 — RESUELTA: agregar `auth_identity_id` FK nullable AHORA, `ON DELETE SET NULL`.** Ver D9: la columna `auth_identity_id` (nullable, FK → `auth_identities.id`, `ON DELETE SET NULL`, único parcial por tenant cuando no nulo) se crea en la migración 006, sin backfill. **Por qué SET NULL y no RESTRICT**: el `Usuario` es el registro de negocio (sobrevive a cambios de credencial); si una `AuthIdentity` se elimina, el `Usuario` debe persistir con `auth_identity_id` puesto a NULL, no bloquear el borrado de la identidad. RESTRICT solo tendría sentido si se exigiera que ninguna identidad pueda desvincularse jamás de su usuario — la KB no impone esa invariante, así que prevalece SET NULL.
- **OQ-3 — RESUELTA: email visible, PII financiera enmascarada/ausente en el read general.** `UsuarioRead` (read del ABM general) expone ÚNICAMENTE: `id`, `email`, `nombre`, `apellidos`, `legajo`, `estado`, resumen de asignaciones/roles, y timestamps (`created_at`, `updated_at`). **NO** expone `dni`/`cuil`/`cbu`/`alias_cbu` en texto plano: se omiten por completo, o (si el consumidor lo requiere) se exponen SOLO enmascarados como últimos dígitos (`****1234`). La PII financiera completa se difiere a un endpoint dedicado de FINANZAS en un change posterior (**dependencia forward** — no se construye en C-07). `tenant_id` y el ciphertext crudo NUNCA se serializan. Ver "Contrato de `UsuarioRead`" más abajo.
- **OQ-4 — RESUELTA: helper de vigencia SOLO en C-07; NO tocar el guard RBAC.** C-07 expone `estado_vigencia` (derivado) más un helper de validez reusable (ver D4), pero **NO** modifica `require_permission` ni la resolución de permisos efectivos. La integración de la validez de asignación dentro del guard RBAC queda diferida a su propio change. **Restricción explícita de apply**: la fase de apply NO debe tocar `require_permission` ni el motor de permisos efectivos — solo entregar el helper y el campo derivado.
- **OQ-5 — DIFERIDA (no bloqueante)**: el cifrado AES-GCM y el blind index HMAC dependen de `ENCRYPTION_KEY`/`SECRET_KEY` fijas. La estrategia de rotación de claves queda como nota de preocupación futura (operacional/infra), **fuera de scope del apply de C-07**. No bloquea.
