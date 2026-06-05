## Context

C-16 implementa la Épica 8 (Workflow de Tareas Internas, F8.1–F8.3) y el flujo FL-05. Es un módulo de **alto uso** (cientos de tareas simultáneas), construido sobre C-07 (Usuario/Asignacion), C-04 (RBAC `require_permission`) y C-05 (audit log). Governance **MEDIO**: lógica de dominio, implementar con checkpoints y surfacear decisiones no obvias.

El patrón de capas a seguir es el de C-15 (avisos): `Router → Service → Repository → Model`, repositorios `TenantScopedRepository`, soft-delete e identidad siempre desde el JWT. La KB (§E12) define el modelo de datos y FL-05 el flujo; la KB nombra estados "Abierta/en progreso/completada" en prosa, pero el scope de C-16 fija el enum canónico **Pendiente | EnProgreso | Resuelta | Cancelada** (alineado con CHANGES.md [C-16]).

## Goals / Non-Goals

**Goals:**
- Modelar `Tarea` y `ComentarioTarea` tenant-scoped, soft-delete, UUID PK.
- Workflow de estado con matriz de transiciones validada en el servicio (no transiciones libres).
- Asignación y delegación con trazabilidad completa (asignado_por, asignado_a, audit + comentario de sistema).
- Hilo de comentarios por tarea.
- Self-service "mis tareas" (F8.1) sin requerir `tareas:gestionar`.
- Administración global con filtros (F8.3) protegida por `tareas:gestionar`.
- API `/api/v1/tareas/*`.
- Migración 014 idempotente, con seed de permiso y extensión de `audit_action`.

**Non-Goals:**
- Notificaciones push / email al asignar o cambiar estado (lo cubre el módulo de avisos/comunicaciones; fuera de C-16).
- Adjuntar archivos/evidencias binarias en comentarios (FL-05 menciona "evidencias"; en C-16 el hilo es solo texto — ver OQ-5).
- Subtareas, dependencias entre tareas, fechas de vencimiento / SLA.
- Frontend (lo cubre el agente Frontend en otro change).
- Paginación avanzada / cursor; el listado de administración usa filtros + límite simple (se puede extender luego).

## Decisions

### D1 — Dos tablas tenant-scoped sobre `TenantScopedBase`
`tarea` y `comentario_tarea`, ambas con `tenant_id`, `created_at`, `updated_at`, `deleted_at`, UUID PK (igual que `aviso`/`acknowledgment_aviso`). Repositorios filtran por `tenant_id` + `deleted_at IS NULL` por defecto.
**Alternativa descartada**: una sola tabla con comentarios en JSONB — rompe el hilo consultable/filtrable y el patrón de la KB (§E12 define `ComentarioTarea` como entidad).

### D2 — Enum `tarea_estado` (Pendiente | EnProgreso | Resuelta | Cancelada)
`str`-enum Python `TareaEstado`, mapeado con `SAEnum(..., name="tarea_estado", create_type=False)` (creado por la migración 014, igual que `aviso_alcance`). Estado inicial al crear: **Pendiente**.

### D3 — Matriz de transiciones de estado (workflow en el servicio)
Las transiciones legales se definen como un diccionario `_TRANSICIONES_VALIDAS: dict[TareaEstado, set[TareaEstado]]` en `tarea_service.py`. Cualquier transición fuera de la matriz → `HTTP 409 Conflict`. Matriz propuesta (ver OQ-1):

| Desde \ Hacia | Pendiente | EnProgreso | Resuelta | Cancelada |
|---------------|-----------|------------|----------|-----------|
| **Pendiente** | — | ✅ | ✅ | ✅ |
| **EnProgreso** | ✅ (volver atrás) | — | ✅ | ✅ |
| **Resuelta** | ❌ | ✅ (reabrir: devolución FL-05 §7) | — | ❌ |
| **Cancelada** | ❌ | ❌ | ❌ | — |

- `Cancelada` es **terminal-final** (no se reabre).
- `Resuelta` es terminal-revisable: coordinación puede reabrirla a `EnProgreso` (FL-05 paso 7, "devuelve al docente para ajustes"). No salta directo a Pendiente.
- Mantener el mismo estado (no-op) se rechaza con 409 (debe ser una transición real).

