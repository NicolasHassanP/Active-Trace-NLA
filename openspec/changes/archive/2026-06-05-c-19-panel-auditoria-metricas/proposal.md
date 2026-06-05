## Why

ADMIN y COORDINADOR necesitan supervisar la actividad del sistema (F9.1, F9.2, FL-11): ver cuánto se usa cada funcionalidad, qué docentes están inactivos y qué comunicaciones fallaron. Hoy `C-05` ya expone una lectura básica del `AuditEvent` (lista paginada con scope y permiso `auditoria:ver`), pero no provee las **agregaciones de uso** (acciones por día, interacciones por docente y por docente×materia, estado de comunicaciones por docente) ni el **log de últimas acciones con límite configurable** ni los **filtros ricos** (rango de fechas, materia, usuario, estado) que el panel de supervisión requiere. C-19 cierra esa brecha sin tocar el modelo (la tabla `audit_event` ya existe desde la migración 004): es una capa de **solo lectura** sobre datos ya capturados.

## What Changes

- **Nuevas agregaciones de auditoría** (solo lectura sobre `audit_event` y `comunicacion`):
  - Acciones por día: serie temporal de volumen de acciones, opcionalmente desglosada por actor.
  - Interacciones por docente: conteo de acciones por actor y por tipo de acción (`accion`).
  - Interacciones por docente×materia: conteo por actor y materia, derivando la materia desde `entidad_id` cuando `entidad_tipo = "Materia"` (no existe columna `materia_id` en `audit_event`).
  - Estado de comunicaciones por docente: distribución de `ComunicacionEstado` (Pendiente/Enviando/Enviado/Error/Cancelado) agrupada por `enviado_por`.
- **Log de últimas acciones con límite configurable**: endpoint que devuelve los N registros más recientes, con N por defecto 200 y tope máximo acotado por configuración (no ilimitado).
- **Filtros del panel**: rango de fechas (`desde`/`hasta`), materia, usuario (`actor_user_id`) y estado de comunicación, aplicables a las agregaciones y al log completo (F9.2, RN-23/RN-24).
- **Scope `(propio)` del COORDINADOR**: cuando el grant de `auditoria:ver` tiene scope `propio`, todas las vistas (agregaciones y log) se acotan a los eventos cuyo actor real es el usuario actual; con scope global devuelven todo el tenant. Reusa el patrón de `PermissionGrant` ya establecido en C-05.
- **Nuevos endpoints `/api/v1/auditoria/*`**: `…/metricas/acciones-por-dia`, `…/metricas/interacciones-docente`, `…/metricas/interacciones-docente-materia`, `…/metricas/comunicaciones-por-docente`, y `…/ultimas-acciones`. Todos bajo `require_permission("auditoria:ver")`, fail-closed.
- **Sin migración nueva**: ninguna tabla ni columna se agrega; C-19 es exclusivamente lectura/agregación.

## Capabilities

### New Capabilities
- `auditoria-metricas`: agregaciones de uso sobre el log de auditoría (acciones por día, interacciones por docente y por docente×materia) y distribución de estado de comunicaciones por docente, con filtros de rango de fechas / materia / usuario / estado y scope `propio`/global por permiso.
- `auditoria-panel-log`: log de últimas acciones con límite configurable (defecto 200, tope acotado) y filtros del panel, como vista de solo lectura complementaria a la lista paginada de `audit-query`.

### Modified Capabilities
<!-- Ninguna. audit-query (C-05) permanece intacto; C-19 añade capacidades nuevas sin cambiar sus requisitos. -->

## Impact

- **Backend nuevo**:
  - `app/repositories/audit_metrics_repository.py` — queries de agregación (GROUP BY) sobre `audit_event`; consultas de estado sobre `comunicacion`. Solo lectura, scoped por tenant.
  - `app/services/auditoria_panel_service.py` — orquesta agregaciones + aplica scope `propio`/global desde el `PermissionGrant`.
  - `app/schemas/auditoria_metricas.py` — DTOs de salida (Pydantic v2, `extra='forbid'`).
  - Extensión de `app/api/v1/routers/auditoria.py` — nuevos endpoints de métricas y log.
- **Configuración**: nuevo parámetro de tope del log (p. ej. `AUDIT_PANEL_LOG_MAX`, defecto 200) en `app/core/config.py`.
- **Reutiliza sin modificar**: `AuditEvent`/`AuditAction`/`AuditResultado` (C-05), `Comunicacion`/`ComunicacionEstado` (C-12), `require_permission` + `PermissionGrant` + `PermisoScope` (C-04), `AuditRepository.list` existente.
- **Dependencias de datos**: `C-05` (audit-log, tabla `audit_event`) y `C-07` (usuarios y asignaciones) — ambos archivados.
- **Sin cambios de schema**: no hay nueva migración Alembic.
- **Governance**: ALTO — superficie de lectura sobre datos de auditoría sensibles; las decisiones de derivación de materia y de scope `propio` se documentan en `design.md` para revisión humana.
