## Context

C-06 dejó las entidades raíz `Carrera`, `Cohorte` y `Materia` (modelos en `app/models/estructura.py`, migración 005) y el permiso RBAC `estructura:gestionar` (ADMIN, COORDINADOR). C-17 agrega dos entidades de calendario/documentación que cuelgan de ellas:

- `ProgramaMateria` (KB §E16): documento oficial por materia × carrera × cohorte.
- `FechaAcademica` (KB §E15): instancia evaluativa por materia × cohorte × número.

El patrón del repo está consolidado tras C-08/C-13/C-14: modelos sobre `TenantScopedBase`, repos sobre `TenantScopedRepository[T]`, services sin acceso directo a DB, routers con `require_permission(...)` y `get_current_user`. Governance del dominio: **BAJO** (catálogo/calendario sin lógica financiera ni de seguridad), autonomía total con tests.

La última migración es `014`; la siguiente es `015`. El enum de tipo de evaluación ya existe en DB como `evaluacion_tipo` (Parcial/TP/Coloquio/Recuperatorio, creado en migración 012).

## Goals / Non-Goals

**Goals:**
- Persistir `ProgramaMateria` y `FechaAcademica` con aislamiento por tenant y soft-delete.
- CRUD de fechas académicas con listado tabular filtrable (por materia, cohorte, tipo, período) y vista calendario.
- Alta + asociación de programas con `referencia_archivo` tratada como puntero opaco (el servicio NO interpreta ni valida el contenido del archivo).
- Generación de un fragmento HTML del calendario de fechas listo para el aula virtual (F5.4), como función pura escapada contra XSS.
- Reusar `estructura:gestionar`; no inventar permisos.

**Non-Goals:**
- Subida/almacenamiento físico del archivo del programa: el endpoint recibe y guarda solo la `referencia_archivo` (string opaco). La integración con el servicio de blobs/Moodle queda fuera de C-17.
- Inscripción a evaluaciones, turnos y reservas: eso es C-14 (`Evaluacion`/`ReservaEvaluacion`), entidad distinta. `FechaAcademica` es solo calendarización, sin cupos.
- Frontend: lo consume C-23.

## Decisions

**D1 — Dos modelos en un archivo `app/models/academico.py`.**
Ambos son pequeños y comparten el mismo change/migración. Mantiene <500 LOC. Alternativa (un archivo por modelo) descartada por sobre-fragmentación.

**D2 — Enum de tipo: reutilizar el DB enum `evaluacion_tipo` existente.**
`FechaAcademica.tipo` tiene exactamente los mismos valores que `EvaluacionTipo` (Parcial/TP/Coloquio/Recuperatorio). Se mapea con `SAEnum(..., name="evaluacion_tipo", create_type=False)` para reutilizar el tipo PG ya creado en migración 012, evitando un enum duplicado. La clase Python `FechaAcademicaTipo` se define localmente con los mismos valores (no se importa `EvaluacionTipo` para no acoplar módulos de dominio distintos). Alternativa (nuevo enum `fecha_academica_tipo`) descartada: duplica el tipo y obliga a mantener dos enums sincronizados.

**D3 — `referencia_archivo` es un string opaco (Text, NOT NULL).**
El service nunca abre, valida ni interpreta el archivo. Convención KB: "puntero opaco al servicio de almacenamiento, no un path de disco". El test verifica que se persiste y recupera tal cual, sin transformación.

**D4 — FKs `materia_id`, `carrera_id`, `cohorte_id` con `ON DELETE RESTRICT`, indexadas.**
Coherente con el patrón de `Evaluacion`/`Cohorte`. `ProgramaMateria` lleva las tres; `FechaAcademica` lleva `materia_id` + `cohorte_id` (no carrera: el calendario evaluativo se define por cohorte, que ya pertenece a una carrera).

**D5 — Unicidad de programa por (tenant, materia, carrera, cohorte) WHERE deleted_at IS NULL.**
Un solo programa vigente por combinación. Índice parcial único en la migración (patrón C-06). Un re-alta tras baja lógica es válido. Para `FechaAcademica`: unicidad parcial por (tenant, materia, cohorte, tipo, numero, periodo) WHERE deleted_at IS NULL — evita dos "1er Parcial 2026-1" duplicados.

**D6 — Generación de contenido LMS como función pura `generar_fragmento_calendario(fechas) -> str`.**
Sigue el patrón de `encuentro_html.generar_bloque_html`: sin DB ni red, escapa todo texto con `html.escape` (D7 de C-13) contra XSS. El router obtiene las fechas vía service/repo y delega el render a la función pura. Fácil de testear como unidad.

**D7 — Listado tabular y calendario comparten el mismo repo query, distinta proyección.**
El repo expone `listar(filtros)` con filtros opcionales (materia_id, cohorte_id, tipo, periodo). La "vista calendario" es la misma data ordenada por `fecha`; no se denormaliza. El cliente (C-23) decide la presentación. El endpoint `/fechas-academicas?vista=calendario` solo cambia el orden/agrupado, no la fuente.

**D8 — Auditoría: dos acciones nuevas en `audit_action`.**
`PROGRAMA_GESTIONAR` y `FECHA_ACADEMICA_GESTIONAR`, agregadas idempotentemente al enum PG (patrón `DO $$ ... duplicate_object`) en la migración 015. Las mutaciones (alta/edición/baja) registran audit vía `AuditRepository`, como el resto de los módulos.

**D9 — RBAC: reusar `estructura:gestionar`.**
Ya sembrado para ADMIN/COORDINADOR en migración 005. Todos los endpoints (lectura y escritura) lo exigen. Fail-closed. No se crea permiso nuevo.

## Risks / Trade-offs

- **[Reusar el enum `evaluacion_tipo` acopla semánticamente C-14 y C-17]** → Mitigación: solo se comparte el *tipo de dato PG*, no las entidades ni la lógica. Si los conjuntos divergen en el futuro, se crea un enum dedicado en una migración posterior; el riesgo es bajo porque los cuatro valores son estándar del dominio.
- **[`referencia_archivo` sin validación podría guardar basura]** → Mitigación: es por diseño (D3); la validación del puntero es responsabilidad del servicio de almacenamiento (fuera de scope). El schema valida que sea string no vacío.
- **[Unicidad parcial no cubre carreras case-insensitive ni espacios en período]** → Mitigación: `periodo` se normaliza (trim) en el schema; el formato "AAAA-N" se valida con patrón Pydantic.
- **[Fragmento HTML embebido en LMS = vector XSS]** → Mitigación: D6, `html.escape` sobre todos los valores; test de XSS explícito en tasks.

## Migration Plan

1. Crear `015_create_programas_fechas_academicas.py` (down_revision="014"): extiende `audit_action` (D8), crea tablas `programa_materia` y `fecha_academica` con FKs RESTRICT, timestamps, `deleted_at`, e índices parciales únicos (D5). NO crea enum nuevo (reusa `evaluacion_tipo`).
2. Modelos, repos, services, schemas, routers; registrar routers en `main.py`.
3. Rollback: `downgrade()` hace `DROP TABLE` de ambas tablas (los valores agregados al enum `audit_action` no se remueven — PG no soporta DROP VALUE; es inocuo).

## Open Questions

- Ninguna bloqueante. C-17 no depende de las preguntas abiertas ALTA (PA-01/07/22/23/25). `FechaAcademica` usa `cohorte_id` (que ya resuelve PA-07 vía C-06).
