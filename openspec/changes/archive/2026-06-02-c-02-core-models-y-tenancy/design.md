## Context

C-01 dejó un esqueleto Clean Architecture ejecutable: `core/database.py` expone la `Base` declarativa, `build_engine` y `build_session_factory`; `core/config.py` expone `Settings` con `ENCRYPTION_KEY` validado a exactamente 32 chars; `core/dependencies.py` expone `get_db` (sesión async por request); y `backend/alembic/env.py` ya está configurado para engine async, con `target_metadata = Base.metadata` y sin migraciones de dominio. C-01 reservó los slots `core/security.py` y `core/tenancy.py` para este change.

C-02 (governance **CRÍTICO**) construye la base transversal de persistencia del dominio sobre ese cimiento: la entidad raíz `Tenant`, el mixin común de toda entidad de negocio, el repository genérico con scope de tenant siempre activo, el soft delete transversal y el cifrado AES-256 de PII. Las invariantes que materializa son contrato (ADR-002 row-level, identidad por UUID, PII cifrada, soft delete, identidad solo desde la sesión) y romperlas es un defecto que falla en code review.

Restricción clave de la fluidez del flujo: el `tenant_id` real proviene del JWT (C-03). C-02 NO implementa auth; deja el **mecanismo** para que el scope de tenant se inyecte en el repository desde fuera (el caller lo provee), de modo que cuando C-03 conecte el JWT, el repository ya esté listo sin reorganizarse.

## Goals / Non-Goals

**Goals:**

- Entidad `Tenant` (tabla `tenants`) como raíz del modelo, con identidad UUID y campos de auditoría.
- Mixin base combinable: identidad UUID (PK), `tenant_id` (FK indexada), `created_at`/`updated_at` (timestamps automáticos), `deleted_at` (soft delete).
- Repository genérico parametrizado por modelo cuyo scope de tenant está **siempre activo**: toda lectura filtra por `tenant_id` y excluye `deleted_at IS NOT NULL` por defecto.
- Soft delete transversal: `delete()` marca `deleted_at`; nunca borrado físico; camino explícito `include_deleted=True`.
- Utilidad AES-256 en `core/security.py` para atributos `[cifrado]`, con cifrado/descifrado transparente vía `TypeDecorator` de SQLAlchemy. Nunca texto plano en logs.
- Migración Alembic 001 (`tenant`) y la convención de una migración por cambio de schema.
- Tests con DB real/efímera: aislamiento multi-tenant, soft delete, cifrado round-trip, timestamps.

**Non-Goals:**

- Auth, JWT, resolución real del tenant desde la sesión (→ C-03). Aquí el scope se inyecta desde el caller; el wiring JWT llega después.
- El modelo `Usuario` y demás entidades de negocio (→ C-03 en adelante). C-02 solo entrega `Tenant` + la base que el resto hereda.
- RBAC / matriz de permisos (→ C-04).
- Audit log (→ C-05). El soft delete y los timestamps preparan la postura append-only, pero la tabla `AuditLog` no es de este change.
- `core/tenancy.py` con la dependency `get_tenant`: su forma final depende del JWT (C-03). C-02 puede dejar el contrato/utilidad mínima de scope, pero no la dependency acoplada a auth.

## Decisions

### D1 — UUID como PK, generado en la aplicación

