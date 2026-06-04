## Context

Tras C-01..C-12 el sistema tiene: JWT con `get_current_user` (`user_id`, `tenant_id`, roles), tenancy row-level (`TenantScopedRepository` / `TenantScopedBase` con `tenant_id` + soft delete + UUID, generado en Python), RBAC fail-closed (`require_permission`, `AuthorizationService.resolve_effective_permissions`), auditoría append-only (`AuditService.record` + enum cerrado `AuditAction`), catálogo estructural (`Carrera`/`Cohorte`/`Materia`), identidad/autorización (`Usuario`/`Asignacion`, enum `RolAsignacion` con PROFESOR/TUTOR/COORDINADOR/NEXO/ADMIN/FINANZAS) y módulos de padrón, calificaciones, análisis y comunicaciones. La última migración aplicada es **010** (C-08 equipos).

C-13 agrega el módulo de **encuentros** (KB §E9 `SlotEncuentro`, §E10 `InstanciaEncuentro`) y el **registro de guardias** (§E11 `Guardia`), cubriendo el flujo FL-06 y las funcionalidades F6.1–F6.6. Reglas de dominio codificadas: **RN-13** (dos modos excluyentes de creación de slot: recurrente y único) y **RN-14** (el estado de cada instancia es independiente del slot y de otras instancias).

Infraestructura reutilizada **sin modificar** (solo se consume):
- **`TenantScopedRepository`** / **`TenantScopedBase`** (C-02): filtrado por `tenant_id` + `deleted_at IS NULL`, UUID PK, soft delete.
- **`require_permission` + `get_current_user`** (C-03/C-04): guard fail-closed por endpoint; identidad solo desde el JWT.
- **`AuditService.record`** (C-05): registro de la acción de gestión de encuentros/guardias.
- **`Asignacion` / `Materia` / `Carrera` / `Cohorte`** (C-06/C-07): contexto de slots y guardias; la `asignacion_id` del creador resuelve quién posee el slot/guardia.
- Patrón de migración explícita (005..010): SQL explícito, `ALTER TYPE ... ADD VALUE` idempotente (DO/EXCEPTION), índices nombrados, seed idempotente de permisos `ON CONFLICT DO NOTHING` por tenant, enums con `create_type=False` en el modelo (creados por la migración y por `_ensure_schema` en `conftest.py`).

Governance del dominio: **MEDIO** (lógica de dominio; sin tocar auth/tenancy/RBAC core más allá de seedear un permiso nuevo). El seed RBAC del permiso es el único punto sensible: se marca CHECKPOINT en apply.

## Goals / Non-Goals

**Goals:**
- Modelos `SlotEncuentro`, `InstanciaEncuentro`, `Guardia` tenant-scoped con soft delete y FKs a `asignacion`/`materia`/`carrera`/`cohorte`.
- **Generación de fechas recurrentes como función pura** (`encuentro_recurrencia.py`): a partir de `fecha_inicio` + `dia_semana` + `cant_semanas`, producir la lista de fechas de instancia — sin DB ni I/O, trivialmente testeable (corazón de RN-13, cobertura ≥90%).
- Dos modos excluyentes de creación de slot (RN-13): recurrente (`cant_semanas > 0`, genera N instancias) y único (`fecha_unica` set, genera 1 instancia). Validación: exactamente uno de los dos modos.
- Edición individual de instancia (F6.3, RN-14): `estado`, `meet_url`, `video_url`, `comentario`, sin afectar al slot ni a hermanas.
- **Bloque HTML del aula virtual como función pura** (`encuentro_html.py`): toma una lista de instancias y devuelve un string HTML — sin DB ni I/O.
- Vista admin transversal (F6.5): listar todos los encuentros del tenant (no solo los del creador) para COORDINADOR/ADMIN.
- Registro de guardias (F6.6): el TUTOR registra; COORDINADOR/ADMIN consultan global filtrado + export.
- Permiso nuevo `encuentros:gestionar` (fail-closed); auditoría de la gestión; migración **011**.

