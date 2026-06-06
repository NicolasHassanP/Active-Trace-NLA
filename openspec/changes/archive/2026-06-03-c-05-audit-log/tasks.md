# Tasks — C-05 audit-log

> Governance: CRÍTICO (seguridad/auditoría + impersonación). La implementación requiere aprobación humana explícita antes de escribir código.
> Strict TDD en cada task con lógica: test que falla → código mínimo → triangulación → refactor. Tests con DB real (sin mocks). Pydantic v2 con `extra='forbid'`. snake_case. ≤500 LOC/archivo.

## 1. Catálogo de acciones (RN-24)

- [x] 1.1 RED: test que `AuditAction` (enum str) contiene `IMPERSONACION_INICIO`, `IMPERSONACION_FIN`, `AUDITORIA_CONSULTA` y que un código arbitrario no es miembro válido
- [x] 1.2 GREEN: crear `backend/app/models/audit.py` (o `core/audit_actions.py`) con el enum `AuditAction(str, enum.Enum)` del catálogo inicial
- [x] 1.3 Triangulación: verificar uniformidad entre tenants (mismo catálogo) y rechazo de valor fuera del enum

## 2. Modelo `AuditEvent` (D2)

- [x] 2.1 RED: test que el modelo `AuditEvent` tiene `id`, `tenant_id`, `actor_user_id`, `impersonated_user_id` (nullable), `accion`, `modulo`, `entidad_tipo`, `entidad_id`, `resultado`, `registros_afectados`, `before`, `after`, `created_at`; y NO tiene `updated_at` ni `deleted_at`
- [x] 2.2 GREEN: definir `AuditEvent` en `backend/app/models/audit.py` componiendo `UUIDMixin` + `TenantMixin` + `created_at` propio (sin `TimestampMixin` ni `SoftDeleteMixin`, ver D2)
- [x] 2.3 Triangulación: test de que `before`/`after` aceptan dict JSONB y nullables

## 3. Migración 004 (D1, D3)

- [x] 3.1 Crear `backend/alembic/versions/004_create_audit_event_table.py` con `revision="004"`, `down_revision="003"`
- [x] 3.2 `upgrade()`: crear enums `audit_action` y `audit_resultado` (idempotentes, patrón DO/EXCEPTION de 003)
- [x] 3.3 `upgrade()`: `CREATE TABLE audit_event` sin `updated_at`/`deleted_at`, con `created_at TIMESTAMPTZ NOT NULL DEFAULT now()` y FK `tenant_id` RESTRICT
- [x] 3.4 `upgrade()`: índices `ix_audit_event_tenant_created (tenant_id, created_at)` e `ix_audit_event_tenant_actor (tenant_id, actor_user_id)`
- [x] 3.5 `upgrade()`: trigger `BEFORE UPDATE OR DELETE ON audit_event` que lanza excepción (inmutabilidad en DB, D3)
- [x] 3.6 `downgrade()`: drop trigger, tabla y enums en orden inverso
- [x] 3.7 Test de migración: aplicar upgrade/downgrade contra DB de test y verificar que la tabla existe/no existe

## 4. Inmutabilidad reforzada (D3)

- [x] 4.1 RED: test de que un UPDATE directo sobre una fila de `audit_event` falla con excepción de DB
- [x] 4.2 RED: test de que un DELETE directo sobre una fila de `audit_event` falla con excepción de DB
- [x] 4.3 GREEN: confirmar que el trigger de la migración 004 cubre ambos casos; ajustar si algún caso pasa

## 5. `AuditRepository` append-only (D6)

- [x] 5.1 RED: test de que `record(event)` persiste el evento forzando `tenant_id` al scope, y que el repo NO expone `update` ni `delete`
- [x] 5.2 GREEN: crear `backend/app/repositories/audit_repository.py` construido con `(session, tenant_id)`, con `record`, `list` y `get_by_id`; sin métodos de mutación
- [x] 5.3 RED: test de aislamiento de tenant — `list()` del tenant A nunca devuelve eventos del tenant B
- [x] 5.4 Triangulación: test de `list(actor_user_id=...)` (filtro para scope propio) y orden `created_at DESC`

## 6. Redacción PII/secretos (D7, spec audit-event-log)

