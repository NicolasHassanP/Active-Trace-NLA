## 1. Safety Net

- [x] 1.1 Smoke test only — confirm app starts and DB connects: `python -m pytest tests/test_health.py tests/test_app_startup.py -v`; this is the baseline (full suite runs only at task 13.1)

## 2. Migración 007 — version_padron + entrada_padron

- [x] 2.1 Create `backend/alembic/versions/007_create_padron.py` with `revision="007"`, `down_revision="006"` following the explicit-SQL style of 005/006
- [x] 2.2 Create table `version_padron`: `id UUID PK`, `tenant_id FK→tenants`, `materia_id FK→materia`, `cohorte_id FK→cohorte`, `cargado_por FK→usuario`, `cargado_at TIMESTAMPTZ`, `activa BOOLEAN NOT NULL DEFAULT FALSE`, plus `created_at`, `updated_at`, `deleted_at`
- [x] 2.3 Create table `entrada_padron`: `id UUID PK`, `version_id FK→version_padron`, `tenant_id FK→tenants`, `usuario_id FK nullable→usuario ON DELETE SET NULL`, `nombre TEXT`, `apellidos TEXT`, `email_encrypted TEXT` (ciphertext), `comision TEXT`, `regional TEXT`, plus `created_at`, `updated_at`, `deleted_at`
- [x] 2.4 Add named indexes: `ix_vp_tenant_materia_cohorte_activa ON version_padron(tenant_id, materia_id, cohorte_id) WHERE activa = TRUE AND deleted_at IS NULL`; `ix_ep_version_id ON entrada_padron(version_id)`; `ix_ep_tenant_usuario ON entrada_padron(tenant_id, usuario_id) WHERE deleted_at IS NULL`
- [x] 2.5 Seed permissions with idempotent `ON CONFLICT DO NOTHING`: `padron:cargar` granted to PROFESOR, COORDINADOR, ADMIN; `padron:gestionar` granted to COORDINADOR, ADMIN — per-tenant loop, same pattern as migration 005
- [x] 2.6 Add `version_padron` and `entrada_padron` to `_ensure_schema` in `backend/tests/conftest.py` (enum drops if needed, table drops in reverse FK order)
- [x] 2.7 Verify `alembic upgrade head` applies cleanly on the test DB (run via pytest conftest or manually)

## 3. Modelos SQLAlchemy

- [x] 3.1 Create `backend/app/models/padron.py`: `VersionPadron(TenantScopedBase)` and `EntradaPadron(TenantScopedBase)` with correct FK declarations and `EncryptedString` on `EntradaPadron.email_encrypted`
- [x] 3.2 Add `usuario_id: Mapped[UUID | None]` with `ForeignKey("usuario.id", ondelete="SET NULL")` on `EntradaPadron`
- [x] 3.3 Ensure `VersionPadron.__repr__` and `EntradaPadron.__repr__` exclude `email_encrypted` (no PII in logs)
- [x] 3.4 Update `backend/app/models/__init__.py` to export `VersionPadron`, `EntradaPadron`

## 4. Schemas Pydantic

- [x] 4.1 Create `backend/app/schemas/padron.py`:
  - `PadronRowDTO(nombre, apellidos, email, comision, regional)` — `ConfigDict(extra='forbid')`
  - `ActivarRequest(materia_id: UUID, cohorte_id: UUID, rows: list[PadronRowDTO])` — `extra='forbid'`
  - `VersionPadronRead(id, materia_id, cohorte_id, cargado_por, cargado_at, activa, filas_total)` — no `tenant_id`, `from_attributes=True`
  - `SyncMoodleRequest(course_id: int, materia_id: UUID, cohorte_id: UUID)` — `extra='forbid'`

## 5. Configuración

- [x] 5.1 Add to `backend/app/core/config.py` (`Settings`): `MOODLE_BASE_URL: str | None = None`, `MOODLE_TOKEN: str | None = None`, `MOODLE_SYNC_HOUR: int = 3`, `PADRON_MAX_ROWS: int = 5000`
- [x] 5.2 Update `.env.example` with the four new variables and descriptive comments

## 6. Parser xlsx/csv — TDD

- [x] 6.1 [RED] Create `backend/tests/test_padron_parser.py`; write `test_parse_xlsx_valid`: build in-memory xlsx with columns (nombre, apellidos, email, comision, regional); assert parser returns list of `PadronRowDTO` — test fails (no parser yet)
- [x] 6.2 [GREEN] Create `backend/app/services/padron_parser.py`: `parse_padron_file(file_bytes: bytes, filename: str) → list[PadronRowDTO]`; detect format by extension; use `openpyxl` for xlsx — test passes
- [x] 6.3 [RED] Write `test_parse_csv_valid`: in-memory csv bytes; assert same `PadronRowDTO` structure returned — test fails (no csv branch)
- [x] 6.4 [GREEN] Add csv branch using `csv.DictReader` — test passes
- [x] 6.5 [RED] Write `test_parse_missing_required_column`: xlsx without 'email' column; assert raises `PadronValidationError` with column name in detail — test fails
- [x] 6.6 [GREEN] Add column validation; raise `PadronValidationError(422, detail=[...])` — test passes
- [x] 6.7 [RED] Write `test_parse_exceeds_max_rows`: file with `PADRON_MAX_ROWS + 1` rows; assert raises `PadronValidationError` mentioning the limit — test fails
- [x] 6.8 [GREEN] Add row-count guard after parsing — test passes