### D4 — `contexto_id` como referencia blanda polimórfica (`contexto_id` + `contexto_tipo`)
La KB define `contexto_id` como "referencia opcional a otra entidad del dominio (nullable)" — deliberadamente genérica. Para no acoplar `tarea` a una FK fija y permitir vincular tareas a materias, encuentros, coloquios, alumnos, etc., se modela como par **polimórfico blando**: `contexto_id UUID NULL` (sin FK física) + `contexto_tipo VARCHAR(50) NULL` (discriminador, p. ej. `"Encuentro"`, `"Coloquio"`, `"Alumno"`). Ambos null o ambos presentes (validado en schema).
`materia_id` se mantiene como FK explícita aparte (la KB lo lista como FK directa a Materia y es el filtro más usado en F8.3).
**Alternativa descartada**: FK física polimórfica o tabla de enlace — sobreingeniería para un campo opcional e informativo; la integridad referencial estricta del contexto no es un requisito de C-16.

### D5 — Delegación: audit + comentario de sistema (trazabilidad)
Delegar = reasignar una tarea existente cambiando `asignado_a` a otro docente. La delegación:
1. Actualiza `asignado_a` (el `asignado_por` se actualiza al actor que delega, capturando la cadena de responsabilidad actual).
2. Emite audit `TAREA_DELEGAR` (actor del JWT, entidad Tarea, before/after con asignados).
3. Inserta un `ComentarioTarea` **de sistema** (`autor_id` = actor) con texto generado (p. ej. "Tarea delegada de <X> a <Y>") para que el hilo refleje la delegación. Ver OQ-3.

### D6 — Identidad siempre desde el JWT; schemas sin campos de identidad
`asignado_por`, `autor_id`, `tenant_id` se resuelven de `current_user` (JWT) en el servicio, **nunca** del body. Los schemas request (`extra='forbid'`) NO declaran esos campos. `asignado_a` SÍ va en el body (es a quién se asigna, no la identidad del actor).

### D7 — Split de permisos: `tareas:gestionar` vs self-service
- **Requieren `tareas:gestionar`** (F8.3 administración global + asignar/delegar a terceros):
  - `POST /tareas` (crear/asignar a otro docente)
  - `POST /tareas/{id}/delegar` (reasignar a otro docente)
  - `GET /tareas/admin` (listado global con filtros)
  - `DELETE /tareas/{id}` (soft-delete)
- **Solo autenticación** (F8.1/F8.2 self-service del asignado):
  - `GET /tareas/mias` (mis tareas asignadas)
  - `GET /tareas/{id}` (detalle: solo si soy asignado_a, asignado_por, o tengo `tareas:gestionar`)
  - `PATCH /tareas/{id}/estado` (cambiar estado: permitido al `asignado_a` para avanzar su propia tarea, y a quien tenga `tareas:gestionar` para cualquier tarea; la matriz D3 acota qué transiciones)
  - `POST /tareas/{id}/comentarios` (comentar en una tarea de la que soy asignado_a/asignado_por, o con `tareas:gestionar`)
  - `GET /tareas/{id}/comentarios` (mismo criterio de acceso que el detalle)

Razón del split: un docente sin `tareas:gestionar` DEBE poder ver y progresar las tareas que le asignaron (FL-05 "Gestión de la tarea"), pero NO crear/delegar/ver tareas ajenas. El servicio enforce la pertenencia (`asignado_a == current_user` o `asignado_por == current_user`) cuando no hay `tareas:gestionar`. Ver OQ-4.

### D8 — Extensión del enum `audit_action`
Se agregan en migración 014 (patrón idempotente `DO $$ ... ADD VALUE ... duplicate_object`): `TAREA_ASIGNAR`, `TAREA_DELEGAR`, `TAREA_CAMBIAR_ESTADO`. Y se agregan los miembros correspondientes a `AuditAction` en `app/models/audit.py`. Comentar (alta de `ComentarioTarea`) NO se audita por sí solo (alto volumen; el hilo ya es el registro). Ver OQ-3.

### D9 — Migración 014 (referencia: 013)
- `revision="014"`, `down_revision="013"`.
- Orden FK: extender `audit_action` → crear enum `tarea_estado` (idempotente) → `tarea` → `comentario_tarea`.
- Índices nombrados: `ix_tarea_tenant_asignado_a_estado`, `ix_tarea_tenant_asignado_por`, `ix_tarea_tenant_materia_id`, `ix_tarea_tenant_estado`, `ix_comentario_tarea_tenant_tarea_id (tenant_id, tarea_id, created_at)`.
- Seed RBAC: permiso `tareas:gestionar` (modulo `tareas`, accion `gestionar`) por tenant con `ON CONFLICT DO NOTHING`, otorgado a COORDINADOR y ADMIN (espejando el seed de `avisos:publicar`). Ver OQ-4 sobre roles adicionales.
- `downgrade`: borra rol_permiso/permiso `tareas:gestionar`, drop índices, drop tablas en orden inverso, drop enum `tarea_estado`. La extensión de `audit_action` no es reversible (limitación de Postgres) — se documenta en el archivo.
- Sin índice único parcial: no hay unicidad natural en `tarea` (un mismo docente puede tener N tareas idénticas).

