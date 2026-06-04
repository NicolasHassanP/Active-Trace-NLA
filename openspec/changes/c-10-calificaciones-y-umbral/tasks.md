## 1. Safety Net

- [ ] 1.1 Smoke test only — confirm app starts and DB connects: `python -m pytest tests/test_health.py tests/test_app_startup.py -v`; this is the baseline (full suite runs only at the closing task)

## 2. Migración 008 — umbral_materia + calificacion

- [ ] 2.1 Create `backend/alembic/versions/008_create_calificaciones.py` with `revision="008"`, `down_revision="007"` following the explicit-SQL style of 007
- [ ] 2.2 Extend `audit_action` enum idempotently: `DO $$ BEGIN ALTER TYPE audit_action ADD VALUE 'CALIFICACIONES_IMPORTAR'; EXCEPTION WHEN duplicate_object THEN NULL; END $$;`
- [ ] 2.3 Create table `umbral_materia`: `id UUID PK`, `tenant_id FK→tenants RESTRICT`, `asignacion_id FK→asignacion RESTRICT`, `materia_id FK→materia RESTRICT`, `umbral_pct INTEGER NOT NULL DEFAULT 60`, `valores_aprobatorios JSONB NOT NULL DEFAULT '[]'`, plus `created_at`, `updated_at`, `deleted_at`
- [ ] 2.4 Create table `calificacion`: `id UUID PK`, `tenant_id FK→tenants RESTRICT`, `entrada_padron_id FK→entrada_padron RESTRICT`, `materia_id FK→materia RESTRICT`, `importado_por FK→usuario SET NULL`, `actividad TEXT NOT NULL`, `nota_numerica NUMERIC NULL`, `nota_textual TEXT NULL`, `aprobado BOOLEAN NOT NULL DEFAULT FALSE`, `origen` (enum `calificacion_origen`: `Importado`|`Manual`), `importado_at TIMESTAMPTZ`, plus `created_at`, `updated_at`, `deleted_at`
- [ ] 2.5 Add named indexes: `ix_um_tenant_id`, `ix_um_materia_id`; partial unique `uq_um_asignacion_materia ON umbral_materia(tenant_id, asignacion_id, materia_id) WHERE deleted_at IS NULL`; `ix_cal_tenant_id`, `ix_cal_entrada_padron`, `ix_cal_materia_id`; partial unique `uq_cal_entrada_materia_actividad_importador ON calificacion(tenant_id, entrada_padron_id, materia_id, actividad, importado_por) WHERE deleted_at IS NULL`
- [ ] 2.6 Seed permissions idempotently with `ON CONFLICT DO NOTHING` per-tenant (same pattern as 007): `calificaciones:importar` and `calificaciones:configurar-umbral`, each granted to PROFESOR, COORDINADOR, ADMIN — **CHECKPOINT RBAC (CRÍTICO): review and confirm grants before writing**
- [ ] 2.7 Add `umbral_materia` and `calificacion` (and the `calificacion_origen` enum) to `_ensure_schema` in `backend/tests/conftest.py` (drop `calificacion` before `umbral_materia`; both before `entrada_padron`/`materia`/`asignacion`; enum drop if needed)
- [ ] 2.8 Verify `alembic upgrade head` applies cleanly on the test DB (via conftest or manually)

## 3. Modelos SQLAlchemy

- [ ] 3.1 Create `backend/app/models/calificacion.py`: `Calificacion(Base, TenantScopedBase)` with FKs (`entrada_padron_id` RESTRICT, `materia_id` RESTRICT, `importado_por` SET NULL), `nota_numerica` (Numeric, nullable), `nota_textual` (Text, nullable), `aprobado` (Boolean), `origen` (SAEnum `calificacion_origen`, `create_type=False`), `importado_at`
- [ ] 3.2 Add `UmbralMateria(Base, TenantScopedBase)` to the same file (or its own) with `asignacion_id`, `materia_id`, `umbral_pct` (Integer default 60), `valores_aprobatorios` (JSONB list of str)
- [ ] 3.3 Ensure both models have a `__repr__` that excludes any PII (no email; identity is the linked EntradaPadron)
- [ ] 3.4 Update `backend/app/models/__init__.py` to export `Calificacion`, `UmbralMateria`
- [ ] 3.5 Add `CALIFICACIONES_IMPORTAR = "CALIFICACIONES_IMPORTAR"` to `AuditAction` in `backend/app/models/audit.py`

