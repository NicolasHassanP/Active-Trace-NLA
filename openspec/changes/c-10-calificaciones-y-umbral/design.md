## Context

Tras C-01..C-09 el sistema tiene: JWT con `get_current_user` (`user_id`, `tenant_id`, roles), tenancy row-level (`TenantScopedRepository` / `TenantScopedBase` con `tenant_id` + soft delete + UUID), RBAC fail-closed (`require_permission`, `AuthorizationService.resolve_effective_permissions`), auditoría append-only (`AuditService.record` + enum cerrado `AuditAction`), catálogo estructural (Carrera/Cohorte/Materia), identidad/autorización (Usuario/Asignacion) y el **padrón versionado** (`VersionPadron` + `EntradaPadron`, `EntradaPadron.email` cifrado, `usuario_id` nullable). La última migración aplicada es **007**.

C-10 agrega las **calificaciones** y el **umbral de aprobación**. La `EntradaPadron` activa de C-09 es la raíz de cada `Calificacion`: cada nota cuelga de una entrada del padrón, no directamente del `Usuario` (que puede no existir todavía — D4 de C-09). El parser xlsx/csv replica el patrón ya probado de `padron_parser.py`.

Reglas de dominio que C-10 codifica: **RN-01** (columna numérica = header termina en `(Real)`), **RN-02** (escala textual aprobatoria), **RN-03** (umbral por docente, defecto 60%), **RN-04** (scope-isolated por `usuario × materia`), **RN-07/RN-08** (reporte de finalización, solo escala textual).

Infraestructura reutilizada sin modificar:
- **`TenantScopedRepository`** (C-02): filtrado por `tenant_id` + `deleted_at IS NULL`.
- **`require_permission` + `get_current_user`** (C-03/C-04): guard fail-closed por endpoint; identidad solo desde el JWT.
- **`AuditService.record`** (C-05): registro de `CALIFICACIONES_IMPORTAR`.
- **`Asignacion` / `Materia`** (C-06/C-07): contexto del umbral y de las notas.
- **`EntradaPadron`** (C-09): raíz de cada `Calificacion`; el padrón activo define qué alumnos existen.
- Patrón parser xlsx/csv + `PadronValidationError` → 422 (C-09).

## Goals / Non-Goals

**Goals:**
- Modelos `Calificacion` y `UmbralMateria` tenant-scoped con soft delete; `aprobado` derivado (no es input del usuario).
- Derivación de `aprobado` como **función pura** (`calificacion_aprobado.py`): numérica vs. umbral sobre nota máxima, textual vs. conjunto aprobatorio — trivialmente testeable, sin DB ni I/O.
- Detección de columnas numéricas por sufijo `(Real)` (RN-01) y textuales por valores de escala (RN-02) en el parser.
- Import en dos pasos: **preview** (parsea, detecta actividades, no escribe) + **confirm** (recibe selección de actividades, persiste solo esas).
- Umbral por `(asignacion_id, materia_id)`: configuración aislada por docente (RN-03); fallback al defecto del tenant (60%, conjunto textual estándar) si no hay registro.
- Reporte de finalización (F1.2): cruza completitud contra `Calificacion`, reporta entregas textuales sin nota (RN-07/RN-08).
- Auditoría `CALIFICACIONES_IMPORTAR` en cada import exitoso (RN-23).
- Permisos nuevos `calificaciones:importar` y `calificaciones:configurar-umbral`; migración **008**.

**Non-Goals:**
- NO se computan atrasados, ranking, notas finales agrupadas ni monitores (eso es C-11).
- NO se construyen comunicaciones (C-12).
- NO se almacena el archivo importado (parse en memoria y descarte, igual que C-09).
- NO se implementa edición manual de notas individuales más allá de `origen='Manual'` como valor del modelo (el ABM manual no es scope de C-10; el modelo lo soporta para C-11+).
- NO se modifica RBAC, auth, auditoría, padrón ni la integración Moodle existentes — C-10 solo los consume.
- NO se implementa frontend (C-21+).

## Decisions