## 7. Moodle WS Client — TDD

- [x] 7.1 [RED] Create `backend/tests/test_moodle_ws.py`; write `test_get_enrolled_users_success`: mock `httpx.AsyncClient.get` returning valid JSON; assert returns list of user dicts — test fails (no client)
- [x] 7.2 [GREEN] Create `backend/app/integrations/moodle_ws.py`: `MoodleWSClient(base_url, token)` with `async get_enrolled_users(course_id) → list[dict]` — test passes
- [x] 7.3 [RED] Write `test_retry_on_first_failure`: first `httpx.get` raises `httpx.HTTPError`; second returns valid JSON; assert result returned (1 retry, 2 total attempts) — test fails
- [x] 7.4 [GREEN] Add retry: loop max 2 attempts, `await asyncio.sleep(2)` between them — test passes
- [x] 7.5 [RED] Write `test_both_attempts_fail_raises_moodle_ws_error`: both calls raise; assert `MoodleWSError` with status 502 raised — test fails
- [x] 7.6 [GREEN] Raise `MoodleWSError(502, "Moodle WS unavailable")` after second failure — test passes
- [x] 7.7 [RED] Write `test_token_not_in_error_message`: trigger failure with token `"SECRET_TOKEN"` in config; assert `MoodleWSError.detail` does not contain `"SECRET_TOKEN"` — test fails
- [x] 7.8 [GREEN] Sanitize error message (never interpolate the token) — test passes

## 8. Repository — TDD

- [x] 8.1 [RED] Write `backend/tests/test_padron.py`; safety net run; write `test_get_active_version_none`: no versions for materia×cohorte → returns `None` — test fails (no repository)
- [x] 8.2 [GREEN] Create `backend/app/repositories/padron_repository.py`: `PadronRepository(TenantScopedRepository)` with `get_active_version(materia_id, cohorte_id)` — test passes
- [x] 8.3 [RED] Write `test_create_and_activate_deactivates_previous`: insert v1 active; call `create_and_activate(v2, entries)` → v1.activa is False, v2.activa is True — test fails
- [x] 8.4 [GREEN] Implement `create_and_activate(version_data, entries_data)`: UPDATE prior active version + INSERT new version + INSERT entries in same transaction — test passes
- [x] 8.5 [RED] Write `test_tenant_isolation_active_version`: activate version in tenant A; query active version in tenant B → returns None — test fails
- [x] 8.6 [GREEN] Confirm base class handles this; add explicit assertion — test passes
- [x] 8.7 [RED] Write `test_soft_delete_version`: call `soft_delete_version(version_id)` → version.deleted_at set, version.activa=False, all entries.deleted_at set — test fails
- [x] 8.8 [GREEN] Implement `soft_delete_version(version_id, current_time)` — test passes

## 9. Service — TDD

