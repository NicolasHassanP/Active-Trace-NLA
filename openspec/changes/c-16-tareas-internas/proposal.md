## Why

El equipo docente y de coordinación necesita un canal estructurado para coordinar trabajo interno asíncrono: asignar tareas de seguimiento, delegarlas entre docentes con trazabilidad de quién asignó y quién resuelve, avanzar su estado y discutirlas en un hilo de comentarios. Hoy esa coordinación ocurre fuera de la plataforma (mail, mensajería), sin trazabilidad ni auditoría. C-16 introduce el módulo de tareas internas (Épica 8, FL-05), un módulo de **alto uso** (cientos de tareas simultáneas en período activo) que opera sobre los usuarios y asignaciones ya provistos por C-07.

## What Changes

- Nuevo modelo `Tarea` (tenant-scoped, soft-delete, UUID PK) con `asignado_a` (Usuario que resuelve), `asignado_por` (Usuario que asigna — siempre del JWT), `estado` (Pendiente | EnProgreso | Resuelta | Cancelada), `descripcion`, `materia_id` (nullable), `contexto_id` + `contexto_tipo` (referencia blanda opcional a otra entidad del dominio).
- Nuevo modelo `ComentarioTarea` (hilo de comentarios por tarea; `autor_id` siempre del JWT; soporta comentarios de sistema para asentar delegaciones y cambios de estado).
- **Workflow de estado** validado en la capa de servicio (matriz de transiciones legales; sin transiciones libres). Resuelta puede reabrirse a EnProgreso (devolución de coordinación, FL-05 paso 7); Cancelada es terminal.
- **F8.1 — Mis tareas**: un docente ve y progresa las tareas asignadas a él, filtradas por contexto. Solo requiere autenticación.
- **F8.2 — Asignar/delegar tarea**: crear una tarea para otro docente y reasignar (delegar) una tarea existente a otro docente, dejando trazabilidad (audit + comentario de sistema).
- **F8.3 — Administración global**: vista de todas las tareas del tenant con filtros (asignado_a, asignado_por, materia, estado, búsqueda libre). Requiere `tareas:gestionar`.
- Cambio de estado + alta de comentarios como parte del workflow asíncrono.
- API REST `/api/v1/tareas/*`.
- **Migración 014**: tablas `tarea` y `comentario_tarea`, enum `tarea_estado`, índices nombrados, seed del permiso `tareas:gestionar`, y extensión del enum `audit_action` con las acciones de tarea.

## Capabilities

### New Capabilities
- `tareas-internas`: modelo, workflow de estado, asignación/delegación con trazabilidad, comentarios en hilo, mis-tareas (self-service), administración global con filtros, y API `/api/v1/tareas/*`. Cubre la Épica 8 (F8.1–F8.3) y el flujo FL-05.

### Modified Capabilities
- `audit-action-catalog`: se agregan al catálogo cerrado de acciones auditables los códigos de tareas (asignación, delegación, cambio de estado). Cada nuevo valor exige `ALTER TYPE audit_action ADD VALUE` en la migración.

## Impact

- **Modelos**: `backend/app/models/tarea.py` (nuevo). FKs a `usuario.id` (asignado_a, asignado_por, autor_id), `materia.id` (nullable).
- **Schemas**: `backend/app/schemas/tarea.py` (nuevo) — Pydantic v2, `extra='forbid'`, sin campos de identidad.
- **Repositories**: `backend/app/repositories/tarea_repository.py` (nuevo) — `TareaRepository`, `ComentarioTareaRepository`; queries tenant-scoped + soft-delete.
- **Services**: `backend/app/services/tarea_service.py` (nuevo) — workflow de transiciones, delegación, comentarios, audit.
- **Routers**: `backend/app/api/v1/routers/tareas.py` (nuevo); registrado en `backend/app/main.py`.
- **Audit**: extensión de `AuditAction` en `backend/app/models/audit.py`.
- **Migración**: `backend/alembic/versions/014_create_tareas_internas.py` (nuevo; revision="014", down_revision="013").
- **Dependencias**: C-07 (Usuario, Asignacion) — ARCHIVED. C-04 (RBAC, require_permission). C-05 (audit log).
- **Tests**: alta + asignación, delegación con trazabilidad, transiciones de estado (legales e ilegales), comentarios en hilo, filtros de administración, aislamiento de tenant.