### D1 — Migración 008 (siguiente número libre)
007 ya está ocupada por C-09. La próxima libre es **008**: `backend/alembic/versions/008_create_calificaciones.py`, `revision="008"`, `down_revision="007"`. Se sigue el patrón explícito de 005/006/007: SQL explícito, `ALTER TYPE audit_action ADD VALUE` idempotente (DO/EXCEPTION), índices nombrados, seed idempotente de permisos con `ON CONFLICT DO NOTHING` por tenant.

### D2 — `Calificacion` cuelga de `EntradaPadron`, no de `Usuario`
`Calificacion.entrada_padron_id` (FK → `entrada_padron.id`, `ON DELETE RESTRICT`) es la raíz, alineado con KB §E7 ("FK → EntradaPadron"). Un alumno puede tener nota antes de tener cuenta `Usuario` (la `EntradaPadron.usuario_id` ya es nullable en C-09). `materia_id` se desnormaliza en `Calificacion` (FK → `materia`) para queries de análisis directas en C-11 sin join obligatorio a la versión de padrón.
**Alternativa descartada**: colgar de `Usuario.id` → rompería cuando el alumno no tiene cuenta y contradice la KB.

### D3 — `aprobado` derivado y persistido, calculado en el momento del import
`aprobado` es un `BOOLEAN NOT NULL` persistido, pero **nunca** lo provee el cliente: lo calcula `derive_aprobado(...)` (función pura) al persistir, usando el umbral efectivo de la asignación del importador. Se persiste (en vez de calcularse on-read) porque C-11 hará agregaciones masivas (ranking, conteo de atrasados) y un campo materializado evita recomputar en cada query. Si el docente cambia el umbral después, C-11 deberá ofrecer un recálculo — se documenta como OQ-1.
**Alternativa considerada**: columna generada / cálculo on-read. Descartada para C-10: el umbral vive en otra tabla por asignación y la regla numérica necesita la nota máxima, lo que complica una columna generada pura en SQL.

### D4 — Derivación `aprobado` como función pura aislada (`calificacion_aprobado.py`)
`derive_aprobado(nota_numerica, nota_textual, nota_maxima, umbral_pct, valores_aprobatorios) -> bool`:
1. Si `nota_numerica is not None` y `nota_maxima`: `aprobado = (nota_numerica / nota_maxima) * 100 >= umbral_pct`.
2. Sino, si `nota_textual is not None`: `aprobado = nota_textual in valores_aprobatorios`.
3. Sino: `aprobado = False`.
Precedencia numérica > textual (RN-02/RN-03). Pure function, sin DB ni I/O → TDD directo con tablas de casos. Es el corazón de negocio (cobertura ≥90%).