- [x] 6.1 RED: test de que registrar un evento con `before`/`after` conteniendo `cbu` o `password` persiste esos valores redactados
- [x] 6.2 RED: test de redacción recursiva en dicts anidados
- [x] 6.3 GREEN: implementar helper de redacción (lista de claves sensibles: password, cbu, dni, alias_cbu, token, secret, hash) recursivo sobre dicts
- [x] 6.4 Refactor: extraer la lista de claves sensibles a una constante reutilizable

## 7. `AuditService` (D7)

- [x] 7.1 RED: test de que `record(...)` con un código válido construye y persiste el evento; con un código fuera del catálogo lanza error de dominio y no persiste (RN-24)
- [x] 7.2 GREEN: crear `backend/app/services/audit_service.py` con `AuditService(repository)` y `record(actor, action, *, modulo, entidad_tipo, entidad_id, resultado, registros_afectados, before, after, ip, user_agent, impersonated_user_id=None)`
- [x] 7.3 RED: test de atribución — bajo impersonación el evento se atribuye al actor real y registra el usuario impersonado; sin impersonación el campo impersonado queda vacío (RN-41)
- [x] 7.4 Refactor: integrar el helper de redacción del paso 6 dentro de `record`

## 8. Captura de contexto de petición (D7)

- [x] 8.1 RED: test de que `extract_request_context(request)` devuelve IP y user-agent del `Request` (y respeta `X-Forwarded-For` solo si hay proxy de confianza)
- [x] 8.2 GREEN: implementar helper en `backend/app/core/` que lee `request.client.host` y `request.headers.get("user-agent")`, tratándolos como contexto, nunca como identidad

## 9. Schemas Pydantic v2 (D9)

- [x] 9.1 RED: test de que `AuditEventRead` valida una salida bien formada y rechaza campos no declarados (`extra='forbid'`)
- [x] 9.2 GREEN: crear `backend/app/schemas/audit.py` con `AuditEventRead` (y `AuditEventCreate` interno si hace falta), `model_config = ConfigDict(extra='forbid')`, `before`/`after` como `dict[str, Any] | None`

## 10. Eventos de impersonación (RN-41, spec impersonation-audit-trail)

- [x] 10.1 RED: test de que iniciar impersonación registra `IMPERSONACION_INICIO` con actor real, usuario impersonado y timestamp
- [x] 10.2 RED: test de que finalizar impersonación registra `IMPERSONACION_FIN` con actor real, usuario impersonado y timestamp
- [x] 10.3 GREEN: exponer métodos en `AuditService` (`record_impersonation_start` / `record_impersonation_end`) que emiten esos eventos. NOTA: no se construye la sesión de impersonación (Non-Goal); solo el registro de auditoría

## 11. Endpoint de lectura de auditoría (D8, spec audit-query)

- [x] 11.1 RED: test de que `GET /api/v1/auditoria` sin `auditoria:ver` responde 403 (fail-closed)
- [x] 11.2 RED: test de que con `auditoria:ver` alcance `propio` devuelve solo eventos del propio actor; con alcance global devuelve todos los del tenant
- [x] 11.3 GREEN: crear `backend/app/api/v1/routers/auditoria.py` con `GET /auditoria` protegido por `require_permission("auditoria:ver")`, aplicando el filtro según `PermissionGrant.scope`, paginado, devolviendo `AuditEventRead`
- [x] 11.4 GREEN: registrar el router en el agregador v1
- [x] 11.5 Triangulación: test de aislamiento de tenant en el endpoint (usuario del tenant A no ve eventos del tenant B) y registro de `AUDITORIA_CONSULTA` al consultar (OQ-2 resuelta: siempre registrar)

## 12. Cierre

- [x] 12.1 ✅ OQ-1 RESUELTA: `resultado` = enum (`ok`, `fail`, `partial`). OQ-2 RESUELTA: `AUDITORIA_CONSULTA` sí se registra. OQ-3 RESUELTA: `entidad_id` = VARCHAR nullable. OQ-4 RESUELTA: REVOKE fuera de scope. OQ-5 RESUELTA: catálogo mínimo solo con IMPERSONACION_INICIO/FIN + AUDITORIA_CONSULTA. (usuario, 2026-06-03)
- [x] 12.2 Verificar cobertura ≥80% líneas / ≥90% reglas de negocio del módulo de auditoría — 108/108 tests passing
- [x] 12.3 Verificar que ningún archivo backend supera 500 LOC; una sola migración (004) para el cambio de schema
- [x] 12.4 Marcar C-05 como `[x]` en `CHANGES.md`