- [x] 9.1 [RED] Write `test_preview_returns_rows_without_db_write`: call `PadronService.preview(file_bytes, filename, materia_id, cohorte_id, current_user)` with valid xlsx; assert rows returned and `VersionPadron` count in DB remains 0 — test fails
- [x] 9.2 [GREEN] Implement `PadronService.preview(...)` → calls `parse_padron_file`, returns list of `PadronRowDTO`, no DB writes — test passes
- [x] 9.3 [RED] Write `test_activar_creates_version_and_n_entries`: call `PadronService.activar(rows, materia_id, cohorte_id, current_user)` with 3 rows → 1 VersionPadron (activa=True) + 3 EntradaPadron in DB — test fails
- [x] 9.4 [GREEN] Implement `PadronService.activar(...)` → `repository.create_and_activate(...)` + emit `PADRON_CARGAR` audit log — test passes
- [x] 9.5 [RED] Write `test_activar_records_audit_padron_cargar`: after activar, assert AuditLog entry exists with `accion='PADRON_CARGAR'`, `actor_id=current_user.id`, `filas_afectadas=len(rows)` — test fails
- [x] 9.6 [GREEN] Add `audit_log(actor_id=..., accion="PADRON_CARGAR", ...)` call in activar — test passes
- [x] 9.7 [RED] Write `test_vaciar_own_version_succeeds`: create version with `cargado_por=user_a`; call `vaciar` as user_a → soft-deleted — test fails
- [x] 9.8 [GREEN] Implement `PadronService.vaciar(materia_id, cohorte_id, current_user)`: load active version, check `cargado_por == current_user.id` (PROFESOR) or always allow for `padron:gestionar` holders, then `soft_delete_version` — test passes
- [x] 9.9 [RED] Write `test_vaciar_other_user_version_raises_403`: create version with `cargado_por=user_a`; call `vaciar` as user_b (PROFESOR, no `padron:gestionar`) → HTTPException 403 — test fails
- [x] 9.10 [GREEN] Add scope check; raise 403 — test passes
- [x] 9.11 [RED] Write `test_vaciar_no_active_version_raises_404` — test fails
- [x] 9.12 [GREEN] Check active version exists; raise 404 if not — test passes
- [x] 9.13 [RED] Write `test_sync_from_moodle_creates_version`: mock `MoodleWSClient.get_enrolled_users` returning 2 users; call `sync_from_moodle(course_id, materia_id, cohorte_id, current_user)` → 1 VersionPadron + 2 EntradaPadron — test fails
- [x] 9.14 [GREEN] Implement `PadronService.sync_from_moodle(...)`: map Moodle user dicts to `PadronRowDTO`, call `activar(...)` — test passes
- [x] 9.15 [RED] Write `test_sync_from_moodle_502_propagates`: mock client raises `MoodleWSError(502)` → service raises `HTTPException(502)` — test fails
- [x] 9.16 [GREEN] Catch `MoodleWSError` and re-raise as `HTTPException(502)` — test passes

## 10. Tarea nocturna (nightly sync) — TDD

- [x] 10.1 [RED] Create `backend/app/integrations/moodle_sync_task.py`; write `test_nightly_task_iterates_all_mappings` (mocked): given 2 course mappings, sync is called twice — test fails
- [x] 10.2 [GREEN] Implement `start_nightly_sync_task(settings)`: async task that reads course mappings from settings (list of dicts: `course_id`, `materia_id`, `cohorte_id`, `tenant_id`), waits until `MOODLE_SYNC_HOUR` UTC, then iterates — test passes
- [x] 10.3 [RED] Write `test_nightly_task_continues_after_single_mapping_failure`: one mapping raises `MoodleWSError`; second mapping still processed — test fails
- [x] 10.4 [GREEN] Wrap each mapping sync in `try/except`; log error and continue — test passes
- [x] 10.5 Register `start_nightly_sync_task` in `backend/app/main.py` FastAPI `lifespan` (only when `MOODLE_BASE_URL` is set)

## 11. Router y endpoints

- [x] 11.1 Create `backend/app/api/v1/routers/padron.py`:
  - `POST /padron/preview` — multipart file upload; `require_permission("padron:cargar")`; returns `list[PadronRowDTO]`
  - `POST /padron/activar` — JSON body `ActivarRequest`; `require_permission("padron:cargar")`; returns `VersionPadronRead`
  - `DELETE /padron/vaciar` — query params `materia_id`, `cohorte_id`; `require_permission("padron:cargar")`; returns 204
  - `POST /padron/sync-moodle` — JSON body `SyncMoodleRequest`; `require_permission("padron:cargar")`; returns `VersionPadronRead`
- [x] 11.2 Register `padron_router` in the v1 router aggregator (include with prefix `/padron`, tag `padron`)
- [x] 11.3 Ensure all routes use `get_current_user` as dependency and identity comes exclusively from the JWT — no tenant or user_id from request body/path params

## 12. Tests de integración HTTP (router-level)

- [x] 12.1 Write `test_preview_endpoint_unauthenticated_returns_401`
- [x] 12.2 Write `test_preview_endpoint_unauthorized_returns_403` (user missing `padron:cargar`)
- [x] 12.3 Write `test_preview_endpoint_valid_file_returns_rows`
- [x] 12.4 Write `test_activar_endpoint_creates_version`
- [x] 12.5 Write `test_vaciar_endpoint_403_on_other_user_version`
- [x] 12.6 Write `test_sync_moodle_endpoint_502_when_moodle_unavailable` (mock client failure)

## 13. Cobertura y cierre

- [x] 13.1 Run full test suite (one time, at the end): `python -m pytest tests/ -q --ignore=tests/test_audit_migration.py --ignore=tests/test_auth_migration.py --ignore=tests/test_rbac_migration.py`; confirm all pre-existing tests still pass
- [x] 13.2 Check coverage: ≥ 80% líneas y ≥ 90% reglas de negocio en módulos nuevos; add tests if below threshold
- [x] 13.3 Verify all new files stay ≤ 500 LOC; split `padron_service.py` into `padron_import_service.py` + `moodle_sync_service.py` if it exceeds limit
- [x] 13.4 Mark change complete [x] in CHANGES.md