## 4. Schemas Pydantic (`extra='forbid'`)

- [ ] 4.1 Create `backend/app/schemas/calificacion.py`:
  - `ActividadDetectada(actividad: str, escala: Literal['numerica','textual'])`
  - `PreviewCalificaciones(actividades: list[ActividadDetectada], filas: list[dict], no_en_padron: list[str])`
  - `ImportarCalificacionesRequest(materia_id: UUID, cohorte_id: UUID, actividades_seleccionadas: list[str], filas: list[dict])`
  - `CalificacionRead(id, entrada_padron_id, materia_id, actividad, nota_numerica, nota_textual, aprobado, origen, importado_at)` — no `tenant_id`, `from_attributes=True`
  - `ConfigurarUmbralRequest(materia_id: UUID, umbral_pct: int, valores_aprobatorios: list[str])` — `umbral_pct` validado 0..100
  - `UmbralMateriaRead(id, asignacion_id, materia_id, umbral_pct, valores_aprobatorios)` — no `tenant_id`
  - `ReporteFinalizacionRequest` / `EntregaSinCorregir(entrada_padron_id, actividad)` for F1.2
  - All with `model_config = ConfigDict(extra='forbid')`

## 5. Configuración

- [ ] 5.1 Add to `backend/app/core/config.py` (`Settings`): `UMBRAL_PCT_DEFECTO: int = 60`, `VALORES_APROBATORIOS_DEFECTO: list[str] = ["Satisfactorio", "Supera lo esperado"]`, `NOTA_MAXIMA_DEFECTO: float = 10.0` (OQ-2)
- [ ] 5.2 Update `.env.example` with the new variables and descriptive comments

## 6. Derivación de `aprobado` (función pura) — TDD

- [ ] 6.1 [RED] Create `backend/tests/test_calificacion_aprobado.py`; write `test_numeric_at_or_above_threshold_is_approved` (7/10, umbral 60 → True) — fails (no module)
- [ ] 6.2 [GREEN] Create `backend/app/services/calificacion_aprobado.py`: `derive_aprobado(nota_numerica, nota_textual, nota_maxima, umbral_pct, valores_aprobatorios) -> bool` (numeric branch) — passes
- [ ] 6.3 [RED] `test_numeric_below_threshold_is_not_approved` (5/10, umbral 60 → False) — fails
- [ ] 6.4 [GREEN] generalize numeric comparison — passes
- [ ] 6.5 [RED] `test_textual_in_approving_set_is_approved` and `test_textual_outside_set_is_not_approved` — fails
- [ ] 6.6 [GREEN] add textual branch (membership in `valores_aprobatorios`) — passes
- [ ] 6.7 [RED] `test_numeric_takes_precedence_over_textual` (8/10 + "No alcanzado" → True) — fails
- [ ] 6.8 [GREEN] enforce numeric precedence (RN-02/RN-03) — passes
- [ ] 6.9 [RED] `test_both_null_is_not_approved` — fails; [GREEN] return False when both None — passes; confirm ≥90% coverage on this module

## 7. Parser de calificaciones (detección de columnas RN-01/RN-02) — TDD

