## Why

El nombre del producto es *trace*: toda acción significativa debe quedar atribuida a un actor real, en un tenant, con timestamp inmutable (RN-23, ARQUITECTURA §1.5, §5.4). Hoy, tras C-01..C-04, el sistema tiene identidad (JWT), tenancy row-level y RBAC fino, pero NO registra qué hace cada usuario. Sin auditoría append-only no hay trazabilidad para soporte, cumplimiento ni diagnóstico, y la impersonación —capacidad peligrosa ya permisada por `impersonacion:usar`— no puede habilitarse de forma segura porque no quedaría rastro de quién actúa en nombre de quién. C-05 es el primer fork del GATE 4 y cierra esta brecha de seguridad fundacional.

## What Changes

- **Modelo `AuditEvent`** (tabla `audit_event`, migración 004): registro append-only, tenant-scoped, con actor real, actor impersonado (opcional), código de acción del catálogo cerrado, módulo, entidad afectada (tipo + id), resultado, conteo de registros afectados, IP, user-agent, before/after del cambio (JSONB) y timestamp. Sin `updated_at` ni `deleted_at`: los registros de auditoría NO se actualizan ni se borran (append-only, inmutable).
- **Catálogo cerrado de códigos de acción** (RN-24): enum/constantes versionadas tipo `MODULO_ACCION`; se rechaza cualquier código fuera del catálogo.
- **`AuditRepository`** append-only: solo `record(...)` y lecturas scoped por tenant. NO hereda de `TenantScopedRepository` genérico (que expone `delete()` soft-delete); se modela aparte para garantizar que no exista ningún camino de update/delete.
- **`AuditService`**: registra eventos significativos, resolviendo actor real vs impersonado y serializando before/after de forma segura (PII redactada, nunca secretos en claro).
- **Captura de contexto de petición** (IP, user-agent) para enriquecer el evento, derivada del `Request`, nunca de identidad.
- **Impersonación auditada** (RN-41): inicio y fin de impersonación generan eventos de auditoría (`IMPERSONACION_INICIO`, `IMPERSONACION_FIN`) con actor real, usuario impersonado y marcas temporales. El modelo `AuditEvent` soporta atribuir toda acción al actor real aunque se ejecute bajo impersonación. **Nota**: el mecanismo de sesión de impersonación (token distinguible) NO se construye aquí; C-05 entrega la capacidad de auditarla y el modelo de datos que lo soporta. La activación de la sesión de impersonación queda para un change posterior.
- **Endpoint de lectura de auditoría** `GET /api/v1/auditoria` protegido por `require_permission("auditoria:ver")`, con scope `propio` aplicado row-level cuando el grant lo indique (COORDINADOR ve solo lo propio; ADMIN/FINANZAS, todo el tenant).
- **Helper de auditoría reutilizable** (dependency / función de servicio) para que los changes futuros (importación, comunicación, liquidaciones) registren eventos sin reimplementar la mecánica.

## Capabilities

### New Capabilities
- `audit-event-log`: registro de auditoría append-only e inmutable de acciones significativas, tenant-scoped, con actor real, contexto de petición (IP/UA), entidad afectada, before/after y resultado.
- `audit-action-catalog`: catálogo cerrado y versionado de códigos de acción `MODULO_ACCION`; rechazo de códigos arbitrarios.
- `impersonation-audit-trail`: registro de inicio/fin de impersonación atribuido al actor real, base de trazabilidad para la futura sesión de impersonación.
- `audit-query`: lectura de eventos de auditoría protegida por `auditoria:ver`, con alcance row-level (`propio` vs global) según el grant RBAC.

### Modified Capabilities
<!-- Ninguna capability existente cambia sus requisitos. C-05 solo agrega. -->

## Impact

- **Migración**: nueva `004_create_audit_event_table.py` (sigue a 003). Tabla `audit_event` + enum `audit_action` o tabla-catálogo, sin `updated_at`/`deleted_at`. Posible enforcement de inmutabilidad a nivel DB (revocar UPDATE/DELETE / trigger), a decidir en design.
- **Modelos**: nuevo `backend/app/models/audit.py` (`AuditEvent`). No usa `TenantScopedBase` completo porque excluye soft-delete y update.
- **Repositories**: nuevo `backend/app/repositories/audit_repository.py` (append-only).
- **Services**: nuevo `backend/app/services/audit_service.py`.
- **Schemas**: nuevo `backend/app/schemas/audit.py` (Pydantic v2, `extra='forbid'`).
- **API**: nuevo router `backend/app/api/v1/routers/auditoria.py` (lectura) + registro en el router v1.
- **Core**: posible helper en `backend/app/core/` para capturar IP/UA del `Request` y exponer un dependency de auditoría.
- **Dependencias**: ninguna nueva librería; reutiliza SQLAlchemy 2.0 async, Pydantic v2, FastAPI, JWT/RBAC ya existentes.
- **Governance**: dominio CRÍTICO (seguridad/auditoría + impersonación). Propuesta y diseño primero; implementación requiere aprobación humana explícita.
- **Scope de commits**: `auditoria`.