**Non-Goals:**
- NO frontend (C-21+): los endpoints devuelven el bloque HTML como string; la inserción en el LMS es manual fuera del sistema (FL-06 paso 8).
- NO integración automática con Moodle/N8N para publicar el bloque (es copy-paste manual).
- NO notificaciones ni recordatorios automáticos de encuentros (fuera de scope).
- NO se modifica RBAC, auth, auditoría, tenancy ni estructura académica existentes — C-13 solo los consume (salvo el seed del permiso nuevo y el nuevo código de auditoría).
- NO reprogramación masiva de instancias ni edición en lote del slot (cada instancia se edita individualmente, RN-14).

## Decisions

### D1 — Migración 011 (siguiente número libre)
010 ya está ocupada por C-08. La próxima libre es **011**: `backend/alembic/versions/011_create_encuentros_guardias.py`, `revision="011"`, `down_revision="010"`. Sigue el patrón explícito de 005..010: SQL explícito, `ALTER TYPE audit_action ADD VALUE` idempotente (DO/EXCEPTION), CREATE TYPE para los enums nuevos, índices nombrados, seed idempotente de permisos `ON CONFLICT DO NOTHING` por tenant.

### D2 — Tres modelos en un archivo `encuentro.py`, con `Guardia` separable
`SlotEncuentro`, `InstanciaEncuentro` y `Guardia` viven en `backend/app/models/encuentro.py`. Si el archivo supera 500 LOC, `Guardia` se mueve a `backend/app/models/guardia.py`. Todos heredan `(Base, TenantScopedBase)`. `__repr__` no expone datos sensibles (los encuentros no portan PII de alumnos, pero se mantiene la convención de no volcar el objeto completo).

### D3 — `SlotEncuentro` es la plantilla; `InstanciaEncuentro` el evento concreto (RN-13, RN-14)
`SlotEncuentro` (KB §E9) modela la recurrencia: `asignacion_id` (FK→asignacion, dueño), `materia_id`, `titulo`, `hora`, `dia_semana`, `fecha_inicio`, `cant_semanas` (0 = único), `fecha_unica` (nullable), `meet_url`, `vig_desde`/`vig_hasta`. `InstanciaEncuentro` (KB §E10) cuelga del slot vía `slot_id` (FK→slot, **nullable** para instancias independientes), con `materia_id` desnormalizado, `fecha`, `hora`, `titulo`, `estado`, `meet_url`, `video_url` (nullable), `comentario`. El estado de cada instancia es independiente (RN-14): editar una no toca al slot ni a las hermanas.
**Alternativa descartada**: materializar instancias on-read derivándolas del slot → impediría el estado/grabación individual por instancia que exige RN-14/F6.3.

### D4 — Generación de fechas recurrentes como función pura (`encuentro_recurrencia.py`)
`generar_fechas(fecha_inicio: date, dia_semana: DiaSemana, cant_semanas: int) -> list[date]`:
1. Avanzar `fecha_inicio` hasta el primer día que cae en `dia_semana` (si `fecha_inicio` ya cae en ese día, esa es la primera).
2. Generar `cant_semanas` fechas con paso de 7 días.
Sin DB ni I/O → TDD directo con tablas de casos. Es el corazón de RN-13 (cobertura ≥90%). La función NO crea instancias; el service la usa y luego persiste.
**Decisión de borde**: si `fecha_inicio` no cae en `dia_semana`, la primera instancia es el siguiente `dia_semana` (se documenta como decisión, no OQ — el flujo FL-06 define día + fecha de inicio coherentes; se elige la interpretación "fecha_inicio es el piso, el día de semana manda").

### D5 — Dos modos excluyentes de creación (RN-13)
El service `crear_slot(...)` valida que se reciba **exactamente uno** de:
- **Recurrente**: `cant_semanas > 0` + `dia_semana` + `fecha_inicio` → genera `cant_semanas` instancias vía `generar_fechas`.
- **Único**: `fecha_unica` set (`cant_semanas = 0`) → genera 1 instancia con `fecha = fecha_unica`.
Si llegan ambos o ninguno → `EncuentroValidationError(422)`. Cada instancia generada nace en estado `Programado`, hereda `titulo`/`hora`/`meet_url`/`materia_id` del slot, y `video_url = NULL`, `comentario = ""`.

### D6 — Edición de instancia restringida a campos mutables (F6.3, RN-14)
`editar_instancia(instancia_id, patch, current_user)` solo permite mutar `estado` (`Programado`|`Realizado`|`Cancelado`), `meet_url`, `video_url`, `comentario`. NO permite cambiar `fecha`, `hora`, `slot_id`, `materia_id` ni `tenant_id` (el schema de patch los excluye con `extra='forbid'`). La instancia se resuelve por `id` **dentro del tenant del JWT**; nunca se acepta `tenant_id` del body.