- [ ] 7.1 [RED] Create `backend/tests/test_calificacion_parser.py`; `test_detects_numeric_column_by_real_suffix`: header `"Tarea 1 (Real)"` → activity `"Tarea 1"`, escala numerica — fails (no parser)
- [ ] 7.2 [GREEN] Create `backend/app/services/calificacion_parser.py`: `parse_calificaciones_file(file_bytes, filename, escala_textual) -> PreviewCalificaciones`; xlsx via openpyxl, csv via DictReader (reuse C-09 pattern); detect `(Real)` numeric columns — passes
- [ ] 7.3 [RED] `test_column_without_real_suffix_not_numeric` — fails; [GREEN] only `(Real)`-suffixed headers are numeric (RN-01) — passes
- [ ] 7.4 [RED] `test_detects_textual_column_by_scale_values`: column with "Satisfactorio"/"No alcanzado" → escala textual — fails; [GREEN] classify textual columns by configured scale set (RN-02) — passes
- [ ] 7.5 [RED] `test_identity_columns_ignored_as_activities`: "Nombre", "Dirección de correo" not detected as activities — fails; [GREEN] exclude identity/metadata columns — passes
- [ ] 7.6 [RED] `test_missing_identity_column_raises_422`: file without any email/name column → `CalificacionValidationError(422)` — fails; [GREEN] validate identity column present — passes

## 8. Servicio de Umbral — TDD

- [ ] 8.1 [RED] Write `backend/tests/test_umbral.py`; safety net; `test_get_efectivo_returns_default_when_none` (no UmbralMateria → umbral_pct 60, default set) — fails (no service/repo)
- [ ] 8.2 [GREEN] Create `backend/app/repositories/calificacion_repository.py` with `get_umbral(asignacion_id, materia_id)`; create `backend/app/services/umbral_service.py` `UmbralService.get_efectivo(...)` returning default from Settings when None — passes
- [ ] 8.3 [RED] `test_configurar_creates_umbral_for_asignacion` (PROFESOR sets 70 → UmbralMateria with asignacion_id resolved from current_user) — fails
- [ ] 8.4 [GREEN] Implement `UmbralService.configurar(materia_id, umbral_pct, valores_aprobatorios, current_user)`: resolve asignación from user+materia, get-or-create upsert — passes
- [ ] 8.5 [RED] `test_threshold_one_docente_does_not_affect_another` (A=80, B=50 same materia → independent records, get_efectivo per asignación distinct) — fails; [GREEN] confirm uniqueness by `(asignacion, materia)` — passes
- [ ] 8.6 [RED] `test_umbral_tenant_isolation` (T1 umbral not visible in T2) — fails; [GREEN] confirm base class tenant scoping; explicit assertion — passes

## 9. Servicio de Calificaciones (preview + importar) — TDD

- [ ] 9.1 [RED] Write `backend/tests/test_calificaciones.py`; `test_preview_returns_activities_without_db_write`: valid file → activities detected, `Calificacion` count remains 0 — fails (no service)
- [ ] 9.2 [GREEN] Create `backend/app/services/calificacion_service.py` `CalificacionService.preview(file_bytes, filename, current_user)` → calls parser, returns `PreviewCalificaciones`, no DB writes — passes
- [ ] 9.3 [RED] `test_importar_persists_only_selected_activities` (detect A,B,C; select A,C → Calificacion only for A and C) — fails
- [ ] 9.4 [GREEN] Implement `CalificacionService.importar(req, current_user)`: filter to selected activities, link each row to active-padron `EntradaPadron` by email (D7), derive `aprobado` via `derive_aprobado` + `UmbralService.get_efectivo`, upsert `Calificacion` (`origen='Importado'`, `importado_por=current_user.user_id`) — passes
- [ ] 9.5 [RED] `test_row_not_in_active_padron_is_reported_not_persisted` (email with no padrón match → in `no_en_padron`, no Calificacion) — fails; [GREEN] resolve via `PadronRepository.get_active_version` + entries; report unmatched — passes
- [ ] 9.6 [RED] `test_import_scope_isolated_per_user` (A and B import same materia → distinct rows, no overwrite of each other) — fails; [GREEN] confirm `importado_por` in upsert key (RN-04) — passes
- [ ] 9.7 [RED] `test_importar_records_audit_calificaciones_importar` (AuditEvent `accion='CALIFICACIONES_IMPORTAR'`, `registros_afectados=N`, no PII in after) — fails; [GREEN] call `AuditService.record(...)` — passes
- [ ] 9.8 [RED] `test_reimport_same_activity_updates_not_duplicates` (re-import corrected file → updates nota/aprobado, no duplicate row) — fails; [GREEN] confirm upsert on unique key — passes