### D10 — Listado de administración con filtros derivados
`GET /tareas/admin` aplica filtros opcionales (`asignado_a`, `asignado_por`, `materia_id`, `estado`, `q` búsqueda libre sobre `descripcion` con `ILIKE`). Todo en una query tenant-scoped en el repositorio (queries SOLO en repositories). Sin denormalizar contadores: si se necesita conteo de comentarios, se deriva con `COUNT`.

### D11 — Performance (alto uso)
Índices compuestos liderados por `tenant_id` cubren las rutas calientes: `mis tareas` (`tenant_id, asignado_a, estado`), administración (`tenant_id, estado` / `tenant_id, materia_id`), hilo de comentarios (`tenant_id, tarea_id, created_at`). Relaciones `lazy="noload"` para evitar N+1 (patrón aviso).

## Risks / Trade-offs

- **[Referencia blanda `contexto_id` sin FK]** → un `contexto_id` puede quedar colgado si la entidad referida se borra. Mitigación: es informativo/opcional; el frontend resuelve por `contexto_tipo` y tolera "no encontrado". Documentado como decisión consciente (D4).
- **[Reabrir Resuelta]** → permite "des-resolver". Mitigación: la transición Resuelta→EnProgreso queda auditada (`TAREA_CAMBIAR_ESTADO`) y registrada en el hilo; sólo a EnProgreso, no a Pendiente.
- **[Comentarios no auditados individualmente]** → menor trazabilidad fina. Mitigación: el hilo `comentario_tarea` ES append-style (soft-delete) y queda como registro; las acciones de peso (asignar/delegar/estado) sí se auditan (D8).
- **[`asignado_por` se sobreescribe al delegar]** → se pierde el asignador original como columna. Mitigación: la cadena de delegaciones queda en audit (before/after) y en los comentarios de sistema (D5). Si se requiriera el asignador original persistente, sería una columna extra (no incluida; ver OQ-3).
- **[Volumen alto]** → listados sin paginación pueden crecer. Mitigación: filtros obligan a acotar; índices compuestos; paginación se puede añadir sin romper contrato (query param opcional).

## Migration Plan

1. Crear modelos, schemas, repos, service y router (TDD, sin tocar DB todavía).
2. Escribir migración 014 siguiendo 013 exactamente.
3. Aplicar `alembic upgrade head` contra la DB de test (asyncpg disponible en Python 3.10) y verificar tablas/enum/seed.
4. Verificar `alembic downgrade -1` (rollback limpio salvo la extensión de enum, documentada).
5. Registrar el router en `main.py`.
6. Suite de tests contra PostgreSQL real (sin mocks de DB).

**Rollback**: `alembic downgrade 013` revierte tablas, índices, enum y seed de permiso.

## Open Questions

- **OQ-1**: ¿La matriz de transiciones D3 es correcta? En particular: (a) ¿`Resuelta` debe poder reabrirse, y solo a `EnProgreso` (no a `Pendiente`)? (b) ¿`Cancelada` es definitivamente terminal-final? (c) ¿Se permite `EnProgreso → Pendiente` (volver atrás)?
- **OQ-2**: `contexto_id` polimórfico blando (`contexto_id` + `contexto_tipo`, sin FK) vs FK fija a una entidad concreta. ¿Se aprueba el enfoque polimórfico (D4)?
- **OQ-3**: ¿Delegar debe (a) auditar `TAREA_DELEGAR`, (b) insertar comentario de sistema, ambos? ¿Y debe persistirse el `asignado_por` original como columna aparte, o alcanza con audit + comentarios?
- **OQ-4**: Split de permisos (D7): ¿`tareas:gestionar` para COORDINADOR + ADMIN es suficiente, o algún otro rol (p. ej. NEXO) administra tareas globalmente? ¿El `asignado_a` sin `tareas:gestionar` puede cambiar estado de su propia tarea (asumido SÍ)?
- **OQ-5**: FL-05 menciona "evidencias" en el hilo. ¿C-16 las incluye (adjuntos) o el hilo es solo texto (asumido solo texto, adjuntos fuera de scope)?