### D7 — Bloque HTML como función pura (`encuentro_html.py`, F6.4)
`generar_bloque_html(instancias: list[InstanciaEncuentroDTO]) -> str` produce un fragmento HTML (tabla/lista) con título, fecha, hora, link de meet y link de grabación si existe. Sin DB ni I/O → testeable con casos. El endpoint resuelve las instancias del slot/materia y le pasa la lista; el HTML se devuelve como texto plano para copiar al LMS. Se escapan los valores de texto (`html.escape`) para evitar inyección en el aula virtual.

### D8 — `Guardia` independiente, con contexto académico completo (F6.6, KB §E11)
`Guardia`: `asignacion_id` (FK→asignacion, quién cubre — típicamente un TUTOR), `materia_id`, `carrera_id`, `cohorte_id` (FK→carrera/cohorte), `dia` (enum `DiaSemana`, reutilizado), `horario` (texto, ej. "14:00–14:45"), `estado` (`Pendiente`|`Realizada`|`Cancelada`), `comentarios`, `creada_at`. El TUTOR registra su propia guardia: `asignacion_id` se resuelve desde `current_user` + materia (no se acepta como selector de identidad del body — reglas duras #8/#14). COORDINADOR/ADMIN consultan el registro global filtrado (por materia, carrera, cohorte, día, estado) y exportan.

### D9 — Permiso único `encuentros:gestionar` con matriz por rol en el guard
Un solo permiso nuevo `encuentros:gestionar` cubre el módulo (encuentros + guardias). La diferenciación por rol (PROFESOR/COORDINADOR crean encuentros; TUTOR registra guardias; COORDINADOR/ADMIN ven la vista global) se modela seedeando el permiso a esos roles y, donde haga falta distinguir "global" de "propio", el service filtra por `asignacion_id` del creador salvo que el usuario tenga rol COORDINADOR/ADMIN (vista transversal F6.5/F6.6). Seed idempotente por tenant (patrón 007/008).
**Alternativa considerada**: permisos separados `encuentros:gestionar` + `guardias:registrar` + `guardias:ver-global`. Descartada para el MVP: un permiso simplifica el seed y el roadmap pide explícitamente el guard `encuentros:gestionar`; la granularidad fina se difiere a OQ-2.

### D10 — Auditoría de gestión de encuentros/guardias
Se agrega `ENCUENTRO_GESTIONAR = "ENCUENTRO_GESTIONAR"` al enum `AuditAction` (modelo + `ALTER TYPE` en 011). El service llama `AuditService.record(action=AuditAction.ENCUENTRO_GESTIONAR, modulo="encuentros", entidad_tipo="SlotEncuentro"|"InstanciaEncuentro"|"Guardia", resultado=ok, registros_afectados=N, after={...})`. No hay PII de alumnos en estos datos; aun así el redactor de C-05 actúa como defensa en profundidad.

### D11 — Vista admin transversal (F6.5) vs. vista propia
`listar_encuentros(current_user, filtros)`: si el usuario tiene rol COORDINADOR o ADMIN, lista todas las instancias del tenant; si es PROFESOR, filtra a las instancias de slots cuya `asignacion_id` pertenece al usuario. El repository siempre filtra por `tenant_id` (regla dura #9); el filtro por `asignacion_id` se aplica en el service según el rol resuelto del JWT.

### D12 — Patrón de archivos y límite ≤500 LOC
- `backend/app/models/encuentro.py` — `SlotEncuentro`, `InstanciaEncuentro`, `Guardia` + enums (split `guardia.py` si >500).
- `backend/app/repositories/encuentro_repository.py` — slots + instancias.
- `backend/app/repositories/guardia_repository.py` — guardias.
- `backend/app/services/encuentro_recurrencia.py` — `generar_fechas` (función pura).
- `backend/app/services/encuentro_html.py` — `generar_bloque_html` (función pura).
- `backend/app/services/encuentro_service.py` — crear slot, editar instancia, listar.
- `backend/app/services/guardia_service.py` — registrar, consultar, export.
- `backend/app/schemas/encuentro.py`, `backend/app/schemas/guardia.py` — `extra='forbid'`.
- `backend/app/api/v1/routers/encuentros.py`, `guardias.py`.
- `backend/alembic/versions/011_create_encuentros_guardias.py`.

## Risks / Trade-offs

- **[Día de inicio que no coincide con `dia_semana`]** → `generar_fechas` debe decidir si la primera instancia es `fecha_inicio` o el siguiente `dia_semana`. Mitigación: regla explícita (D4) — el `dia_semana` manda, `fecha_inicio` es el piso. Documentado y cubierto por test de triangulación.
- **[Un solo permiso `encuentros:gestionar`]** → No distingue finamente "registrar guardia" de "ver global". Mitigación: el service filtra por rol/asignación (D9, D11); la granularidad fina se difiere a OQ-2 si el negocio la exige.
- **[Generación de muchas instancias]** → `cant_semanas` sin tope podría generar cientos de instancias. Mitigación: validar `cant_semanas` en un rango razonable (`1..52`) en el schema; documentado como límite del MVP.
- **[Export de guardias formato]** → F6.6 pide "exportación" sin definir formato. Mitigación: CSV (mismo patrón que otros exports del sistema); documentado en OQ-1.
- **[Inyección en el bloque HTML]** → El título/comentario del docente se embebe en HTML que va al LMS. Mitigación: `html.escape` de todos los valores de texto (D7).

## Migration Plan

1. Crear `011_create_encuentros_guardias.py` (`down_revision="010"`):
   - `ALTER TYPE audit_action ADD VALUE 'ENCUENTRO_GESTIONAR'` (idempotente DO/EXCEPTION).
   - CREATE TYPE `dia_semana` (`Lunes`..`Domingo`), `instancia_encuentro_estado` (`Programado`|`Realizado`|`Cancelado`), `guardia_estado` (`Pendiente`|`Realizada`|`Cancelada`).
   - CREATE TABLE `slot_encuentro`, `instancia_encuentro`, `guardia` con FKs (RESTRICT a tenant/materia/carrera/cohorte/asignacion; `instancia_encuentro.slot_id` ON DELETE SET NULL para instancias independientes), columnas `created_at`/`updated_at`/`deleted_at`.
   - Índices nombrados (`ix_slot_tenant_id`, `ix_slot_asignacion`, `ix_slot_materia`, `ix_inst_tenant_id`, `ix_inst_slot`, `ix_inst_materia`, `ix_inst_fecha`, `ix_guardia_tenant_id`, `ix_guardia_asignacion`, `ix_guardia_materia`).
   - Seed idempotente `encuentros:gestionar` por tenant → PROFESOR, TUTOR, COORDINADOR, ADMIN (`ON CONFLICT DO NOTHING`). **CHECKPOINT RBAC en apply.**
2. Agregar las tres tablas y los tres enums a `_ensure_schema` en `backend/tests/conftest.py` (drop en orden inverso de FK: `instancia_encuentro` antes que `slot_encuentro`; `guardia` independiente; los tres antes que `asignacion`/`materia`/`carrera`/`cohorte`; drop de enums al final).
3. `alembic upgrade head` aplica limpio en la DB de test.
4. Rollback: `downgrade()` dropea índices y tablas en orden inverso, revoca el grant/permiso y dropea los tres enums nuevos. El `ALTER TYPE audit_action ADD VALUE` de Postgres no es reversible directamente; el downgrade lo deja documentado sin romper (mismo trade-off que 004/007/008).

## Open Questions

Ninguna bloqueante para apply. Notas diferidas:
- **OQ-1**: ¿Formato del export de guardias? C-13 asume **CSV** (consistente con otros exports). Confirmar si coordinación necesita XLSX.
- **OQ-2**: ¿Se requiere granularidad de permisos más fina (`guardias:registrar` vs `guardias:ver-global`)? C-13 usa un único `encuentros:gestionar` + filtrado por rol/asignación. Reevaluar si el negocio exige separar.
- **OQ-3**: ¿La primera instancia recurrente debe ser exactamente `fecha_inicio` aunque no caiga en `dia_semana`, o el siguiente `dia_semana`? C-13 decide: el `dia_semana` manda (D4). Confirmar con un caso real si difiere.