### D5 — Umbral por `(asignacion_id, materia_id)` con fallback al defecto del tenant
`UmbralMateria` tiene unicidad por `(tenant_id, asignacion_id, materia_id)` (índice único parcial `WHERE deleted_at IS NULL`). `UmbralService.get_efectivo(asignacion_id, materia_id)` retorna el registro del docente o un defecto (`umbral_pct=60`, conjunto `{"Satisfactorio", "Supera lo esperado"}`) si no existe (RN-03). Esto garantiza que el umbral de un docente **no afecta a otro** en la misma materia: cada asignación tiene su propio registro.
**Configuración (upsert)**: el endpoint de configuración hace get-or-create por `(asignacion_id, materia_id)` y actualiza `umbral_pct`/`valores_aprobatorios`. La `asignacion_id` se resuelve desde el `current_user` + materia (no se acepta del body como selector de identidad — regla dura #8/#14); el body solo trae `materia_id`, `umbral_pct`, `valores_aprobatorios`.

### D6 — Detección de columnas en el parser (RN-01, RN-02)
`calificacion_parser.py` separa columnas en tres clases:
- **Identidad**: headers que matchean nombre/apellidos/email (para linkear a `EntradaPadron`).
- **Numéricas**: header termina en `(Real)` (case-insensitive, strip) → `actividad = header sin el sufijo "(Real)"`, escala numérica.
- **Textuales**: columna cuyos valores caen en el conjunto de escala textual configurado → escala textual.
- El resto se ignora.
Retorna una estructura `PreviewCalificaciones` (actividades detectadas con nombre + escala, y filas por alumno). `PadronValidationError`-equivalente (`CalificacionValidationError(422)`) si no hay columna de identidad parseable.
**Nota nota_maxima**: para la escala numérica, la nota máxima por actividad se toma del header si Moodle la incluye (formato típico `Tarea 1 (Real)` con max en otra fila/columna) o, en su defecto, se asume 10 como `NOTA_MAXIMA_DEFECTO` configurable. Esto se documenta como OQ-2 (el formato exacto del export de Moodle es un supuesto a confirmar).

### D7 — Linkeo `fila → EntradaPadron` por email contra el padrón activo
Al confirmar el import, cada fila se asocia a la `EntradaPadron` de la **versión activa** de `(materia, cohorte)` cuyo email coincide. El cliente debe enviar `cohorte_id` (igual que C-09) para resolver la versión activa. Filas sin match en el padrón activo se reportan en la respuesta como "no encontradas en el padrón" y **no** generan `Calificacion` (no se crean entradas huérfanas). La comparación por email se hace descifrando en memoria las entradas del padrón activo (no hay blind index — C-09 D3); para padrones del tamaño del MVP (≤5000) es aceptable. Optimización futura (blind index) → OQ-3.
**Alternativa descartada**: crear `EntradaPadron` faltantes durante el import de notas → mezclaría responsabilidades (el padrón es la fuente de verdad de quién cursa) y violaría RN-05.

### D8 — Import scope-isolated por `(usuario × materia)` (RN-04)
Cada `Calificacion` lleva `importado_por` (FK → `usuario`, `ON DELETE SET NULL`) para soportar el scope `(usuario × materia)` de RN-04 que C-11/F1.5 explotarán al vaciar. En C-10 el import simplemente registra `importado_por = current_user.user_id`. El vaciado (F1.5) es de C-11/posterior; aquí solo se garantiza que el dato existe para aislarlo.
**Decisión**: re-importar la misma actividad por el mismo usuario hace **upsert** sobre `(tenant_id, entrada_padron_id, materia_id, actividad, importado_por)` (índice único parcial `WHERE deleted_at IS NULL`): actualiza nota/aprobado y `importado_at`. Evita duplicados al re-subir el archivo corregido.

### D9 — Permisos nuevos y seed idempotente (regla dura #10, CRÍTICO)
Dos permisos en la migración 008, seed idempotente por tenant (patrón de 007):
- `calificaciones:importar` (PROFESOR, COORDINADOR, ADMIN): preview, confirm, reporte de finalización.
- `calificaciones:configurar-umbral` (PROFESOR, COORDINADOR, ADMIN): configurar `UmbralMateria`.
El seed RBAC es dominio CRÍTICO: el agente de apply debe marcar el CHECKPOINT y revisar el grant antes de escribir, igual que en 007.

### D10 — Auditoría `CALIFICACIONES_IMPORTAR`
Se agrega `CALIFICACIONES_IMPORTAR = "CALIFICACIONES_IMPORTAR"` al enum `AuditAction` (modelo + `ALTER TYPE` en 008). El service llama `AuditService.record(action=AuditAction.CALIFICACIONES_IMPORTAR, modulo="calificaciones", entidad_tipo="Calificacion", resultado=ok, registros_afectados=len(creadas), after={"materia_id":..., "actividades":[...]})`. PII (emails de alumnos) NUNCA va en `before/after` (el redactor de C-05 es defensa extra, pero el service no debe pasar emails).

### D11 — Patrón de archivos (igual a C-09) y límite ≤500 LOC
- `backend/app/models/calificacion.py` — `Calificacion` + `UmbralMateria`
- `backend/app/repositories/calificacion_repository.py` — `CalificacionRepository` (+ lecturas de umbral)
- `backend/app/services/calificacion_aprobado.py` — `derive_aprobado` (función pura)
- `backend/app/services/calificacion_parser.py` — detección de columnas RN-01/RN-02
- `backend/app/services/calificacion_service.py` — preview, importar, reporte de finalización
- `backend/app/services/umbral_service.py` — configurar + `get_efectivo`
- `backend/app/api/v1/routers/calificaciones.py` — endpoints
- `backend/alembic/versions/008_create_calificaciones.py`
Si `calificacion_service.py` supera 500 LOC, dividir en `calificacion_import_service.py` + `finalizacion_service.py`.

## Risks / Trade-offs

- **[Nota máxima del export de Moodle]** → RN-01 no especifica de dónde sale la nota máxima por actividad. Mitigación: `NOTA_MAXIMA_DEFECTO=10` configurable; si el header trae la máxima, se usa esa. Documentado en OQ-2; el formato exacto debe confirmarse con un export real antes de cerrar el parser.
- **[`aprobado` materializado se desincroniza al cambiar el umbral]** → Si el docente reconfigura el umbral después de importar, las notas ya persistidas conservan su `aprobado` viejo. Mitigación: C-11 expondrá un recálculo; documentado en OQ-1. Para C-10 el flujo natural (FL-02 pasos 3→4→5) configura el umbral antes de analizar.
- **[Match por email sin blind index]** → El linkeo fila→EntradaPadron descifra emails del padrón activo en memoria. Para >5000 alumnos sería costoso. Mitigación: límite del padrón ya acotado en C-09 (`PADRON_MAX_ROWS`); blind index diferido a OQ-3.
- **[Detección de escala textual heurística]** → Clasificar una columna como textual depende de que sus valores caigan en el conjunto de escala configurado; una columna con valores libres no se detecta. Mitigación: el conjunto de escala es configuración del tenant (RN-02) y el preview muestra al usuario qué se detectó antes de confirmar.
- **[Upsert por actividad]** → El índice único `(tenant, entrada_padron, materia, actividad, importado_por)` asume que el nombre de actividad es estable entre imports. Si el docente renombra la actividad en Moodle, se crea una nueva en vez de actualizar. Trade-off aceptado para el MVP.

## Migration Plan

1. Crear `008_create_calificaciones.py` (`down_revision="007"`): `ALTER TYPE audit_action ADD VALUE 'CALIFICACIONES_IMPORTAR'`; CREATE TABLE `umbral_materia` y `calificacion`; índices nombrados + únicos parciales; seed idempotente de permisos por tenant.
2. Agregar las tablas a `_ensure_schema` en `backend/tests/conftest.py` (drop en orden inverso de FK: `calificacion` antes que `umbral_materia`; ambas antes que `entrada_padron`/`materia`/`asignacion`).
3. `alembic upgrade head` aplica limpio en la DB de test (vía conftest).
4. Rollback: `downgrade()` revierte grants/permisos, dropea índices y tablas en orden inverso. El `ALTER TYPE ... ADD VALUE` de Postgres no es reversible directamente; el downgrade lo deja documentado (mismo trade-off que 007/004) sin romper.

## Open Questions

Ninguna bloqueante para apply. Notas diferidas:
- **OQ-1**: ¿Recálculo de `aprobado` al cambiar el umbral? En C-10, NO (se materializa al importar). C-11 debe ofrecer recálculo si el umbral cambia post-import.
- **OQ-2**: ¿De dónde sale la nota máxima por actividad numérica en el export real de Moodle? C-10 asume `NOTA_MAXIMA_DEFECTO=10` configurable. Confirmar con un export real (parámetro a ajustar en apply si difiere).
- **OQ-3**: ¿Se necesita blind index sobre `EntradaPadron.email` para el linkeo masivo? En C-10, NO (descifrado en memoria, padrón acotado). Reevaluar si el volumen crece.
- **OQ-4**: ¿La selección de actividades debe persistirse (qué actividades el docente "sigue" en una materia) para C-11? En C-10 la selección es por-import (no se guarda una config de actividades activas). Si C-11 la necesita persistente, se agrega entonces.
