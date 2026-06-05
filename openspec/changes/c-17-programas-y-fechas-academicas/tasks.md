# Tasks — C-17 programas-y-fechas-academicas

> Strict TDD obligatorio: por cada tarea de implementación se escribe primero el test que falla (RED), luego el código mínimo (GREEN), se triangula con un segundo caso (happy + edge) y se refactoriza. Antes de tocar archivos existentes (main.py, migración encadenada), correr Safety Net.
> Governance: BAJO — autonomía total si pasan los tests.
> Capas: Routers → Services → Repositories → Models. snake_case, ≤500 LOC/archivo, Pydantic `extra='forbid'`, soft delete, tenant scope por defecto.

## 1. Modelos (RED → GREEN → TRIANGULATE → REFACTOR)

- [ ] 1.1 RED: test en `backend/tests/models/test_academico_models.py` que importa `ProgramaMateria` y `FechaAcademica` desde `app.models.academico` (aún no existen) y verifica columnas: hereda `TenantScopedBase` (id UUID, tenant_id, created_at, updated_at, deleted_at).
- [ ] 1.2 GREEN: crear `backend/app/models/academico.py` con `ProgramaMateria` (materia_id, carrera_id, cohorte_id FKs RESTRICT indexadas; titulo Text; referencia_archivo Text NOT NULL; cargado_at) sobre `TenantScopedBase`. Registrar en `app/models/__init__.py`.
- [ ] 1.3 GREEN: agregar `FechaAcademica` (materia_id, cohorte_id FKs RESTRICT indexadas; tipo enum mapeado a DB enum `evaluacion_tipo` con `create_type=False`; numero Integer; periodo Text; fecha Date; titulo Text) + clase Python `FechaAcademicaTipo` (Parcial/TP/Coloquio/Recuperatorio).
- [ ] 1.4 TRIANGULATE: tests que verifican que `tipo` solo acepta los 4 valores válidos y que `referencia_archivo` es NOT NULL (segundo caso de borde).
- [ ] 1.5 REFACTOR: docstrings con design decisions D1-D5, `__repr__` sin PII, confirmar tests verdes.

## 2. Migración 015 (Safety Net primero)

- [ ] 2.1 Safety Net: correr tests de migraciones existentes (`test_*_migration.py`) y capturar baseline verde antes de encadenar 015.
- [ ] 2.2 RED: test `backend/tests/test_academico_migration.py` que aplica migraciones y verifica que existen las tablas `programa_materia` y `fecha_academica` con sus columnas e índices únicos parciales.
- [ ] 2.3 GREEN: crear `backend/alembic/versions/015_create_programas_fechas_academicas.py` (revision="015", down_revision="014"): extender `audit_action` con `PROGRAMA_GESTIONAR` y `FECHA_ACADEMICA_GESTIONAR` (idempotente DO $$); crear tablas con FKs RESTRICT, timestamps, deleted_at; NO crear enum nuevo (reusar `evaluacion_tipo`).
- [ ] 2.4 GREEN: agregar índices parciales únicos — `ux_programa_materia_tenant_combo` sobre (tenant_id, materia_id, carrera_id, cohorte_id) WHERE deleted_at IS NULL; `ux_fecha_academica_tenant_combo` sobre (tenant_id, materia_id, cohorte_id, tipo, numero, periodo) WHERE deleted_at IS NULL.
- [ ] 2.5 TRIANGULATE: test que verifica unicidad (insertar duplicado activo falla) y que la baja lógica libera la combinación para re-alta.
- [ ] 2.6 GREEN: `downgrade()` con DROP TABLE de ambas tablas; tests verdes.

## 3. Repositories (RED → GREEN → TRIANGULATE → REFACTOR)