`id` es `UUID` (columna PostgreSQL `UUID`, tipo `sqlalchemy.UUID(as_uuid=True)`), default `uuid4()` generado en Python (no en la DB). Es la identidad interna opaca exigida por el contrato (`docs/ARQUITECTURA.md §8`, KB §Supuestos base #2). El `legajo`, cuando exista en entidades de negocio, será un atributo más — nunca PK ni selector de identidad.

**Por qué UUID generado en app y no `gen_random_uuid()` de PG**: el objeto ORM conoce su `id` antes del flush (facilita tests, relaciones y logs correlacionados) y no acopla la generación a una extensión/versión de PostgreSQL. Trade-off: UUIDv4 fragmenta el índice frente a un BIGSERIAL; aceptable a la escala del producto y consistente con el requisito de identidad opaca.

**Alternativa descartada**: PK autoincremental (`BIGSERIAL`). Se descarta: un entero secuencial es enumerable y filtra volumen de datos entre tenants; el contrato exige identidad opaca por UUID.

### D2 — Mixin descompuesto en piezas combinables

En vez de un único `BaseModel` monolítico, el mixin se descompone para que `Tenant` (que NO lleva `tenant_id`) reutilice las piezas comunes sin heredar la columna de tenant:

- `UUIDMixin` → `id` (UUID PK, default uuid4).
- `TimestampMixin` → `created_at` (default now, server-side `func.now()`), `updated_at` (default now, `onupdate=func.now()`).
- `SoftDeleteMixin` → `deleted_at` (nullable timestamp).
- `TenantMixin` → `tenant_id` (UUID, FK `tenants.id`, `nullable=False`, indexado).

`Tenant` = `Base + UUIDMixin + TimestampMixin + SoftDeleteMixin` (sin `TenantMixin`, es la raíz).
Toda entidad de negocio = `Base + UUIDMixin + TenantMixin + TimestampMixin + SoftDeleteMixin`.

Se define además un alias de conveniencia `TenantScopedBase` que agrupa los cuatro mixins comunes de entidad de negocio, para que los changes siguientes hereden de una sola clase.

**Por qué descomponer**: la raíz no puede llevar `tenant_id` (no tiene tenant padre); un mixin monolítico forzaría una columna que `Tenant` no debe tener. Descomponer respeta esa asimetría sin código condicional.

### D3 — Repository genérico con scope de tenant inyectado, siempre activo

`repositories/base.py` define `TenantScopedRepository[ModelT]`:

- Se construye con `(session: AsyncSession, tenant_id: UUID)`. El `tenant_id` es estado del repository, **no** un parámetro de cada método ni un dato leído de la query → imposible olvidarlo, imposible pasarlo desde la petición.
- Todo método de lectura (`get`, `list`, `get_by_id`) añade `WHERE tenant_id = :tenant_id` automáticamente y `AND deleted_at IS NULL` por defecto.
- `add()`/`create()` fija `tenant_id` desde el scope del repository sobre el objeto antes de persistir (ignora cualquier `tenant_id` entrante).
- Lecturas cross-tenant son imposibles por construcción: un `get_by_id` de un objeto de otro tenant devuelve `None`.

`Tenant` (la raíz) NO usa este repository tenant-scoped — se gestiona con un repository propio sin filtro de tenant (es la tabla que define los tenants). Eso se documenta como excepción explícita.

**Cómo se conecta el `tenant_id` real**: en C-03, una dependency derivará el `tenant_id` del JWT verificado y lo pasará al construir el repository. C-02 entrega el repository listo para recibirlo; los tests lo inyectan directamente.

**Alternativa descartada**: pasar `tenant_id` como argumento en cada método. Se descarta: es olvidable (un método sin el filtro pasa silenciosamente) y abre la puerta a tomarlo de la petición. El scope como estado del repository es fail-safe.

**Alternativa considerada**: PostgreSQL Row-Level Security (RLS) con `SET app.current_tenant`. Potente, pero acopla el aislamiento a sesión/transacción de PG y complica los tests y las migraciones a esta escala. Se deja como evolución futura (consistente con la nota de ADR-002 sobre reevaluación). El filtro a nivel repository cumple el requisito hoy.

### D4 — Soft delete por defecto, con camino explícito a lo borrado

- `delete(obj)` ejecuta `obj.deleted_at = func.now()` y persiste — nunca `DELETE` físico.
- Las lecturas del repository excluyen `deleted_at IS NOT NULL` por defecto.
- Para auditoría/recuperación, los métodos aceptan `include_deleted: bool = False` que omite ese filtro.
- No se usa un event listener global de SQLAlchemy que intercepte `DELETE`; el borrado lógico es explícito vía el repository (más legible y testeable que magia de eventos).

**Por qué no un `@event.listens_for` global**: ocultaría el comportamiento y dificultaría el camino "incluir borrados"; el contrato pide que el soft delete sea la norma observable, no un efecto invisible.

### D5 — AES-256 en `core/security.py` vía `TypeDecorator`

- Helpers puros `encrypt(plaintext: str) -> str` y `decrypt(ciphertext: str) -> str` usando **`AESGCM` de `cryptography.hazmat`** con la clave de 32 bytes derivada de `ENCRYPTION_KEY` (ya validado a 32 chars en `Settings`). Cada operación genera un nonce de 12 bytes aleatorio; la salida almacenable concatena `nonce || ciphertext` codificada (p. ej. base64/urlsafe) en una columna `String/Text`.
- Un `TypeDecorator` `EncryptedString` envuelve el cifrado a nivel columna: `process_bind_param` cifra al escribir, `process_result_value` descifra al leer. Las entidades de negocio (C-03+) declaran `email`, `dni`, `cuil`, `cbu`, `alias_cbu` como `EncryptedString` y el cifrado es transparente.
- El valor en reposo en la columna está cifrado; el texto plano nunca se persiste ni se escribe en logs. El `__repr__`/logging de modelos no incluye campos `[cifrado]`.
- El round-trip es la prueba: `decrypt(encrypt(x)) == x`, y el valor crudo en la columna `!= x`.

**Por qué `AESGCM` de `cryptography.hazmat` y no Fernet ni AES-CBC a mano** (DECIDIDO): AES-256 estricto (clave de 32 bytes), cifrado autenticado (AEAD — detecta manipulación del ciphertext), nonce por valor, librería auditada. Se descarta Fernet porque en su forma estándar es AES-128-CBC + HMAC, y el contrato exige AES-256. Se descarta AES-CBC artesanal por los errores clásicos de padding/IV. La clave la provee `ENCRYPTION_KEY` (32 chars → 32 bytes para AES-256); el nonce de 12 bytes se genera por operación y se almacena junto al ciphertext.

**Dónde vive**: `core/security.py`, el slot que C-01 reservó. No se crea archivo nuevo ni se reorganiza el árbol.

### D6 — Migración Alembic 001 (tenant) y convención

- `backend/alembic/versions/001_*.py` crea la tabla `tenants` con sus columnas (id UUID PK, nombre, estado, created_at, updated_at, deleted_at) e índices.
- `env.py` ya importa `Base.metadata` (C-01); basta con que los modelos de C-02 se importen para que `--autogenerate` los detecte, pero la migración se revisa a mano (autogenerate como borrador, nunca como verdad ciega).
- Convención fijada: **una migración por cambio de schema**, nombre `NNN_descripcion`. C-02 sólo introduce `tenants` (los modelos de negocio y sus tablas llegan en changes posteriores, cada uno con su migración).

### D7 — TDD del change (DB real, sin mocks)

Strict TDD aplica a todo comportamiento testeable. Tests contra DB de test efímera (PostgreSQL real, asyncpg — SQLite no soporta `UUID`/`asyncpg` igual), nunca mockeando la DB (un mock invalida el test de aislamiento):

- **Cifrado**: round-trip `decrypt(encrypt(x)) == x` (RED→GREEN) → triangular con cadena vacía, unicode, valor largo, y verificar que el valor persistido en columna está cifrado.
- **Mixin/timestamps**: al crear, `created_at` y `updated_at` se setean; al actualizar, `updated_at` cambia y `created_at` no.
- **Soft delete**: tras `delete()`, el registro no aparece en `list()` por defecto, sí con `include_deleted=True`, y la fila sigue físicamente en la tabla.
- **Aislamiento multi-tenant**: dos tenants con datos; un repository scoped al tenant A nunca devuelve filas del tenant B (`list`, `get_by_id`) — triangular con get directo por id ajeno → `None`.

## Risks / Trade-offs

- **[El `tenant_id` real depende del JWT que aún no existe (C-03)]** → Mitigación: el repository recibe el `tenant_id` por inyección en su construcción; C-02 lo prueba inyectándolo directo y C-03 sólo conecta la fuente (JWT). El contrato del repository no cambia.
- **[Un futuro acceso a DB que evite el repository saltaría el scope de tenant]** → Mitigación: regla dura ya documentada (Services nunca tocan la DB; sólo Repositories) + el filtro vive en la clase base que todo repository hereda; un query crudo en un Service falla en code review.
- **[Cifrado AES-256 estricto]** → Resuelto: se usa `AESGCM` de `cryptography.hazmat` con clave de 32 bytes (no Fernet, que es AES-128). Cifrado autenticado AEAD con nonce de 12 bytes por valor.
- **[`TypeDecorator` cifrado impide buscar/igualar por el valor en SQL]** (no se puede `WHERE email = :x` sobre el texto plano) → Trade-off aceptado: la PII cifrada no es buscable por igualdad directa. DECIDIDO: la búsqueda por email (login) se resuelve en C-03 mediante un **hash determinista indexable** en una columna separada del campo cifrado (el campo `[cifrado]` mantiene el nonce aleatorio; la columna de hash permite el lookup). Fuera de alcance de C-02.
- **[UUIDv4 fragmenta índices frente a claves secuenciales]** → Trade-off aceptado a esta escala; el requisito de identidad opaca prevalece. Si surge presión de performance, se evalúa UUIDv7 (ordenable temporalmente) sin cambiar el contrato de identidad.
- **[Soft delete acumula filas: la tabla crece sin purga]** → Trade-off aceptado: la postura append-only es deliberada (auditoría, clonado entre períodos). Una política de archivado/purga, si hace falta, es un change futuro y no debe violar la auditoría.

## Migration Plan

Despliegue: aplicar la migración 001 (`alembic upgrade head`) crea la tabla `tenants`. No hay datos previos de dominio que migrar (es la primera migración de negocio). Rollback: `alembic downgrade -1` elimina `tenants`; al no haber entidades de negocio dependientes todavía en este change, el downgrade es limpio. Los changes siguientes (C-03+) añadirán sus tablas con FK a `tenants`, cada uno con su propia migración.

## Decisiones cerradas (antes preguntas abiertas)

Las tres preguntas abiertas de la propuesta fueron resueltas por el usuario:

- **Algoritmo AES**: `AESGCM` de `cryptography.hazmat` con clave de 32 bytes derivada de `ENCRYPTION_KEY` — AES-256 estricto + AEAD, nonce de 12 bytes por valor. (Ver D5.)
- **Búsqueda por campos cifrados (login por email)**: diferida a C-03 mediante un **hash determinista separado** del campo cifrado. C-02 sólo entrega el `EncryptedString` con nonce aleatorio; no se aborda el lookup acá.
- **Alcance de `core/tenancy.py`**: en C-02 se deja **sólo el contrato de inyección del scope de tenant en el repository** (lo estrictamente desacoplado de auth). `get_tenant` (la dependency que deriva el tenant del JWT) se posterga a C-03. No se acopla nada a auth en este change.
