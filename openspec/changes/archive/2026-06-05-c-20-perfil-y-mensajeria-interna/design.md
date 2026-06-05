## Context

C-07 ya entregó la entidad base `Usuario` (E4) con su PII cifrada en reposo (AES-256), el blind index `email_hash` para unicidad `(tenant_id, email)`, soft delete y el ABM administrativo (`/api/v1/admin/usuarios`, permiso `usuarios:gestionar`). Lo que falta es el **autoservicio**: que el propio usuario vea y edite sus datos, y un canal de **mensajería interna** entre usuarios registrados —distinto de los emails salientes a alumnos (`comunicaciones`, C-12)—.

Restricciones del proyecto que condicionan el diseño:
- Identidad SIEMPRE desde el JWT (regla dura #8); el target de perfil/inbox nunca viene de la petición.
- Multi-tenancy row-level (regla #9); repos filtran por `tenant_id` por defecto.
- RBAC `modulo:accion` fail-closed (regla #10); cada endpoint declara `require_permission(...)`.
- Capas Routers → Services → Repositories → Models (regla #11); sin SQL en services.
- PII (CBU, DNI) AES-256 (regla #12); soft delete siempre (regla #13).
- Pydantic v2 `extra='forbid'` (regla #5); ≤500 LOC por archivo backend (regla #15).
- Stack: Python 3.13, FastAPI async, SQLAlchemy 2.0 async, Alembic, PostgreSQL.

Governance del change: **BAJO** según CHANGES.md (CRUD sobre perfil propio + inbox interno; sin tocar el motor de auth/RBAC ni el cálculo de liquidaciones). Autonomía total si pasan los tests. *(Nota: el brief de la tarea mencionó MEDIO; se adopta BAJO por ser la fuente autoritativa en CHANGES.md, manteniendo de todos modos checkpoints en las decisiones de seguridad que tocan PII.)*

## Goals / Non-Goals

**Goals:**
- `GET/PATCH /api/v1/perfil`: ver y editar el perfil propio reusando `Usuario`, con `cuil` read-only e identidad derivada del JWT.
- Mensajería interna basada en hilos (`HiloMensaje` + `Mensaje` + participantes), con envío/respuesta, marcado de leído, conteo de no leídos y aislamiento por usuario y tenant.
- Reusar el cifrado PII, el blind index de email y el soft delete ya existentes; no reinventarlos.
- Endpoints con `require_permission` (`perfil:editar`, `inbox:usar`) y auditoría de la edición de perfil.

**Non-Goals:**
- NO reimplementar logout (F11.3): reusa C-03.
- NO modificar la capability `usuarios` ni el ABM administrativo de C-07 (sus requisitos quedan intactos).
- NO construir UI: este change es backend-first; el frontend lo consume desde C-21.
- NO notificaciones push/email a partir de mensajes internos (fuera de scope; el inbox es interno y pull-based).
- NO threading avanzado (replies anidados, adjuntos): un hilo es lineal y de solo texto en esta iteración.

## Decisions

### D1 — El perfil reusa `Usuario`, no crea una entidad nueva
Perfil = vista/escritura de autoservicio sobre `Usuario`. Se añade router `perfil` + service + repo method (`get_by_id` scoped, `update_self`), y schemas `PerfilRead` / `PerfilUpdate`.
- **Por qué**: evita duplicar datos y mantener dos fuentes de verdad del usuario. La diferencia con el ABM de C-07 es el **autorizador** (titular del JWT vs `usuarios:gestionar`) y el **conjunto de campos** (perfil propio incluye su PII en claro; el ABM la enmascara).
- **Alternativa descartada**: entidad `Perfil` separada → desnormaliza y desincroniza el dato del usuario.

### D2 — `cuil` read-only por omisión en el schema de update
`PerfilUpdate` simplemente NO declara `cuil`. Con `extra='forbid'`, cualquier intento de enviarlo da 422 automáticamente, sin lógica extra.
- **Por qué**: aprovecha el contrato Pydantic en lugar de validaciones imperativas. Alineado con S6 (CUIL derivado/gestionado fuera del perfil).
- **Alternativa descartada**: aceptar `cuil` e ignorarlo silenciosamente → confunde al cliente; preferimos fallar ruidoso.

### D3 — `PerfilRead` devuelve PII en claro al dueño; el ABM la enmascara
El propio usuario ve su `dni`/`cbu`/`cuil`/`alias_cbu` descifrados (es su dato). El `UsuarioRead` del ABM (C-07) ya enmascara esa PII para terceros; ese contrato no cambia.
- **Por qué**: dos contratos distintos para dos autorizadores distintos. La regla "PII nunca en logs" sigue vigente en ambos.

### D4 — Modelo de mensajería: hilo 1:1 + mensajes + participantes (estado de leído por participante)
Tres tablas: `hilos_mensaje` (id, tenant_id, asunto?, timestamps, deleted_at), `mensajes` (id, tenant_id, hilo_id, remitente_id, asunto, cuerpo, created_at, deleted_at), y `hilo_participantes` (hilo_id, usuario_id, tenant_id, last_read_at). **En esta iteración los hilos son estrictamente 1:1**: exactamente 2 participantes por hilo, validado en el service al crear. La participación se deriva de `hilo_participantes`, nunca de la petición.
- **Por qué**: OQ-3 cerrada → limitamos a 1:1 para esta iteración. El modelo soporta grupal en el futuro sin cambio de schema (solo quitar la validación de `max_participantes == 2`).
- **Alternativa descartada**: un único campo `destinatario_id` en `mensajes` → no soporta la futura extensión a grupal ni estado de leído por usuario de forma limpia.

### D5 — Leído = `last_read_at` por participante
Marcar leído al abrir el hilo (`GET /{hilo_id}`) actualiza `last_read_at` del participante; no-leídos = mensajes con `created_at > last_read_at`.
- **Por qué**: una sola columna por participante, conteo barato vía comparación temporal, sin tabla de "lecturas por mensaje".
- **Trade-off**: granularidad por hilo, no por mensaje individual — suficiente para un inbox interno.

### D6 — Mensajería 100% independiente de `comunicaciones`
Tablas, repos, services y router separados. Sin cola de despacho, sin estados Pend→Send→OK/Fail (eso es de emails a alumnos, RN-15). El inbox es pull-based.
- **Por qué**: FL-10 lo declara explícitamente paralelo. Mezclarlos acoplaría dos dominios con ciclos de vida distintos.

### D7 — Identidad y participación siempre server-side
Remitente = `sub` del JWT; participación = consulta a `hilo_participantes`. Cualquier `remitente_id`/`usuario_id` del body se ignora. Hilos ajenos devuelven 404 (no 403) para no revelar existencia.
- **Por qué**: reglas duras #8/#9; 404 evita enumeración de hilos de otros.

### D8 — Permisos nuevos en el catálogo RBAC
`perfil:editar` e `inbox:usar` se registran como permisos del catálogo (administrable como datos, no hardcodeados).
- **`perfil:editar`** — otorgado a **todo usuario autenticado, incluido ALUMNO** (OQ-1 cerrada: autoservicio universal). El seed lo asigna a todos los roles del sistema.
- **`inbox:usar`** — otorgado a TUTOR/PROFESOR/COORDINADOR/NEXO/ADMIN/FINANZAS (F3.4); ALUMNO excluido del inbox en esta iteración.
- **Nota de seed**: la asignación rol↔permiso por defecto se implementa en tasks; el seed es idempotente.

## Risks / Trade-offs

- **[Cambio de email rompe sesión/login]** El email es credencial de login (HU-45). → El PATCH actualiza `email` + `email_hash` atómicamente y respeta unicidad; documentar que un cambio de email cambia el identificador de login. No se invalida la sesión activa (el JWT usa el UUID, no el email).
- **[PII en claro en `PerfilRead`]** Devolver `cbu`/`dni` descifrados amplía la superficie. → Solo al dueño (titular del JWT), nunca a terceros; mantener la regla "PII fuera de logs"; tests que verifican ausencia de PII en logs.
- **[404 vs 403 en hilos ajenos]** Devolver 403 filtraría existencia de hilos. → Se estandariza 404 para recursos no participados/cross-tenant.
- **[Spoofing de remitente]** Un cliente podría enviar `remitente_id`. → `extra='forbid'` + atribución forzada desde JWT; test explícito de spoofing.
- **[Crecimiento de la bandeja]** Inbox sin paginación escala mal. → `GET /inbox` y `GET /inbox/{hilo_id}` con paginación/orden desde el inicio; índices por `(tenant_id, usuario_id)` en participantes y `(tenant_id, hilo_id, created_at)` en mensajes.
- **[Tamaño de archivos]** Service de mensajería podría superar 500 LOC. → Separar `perfil` y `mensajeria` en módulos distintos; dividir service de inbox si crece (listar / leer / responder / iniciar).

## Migration Plan

1. **Migración única C-20**: dos operaciones en una sola revisión Alembic:
   a. `ALTER TABLE usuario ADD COLUMN genero VARCHAR(50)` (nullable, sin default — OQ-2 cerrada: columna no existía).
   b. Crear `hilos_mensaje`, `mensajes` y `hilo_participantes` con `tenant_id`, índices de aislamiento y `deleted_at`.
2. Seed idempotente de los permisos `perfil:editar` (todos los roles, incluyendo ALUMNO) e `inbox:usar` (TUTOR/PROFESOR/COORDINADOR/NEXO/ADMIN/FINANZAS) en el catálogo RBAC.
3. Despliegue sin downtime: la columna `genero` es nullable (no rompe filas existentes); las tablas nuevas son aditivas.
4. Rollback: revertir la migración (drop columna `genero` y las 3 tablas nuevas); `Usuario` vuelve a su estado C-07.

## Open Questions

- **OQ-1** ✅ **CERRADA (2026-06-05)**: `perfil:editar` se otorga a TODO usuario autenticado, incluyendo ALUMNO. Seed cubre todos los roles del sistema.
- **OQ-2** ✅ **CERRADA (2026-06-05)**: `genero` NO existe en `Usuario` (verificado contra el modelo real de C-07). Se agrega como `VARCHAR(50) nullable` en la migración única de este change (ver Migration Plan).
- **OQ-3** ✅ **CERRADA (2026-06-05)**: Mensajería limitada a hilos **1:1** en esta iteración. El modelo soporta grupal en el futuro sin cambio de schema.
