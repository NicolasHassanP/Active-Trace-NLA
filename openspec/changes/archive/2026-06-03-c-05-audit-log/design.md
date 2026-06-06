## Context

Tras C-01..C-04 el sistema tiene: identidad desde JWT (`get_current_user` → `CurrentUser(user_id, tenant_id, roles)`), tenancy row-level (`TenantScopedRepository` filtra por `tenant_id` y `deleted_at IS NULL`), y RBAC fino (`require_permission(codigo)` → `PermissionGrant(codigo, scope)`, fail-closed). El catálogo RBAC ya incluye `auditoria:ver` (ADMIN/FINANZAS global, COORDINADOR propio) e `impersonacion:usar` (ADMIN global), sembrados en la migración 003.

C-05 agrega la capa de auditoría append-only que el producto exige (*trace*: todo audita). Las invariantes que constriñen el diseño:
- **Append-only / inmutable** (RN-23, ARQUITECTURA §5.4): los registros de auditoría no se actualizan ni se borran por ningún rol.
- **Catálogo cerrado de acciones** (RN-24): códigos `MODULO_ACCION`; nada arbitrario.
- **Identidad desde la sesión** (regla dura #8): actor y tenant del evento se derivan del JWT, jamás de la petición. IP y user-agent SÍ se leen del `Request` porque son contexto del cliente, no identidad.
- **Atribución al actor real bajo impersonación** (RN-41): el evento siempre apunta al actor real; el usuario impersonado es un campo adicional opcional.
- **Tenant-scoped** (regla dura #9): toda fila lleva `tenant_id`; las lecturas se filtran por tenant.
- **Governance CRÍTICO**: este diseño es propuesta; la implementación requiere aprobación humana explícita.

Patrones existentes a respetar: mixins en `models/mixins.py` (`UUIDMixin`, `TenantMixin`, `TimestampMixin`, `SoftDeleteMixin`), migraciones con SQL explícito + seed idempotente (003), repositories construidos con `(model, session, tenant_id)`, Pydantic v2 con `extra='forbid'`, tests con DB real (sin mocks), Strict TDD.

## Goals / Non-Goals

**Goals:**
- Persistir eventos de auditoría append-only e inmutables, tenant-scoped, con: actor real, actor impersonado (opcional), código de acción del catálogo, módulo, tipo + id de entidad afectada, resultado (ok/fail), conteo de afectados, IP, user-agent, before/after (JSONB) y timestamp.
- Garantizar que NO existe ningún camino de código (repository/service) que actualice o borre un evento de auditoría.
- Validar contra el catálogo cerrado de códigos de acción (rechazar códigos arbitrarios).
- Registrar inicio y fin de impersonación atribuidos al actor real.
- Exponer una lectura de auditoría protegida por `auditoria:ver`, con scope row-level (`propio` → solo eventos cuyo actor real es el usuario actual; global → todo el tenant).
- Ofrecer un helper reutilizable (`AuditService.record(...)` + captura de contexto del `Request`) para que changes futuros auditen sin reimplementar la mecánica.

**Non-Goals:**
- NO se construye la sesión de impersonación (token distinguible, switch de identidad activa). C-05 entrega solo el modelo y el registro de auditoría que la soportarán; la activación es de un change posterior.
- NO se audita automáticamente toda ruta vía middleware genérico que infiera el código de acción (riesgo de códigos imprecisos). C-05 provee el helper explícito; cada dominio invoca `record(...)` con el código correcto. (Se evalúa un middleware de enriquecimiento de contexto IP/UA, no de inferencia de acción — ver Decisiones.)
- NO se implementan retención/rotación ni exportación de auditoría (append-only sin límite por ahora).
- NO se cifra el contenido de auditoría más allá de redactar PII/secretos; los eventos no almacenan CBU/DNI/passwords en claro.
- NO se modifican capabilities existentes (auth, rbac, tenancy).

## Decisions

### D1 — Migración 004, tabla `audit_event`
La próxima revisión libre es `004` (003 usada por RBAC). `revision = "004"`, `down_revision = "003"`. Se sigue el estilo de 003: `CREATE TABLE` con SQL explícito, índices nombrados, enum creado idempotente.
**Alternativa descartada**: autogenerar con `alembic revision --autogenerate` → el repo usa migraciones escritas a mano y deterministas; mantenemos consistencia.

### D2 — `AuditEvent` NO usa `TenantScopedBase` completo
`TenantScopedBase` agrega `SoftDeleteMixin` (`deleted_at`) y `TimestampMixin` (`updated_at`, `onupdate`). Un registro de auditoría no se borra ni se actualiza. Por eso `AuditEvent` compone solo `UUIDMixin` + `TenantMixin` + un único `created_at` (timestamp del evento), sin `updated_at` ni `deleted_at`.
**Alternativa descartada**: reutilizar `TenantScopedBase` y "no llamar nunca a delete/update" → frágil; expone columnas que contradicen la semántica append-only y permiten un soft-delete accidental que falla en code review. Mejor que el modelo haga imposible el estado inválido.

### D3 — Inmutabilidad reforzada en DB (defensa en profundidad)
Además de no exponer update/delete en el repository (D6), la migración refuerza la inmutabilidad a nivel DB con un **trigger BEFORE UPDATE OR DELETE** sobre `audit_event` que lanza excepción. Esto protege contra cualquier escritura fuera del repository (scripts, ORM directo, otro código).
**Alternativa considerada**: `REVOKE UPDATE, DELETE` al rol de aplicación → más limpio pero depende de gestión de roles de DB que el proyecto aún no define; el trigger es autocontenido en la migración y portable. Se documenta el REVOKE como endurecimiento futuro en Open Questions.
**Trade-off**: el trigger impide también borrados administrativos legítimos; es el comportamiento deseado (append-only sin límite, ARQUITECTURA §8).

### D4 — Catálogo cerrado de códigos de acción como enum versionado en código
Los códigos `MODULO_ACCION` (RN-24) se modelan como un **enum Python** (`AuditAction(str, enum.Enum)`) versionado en el código, validado en `AuditService.record()` y reflejado por un tipo enum PostgreSQL `audit_action` en la columna `accion`. Códigos fuera del catálogo se rechazan (excepción de dominio → no se persiste).
**Por qué enum y no tabla-catálogo por tenant**: a diferencia de roles/permisos RBAC (administrables por tenant), el catálogo de acciones auditables es una constante del sistema, igual para todos los tenants y versionada con el código que las emite. Una tabla por tenant invitaría a divergencias y a códigos arbitrarios, justo lo que RN-24 prohíbe.
**Alternativa descartada**: columna `VARCHAR` libre → viola RN-24 (admite códigos arbitrarios).
Catálogo inicial mínimo (se extiende en cada change que audite): `IMPERSONACION_INICIO`, `IMPERSONACION_FIN`, `AUDITORIA_CONSULTA`. Los códigos de importación/comunicación/liquidaciones se añadirán en sus respectivos changes.

### D5 — Actor real vs impersonado
`AuditEvent.actor_user_id` (NOT NULL) = el actor real, siempre derivado de la sesión. `AuditEvent.impersonated_user_id` (NULLABLE) = el usuario en cuyo nombre se actúa, presente solo bajo impersonación. Toda lógica de atribución (reportes, scope `propio`) usa `actor_user_id`. Esto materializa RN-41: la acción se atribuye al actor real, nunca al impersonado.

### D6 — `AuditRepository` append-only dedicado
No hereda de `TenantScopedRepository` (que expone `delete()`). Expone:
- `record(event: AuditEvent) -> AuditEvent`: fuerza `event.tenant_id = scope` (igual que `TenantScopedRepository.add`), `session.add`, `commit`, `refresh`.
- `list(*, actor_user_id: UUID | None = None, limit, offset) -> list[AuditEvent]`: SELECT filtrado por `tenant_id`, opcionalmente por `actor_user_id` (para scope `propio`), ordenado por `created_at DESC`.
- `get_by_id(id) -> AuditEvent | None`: scoped por tenant.
Construido con `(session, tenant_id)`. NO hay `update` ni `delete`.

### D7 — `AuditService` y captura de contexto de petición
`AuditService(repository)` expone `record(actor, action, *, modulo, entidad_tipo, entidad_id, resultado, registros_afectados, before, after, ip, user_agent, impersonated_user_id=None)`. Responsabilidades:
- Validar `action ∈ AuditAction` (rechazo de código arbitrario).
- Serializar `before`/`after` a JSONB **redactando PII y secretos** (lista de claves sensibles: `password`, `cbu`, `dni`, `alias_cbu`, `token`, `secret`, `hash`) → se reemplazan por `"***"`.
- Construir el `AuditEvent` y delegar en el repository.
IP y user-agent se capturan con un helper `extract_request_context(request) -> RequestContext(ip, user_agent)` en `core/`, que lee `request.client.host` (respetando `X-Forwarded-For` si está configurado el proxy) y `request.headers.get("user-agent")`. Este helper trata esos datos como **contexto**, nunca como identidad.

### D8 — Endpoint de lectura con scope row-level
`GET /api/v1/auditoria` → `Depends(require_permission("auditoria:ver"))`. El `PermissionGrant.scope` decide el filtro:
- `scope == propio` (COORDINADOR): `list(actor_user_id=current_user.user_id)`.
- `scope == global` (ADMIN/FINANZAS): `list()` (todo el tenant).
La lectura misma se audita opcionalmente con `AUDITORIA_CONSULTA` (decisión menor; por defecto sí, para no crear un punto ciego). Respuesta paginada vía schema Pydantic v2 `AuditEventRead` con `extra='forbid'`.

### D9 — Schemas Pydantic v2
`AuditEventRead` (salida) y, si hace falta para endpoints internos, `AuditEventCreate` (uso interno del service, no expuesto en API porque los eventos no se crean por request del usuario). Todos con `model_config = ConfigDict(extra='forbid')`. `before`/`after` se tipan como `dict[str, Any] | None`.

## Risks / Trade-offs

- **[Trigger de inmutabilidad rompe tests que usan factories naive]** → Los tests crean eventos vía `AuditRepository.record`, que solo inserta; ningún test debe actualizar/borrar un evento. Documentar en el spec que update/delete sobre `audit_event` debe fallar (es un escenario de test positivo de la inmutabilidad).
- **[Serialización de before/after filtra PII si la redacción es incompleta]** → Lista explícita de claves sensibles + test que verifica que un `before` con `cbu`/`password` se persiste redactado. Redacción recursiva sobre dicts anidados.
- **[Volumen de auditoría sin retención crece sin límite]** → Aceptado por diseño (ARQUITECTURA §8: append-only sin límite). Índices en `(tenant_id, created_at)` y `(tenant_id, actor_user_id)` para que las consultas escalen. Rotación/particionado es un Non-Goal de C-05.
- **[Auditar la propia consulta de auditoría genera ruido/recursión]** → No hay recursión (consultar no dispara otra consulta auditada en cascada). Se acepta un evento `AUDITORIA_CONSULTA` por lectura; si genera ruido, se vuelve configurable más adelante.
- **[X-Forwarded-For spoofeable]** → Solo se confía en `X-Forwarded-For` si hay un proxy de confianza configurado; por defecto se usa `request.client.host`. La IP es contexto informativo, no control de acceso, así que el riesgo es bajo.
- **[Catálogo enum exige migración de DB al agregar códigos]** → Cada change que sume códigos añadirá `ALTER TYPE audit_action ADD VALUE`. Es el costo deliberado de RN-24 (catálogo cerrado). Aceptado.

## Migration Plan

1. Crear `004_create_audit_event_table.py`:
   - `CREATE TYPE audit_action AS ENUM (...)` idempotente (patrón DO/EXCEPTION de 003) con el catálogo inicial.
   - `CREATE TYPE audit_resultado AS ENUM ('ok', 'fail')` (o columna boolean `exito`; ver Open Questions).
   - `CREATE TABLE audit_event (...)` con: `id`, `tenant_id` (FK RESTRICT), `actor_user_id`, `impersonated_user_id` (nullable), `accion` (audit_action), `modulo`, `entidad_tipo`, `entidad_id` (nullable), `resultado`, `registros_afectados`, `ip`, `user_agent`, `before` JSONB, `after` JSONB, `created_at TIMESTAMPTZ NOT NULL DEFAULT now()`. Sin `updated_at` ni `deleted_at`.
   - Índices: `ix_audit_event_tenant_created (tenant_id, created_at)`, `ix_audit_event_tenant_actor (tenant_id, actor_user_id)`.
   - Trigger `BEFORE UPDATE OR DELETE ON audit_event` → `RAISE EXCEPTION` (inmutabilidad).
2. `downgrade()`: drop trigger, drop table, drop types (orden inverso).
3. No requiere seed de datos (la auditoría se llena en runtime). No hay backfill.
4. **Rollback**: `alembic downgrade 003` elimina tabla, trigger y enums. Sin pérdida de datos de otras tablas (la FK es saliente desde `audit_event`).

## Open Questions

- **OQ-1 ✅ RESUELTA (usuario, 2026-06-03)**: `resultado` como enum `audit_resultado`. Valores iniciales: `ok`, `fail`, `partial`. Extensible vía `ALTER TYPE` en changes futuros.
- **OQ-2 ✅ RESUELTA (usuario, 2026-06-03)**: La consulta de auditoría SÍ genera su propio evento `AUDITORIA_CONSULTA`. Sin punto ciego.
- **OQ-3 ✅ RESUELTA (usuario, 2026-06-03)**: `entidad_id` es `VARCHAR` nullable. Soporta UUIDs, claves de negocio y entidades compuestas. `entidad_tipo` identifica el modelo.
- **OQ-4 ✅ RESUELTA (usuario, 2026-06-03)**: `REVOKE UPDATE/DELETE` queda fuera de scope de C-05. Anotado para un change de hardening futuro.
- **OQ-5 ✅ RESUELTA (usuario, 2026-06-03)**: El catálogo inicial incluye SOLO `IMPERSONACION_INICIO`, `IMPERSONACION_FIN`, `AUDITORIA_CONSULTA`. Cada change agrega sus códigos vía `ALTER TYPE`.