- [ ] 3.1 RED: test `backend/tests/repositories/test_programa_repository.py` — alta tenant-scoped, get_by_id de otro tenant devuelve None, list excluye soft-deleted.
- [ ] 3.2 GREEN: `backend/app/repositories/programa_repository.py` con `ProgramaMateriaRepository(TenantScopedRepository[ProgramaMateria])` + `listar(materia_id?, carrera_id?, cohorte_id?)` y chequeo de combinación duplicada activa.
- [ ] 3.3 RED: test `backend/tests/repositories/test_fecha_academica_repository.py` — alta, listar con filtros (materia/cohorte/tipo/periodo), listar ordenado por fecha (calendario), aislamiento tenant.
- [ ] 3.4 GREEN: `backend/app/repositories/fecha_academica_repository.py` con `FechaAcademicaRepository(...)` + `listar(filtros)` + `listar_calendario(materia_id, cohorte_id)` (orden por fecha) + chequeo de instancia duplicada activa.
- [ ] 3.5 TRIANGULATE: casos de borde — filtros combinados, lista vacía, registros de otro tenant nunca aparecen.
- [ ] 3.6 REFACTOR: queries SOLO en repos; sin lógica de negocio; tests verdes.

## 4. Schemas Pydantic v2 (`extra='forbid'`)

- [ ] 4.1 RED: test `backend/tests/schemas/test_academico_schemas.py` — schema de programa rechaza campos extra, exige `referencia_archivo` no vacía.
- [ ] 4.2 GREEN: `backend/app/schemas/academico.py` — `ProgramaCreate`, `ProgramaRead`, `FechaAcademicaCreate`, `FechaAcademicaUpdate`, `FechaAcademicaRead` con `model_config = ConfigDict(extra='forbid')`.
- [ ] 4.3 TRIANGULATE: validar `tipo` enum, `numero` ≥ 1, `periodo` con patrón "AAAA-N" (trim), título no vacío.

## 5. Services — función pura de contenido LMS

- [ ] 5.1 RED: test `backend/tests/services/test_fecha_academica_html.py` — `generar_fragmento_calendario([])` devuelve fragmento vacío bien formado; con fechas lista tipo/numero/fecha/titulo.
- [ ] 5.2 GREEN: `backend/app/services/fecha_academica_html.py` — función pura que escapa todo texto con `html.escape` (patrón encuentro_html, D6).
- [ ] 5.3 TRIANGULATE: test XSS — `titulo` con `<script>` se emite escapado, sin etiquetas activas.
- [ ] 5.4 RED+GREEN: `backend/app/services/programa_service.py` y `fecha_academica_service.py` orquestando repos + audit (acciones PROGRAMA_GESTIONAR / FECHA_ACADEMICA_GESTIONAR); validan duplicados y elevan error de conflicto. Sin acceso directo a DB.
- [ ] 5.5 TRIANGULATE: alta duplicada → conflicto; baja → soft delete + audit; re-alta tras baja permitida.

## 6. Routers (RED → GREEN → TRIANGULATE)

- [ ] 6.1 RED: test `backend/tests/api/test_programas_router.py` — POST/GET/DELETE bajo `estructura:gestionar`; 403 sin permiso; 404 cross-tenant; 409 duplicado; referencia_archivo preservada.
- [ ] 6.2 GREEN: `backend/app/api/v1/routers/programas.py` (prefix `/programas`) con factory de service tenant-scoped y `require_permission("estructura:gestionar")` en cada ruta.
- [ ] 6.3 RED: test `backend/tests/api/test_fechas_academicas_router.py` — CRUD; listado tabular filtrado; vista calendario ordenada; fragmento LMS; 403/404/409/422; aislamiento tenant.
- [ ] 6.4 GREEN: `backend/app/api/v1/routers/fechas_academicas.py` (prefix `/fechas-academicas`) con endpoints CRUD + `GET ?vista=calendario` + `GET /{...}/contenido-lms`.
- [ ] 6.5 GREEN: registrar ambos routers en `backend/app/main.py` con prefijo `/api/v1` (Safety Net: correr `test_app_startup.py` antes y después).
- [ ] 6.6 TRIANGULATE: cubrir cada escenario de spec restante con al menos un test (happy + edge).

## 7. Cobertura y cierre

- [ ] 7.1 Correr la suite completa de C-17; verificar ≥80% líneas y ≥90% en services/repos (reglas de negocio).
- [ ] 7.2 Verificar que cada escenario de `specs/programas-materia/spec.md` y `specs/fechas-academicas/spec.md` tiene test correspondiente.
- [ ] 7.3 Confirmar reglas duras: tenant scope por defecto, soft delete, sin queries fuera de repos, sin lógica en routers, ≤500 LOC/archivo, Pydantic `extra='forbid'`.