## 10. Reporte de finalización (F1.2, RN-07/RN-08) — TDD

- [ ] 10.1 [RED] `test_completed_textual_without_grade_is_reported`: completion marks textual activity done, no Calificacion → reported as ungraded — fails
- [ ] 10.2 [GREEN] Implement `CalificacionService.detectar_sin_corregir(report, materia_id, cohorte_id, current_user)`: cross completion vs Calificacion, report textual completed-without-grade — passes
- [ ] 10.3 [RED] `test_numeric_activity_excluded_from_ungraded` (RN-08: numeric completed-without-grade NOT reported) — fails; [GREEN] restrict detection to textual scale — passes
- [ ] 10.4 [RED] `test_textual_with_existing_grade_not_reported` — fails; [GREEN] skip activities that already have a `nota_textual` — passes

## 11. Router y endpoints

- [ ] 11.1 Create `backend/app/api/v1/routers/calificaciones.py`:
  - `POST /calificaciones/preview` — multipart upload; `require_permission("calificaciones:importar")`; returns `PreviewCalificaciones`; map `CalificacionValidationError` → 422
  - `POST /calificaciones/importar` — JSON `ImportarCalificacionesRequest`; `require_permission("calificaciones:importar")`; returns list[`CalificacionRead`] or summary
  - `POST /calificaciones/finalizacion` — completion report (multipart or JSON); `require_permission("calificaciones:importar")`; returns list[`EntregaSinCorregir`]
  - `PUT /calificaciones/umbral` — JSON `ConfigurarUmbralRequest`; `require_permission("calificaciones:configurar-umbral")`; returns `UmbralMateriaRead`
  - `GET /calificaciones/umbral` — query `materia_id`; `require_permission("calificaciones:configurar-umbral")`; returns effective `UmbralMateriaRead`
- [ ] 11.2 Register the router in the v1 aggregator (prefix `/calificaciones`, tag `calificaciones`)
- [ ] 11.3 Ensure all routes use `get_current_user`; identity, tenant and asignación derive from the JWT/session — never from body/path params (rules #8/#14)

## 12. Tests de integración HTTP (router-level)

- [ ] 12.1 `test_preview_endpoint_unauthenticated_returns_401`
- [ ] 12.2 `test_preview_endpoint_unauthorized_returns_403` (missing `calificaciones:importar`)
- [ ] 12.3 `test_preview_endpoint_valid_file_returns_activities`
- [ ] 12.4 `test_importar_endpoint_creates_calificaciones_for_selected`
- [ ] 12.5 `test_umbral_put_endpoint_creates_umbral` and `test_umbral_put_unauthorized_returns_403`
- [ ] 12.6 `test_finalizacion_endpoint_reports_textual_only`

## 13. Cobertura y cierre

- [ ] 13.1 Run full test suite once at the end: `python -m pytest tests/ -q --ignore=tests/test_audit_migration.py --ignore=tests/test_auth_migration.py --ignore=tests/test_rbac_migration.py`; confirm all pre-existing tests still pass
- [ ] 13.2 Check coverage: ≥80% líneas y ≥90% reglas de negocio (derive_aprobado, parser detection, umbral, finalización); add tests if below threshold
- [ ] 13.3 Verify all new files stay ≤500 LOC; split `calificacion_service.py` into `calificacion_import_service.py` + `finalizacion_service.py` if it exceeds the limit
- [ ] 13.4 Mark change `[x]` in CHANGES.md (estado del C-10)
