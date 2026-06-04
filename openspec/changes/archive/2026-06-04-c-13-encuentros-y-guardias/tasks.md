## 1. Safety Net

- [x] 1.1 Smoke test only — confirm app starts and DB connects: `python -m pytest tests/test_health.py tests/test_app_startup.py -v`; this is the baseline (full suite runs only at the closing task)

## 2. Migración 011 — slot_encuentro + instancia_encuentro + guardia

- [x] 2.1 Create `backend/alembic/versions/011_create_encuentros_guardias.py` with `revision="011"`, `down_revision="010"` following the explicit-SQL style of 008/010
- [x] 2.2 Extend `audit_action` enum idempotently: `DO $$ BEGIN ALTER TYPE audit_action ADD VALUE 'ENCUENTRO_GESTIONAR'; EXCEPTION WHEN duplicate_object THEN NULL; END $$;`
- [x] 2.3 Create enums idempotently: `dia_semana` (`Lunes`,`Martes`,`Miércoles`,`Jueves`,`Viernes`,`Sábado`,`Domingo`), `instancia_encuentro_estado` (`Programado`,`Realizado`,`Cancelado`), `guardia_estado` (`Pendiente`,`Realizada`,`Cancelada`)
- [x] 2.4 Create table `slot_encuentro`: `id UUID PK`, `tenant_id FK→tenants RESTRICT`, `asignacion_id FK→asignacion RESTRICT`, `materia_id FK→materia RESTRICT`, `titulo TEXT NOT NULL`, `hora TIME NOT NULL`, `dia_semana dia_semana NULL`, `fecha_inicio DATE NULL`, `cant_semanas INTEGER NOT NULL DEFAULT 0`, `fecha_unica DATE NULL`, `meet_url TEXT NULL`, `vig_desde DATE NULL`, `vig_hasta DATE NULL`, plus `created_at`,`updated_at`,`deleted_at`
- [x] 2.5 Create table `instancia_encuentro`: `id UUID PK`, `tenant_id FK→tenants RESTRICT`, `slot_id FK→slot_encuentro SET NULL` (nullable, independent instances), `materia_id FK→materia RESTRICT`, `fecha DATE NOT NULL`, `hora TIME NOT NULL`, `titulo TEXT NOT NULL`, `estado instancia_encuentro_estado NOT NULL DEFAULT 'Programado'`, `meet_url TEXT NULL`, `video_url TEXT NULL`, `comentario TEXT NOT NULL DEFAULT ''`, plus `created_at`,`updated_at`,`deleted_at`
- [x] 2.6 Create table `guardia`: `id UUID PK`, `tenant_id FK→tenants RESTRICT`, `asignacion_id FK→asignacion RESTRICT`, `materia_id FK→materia RESTRICT`, `carrera_id FK→carrera RESTRICT`, `cohorte_id FK→cohorte RESTRICT`, `dia dia_semana NOT NULL`, `horario TEXT NOT NULL`, `estado guardia_estado NOT NULL DEFAULT 'Pendiente'`, `comentarios TEXT NOT NULL DEFAULT ''`, `creada_at TIMESTAMPTZ NOT NULL DEFAULT now()`, plus `created_at`,`updated_at`,`deleted_at`
- [x] 2.7 Add named indexes: `ix_slot_tenant_id`, `ix_slot_asignacion`, `ix_slot_materia`, `ix_inst_tenant_id`, `ix_inst_slot`, `ix_inst_materia`, `ix_inst_fecha`, `ix_guardia_tenant_id`, `ix_guardia_asignacion`, `ix_guardia_materia`, `ix_guardia_cohorte`
- [x] 2.8 Seed permission idempotently with `ON CONFLICT DO NOTHING` per-tenant (same pattern as 008): `encuentros:gestionar` granted to PROFESOR, TUTOR, COORDINADOR, ADMIN — **CHECKPOINT RBAC (CRÍTICO): review and confirm grants before writing**
- [x] 2.9 Add the three tables and three enums to `_ensure_schema` in `backend/tests/conftest.py` (create enums if absent; drop `instancia_encuentro` before `slot_encuentro`; `guardia` independently; all before `asignacion`/`materia`/`carrera`/`cohorte`; drop the three enums at the end)
- [x] 2.10 Verify `alembic upgrade head` applies cleanly on the test DB (via conftest or manually)

## 3. Modelos SQLAlchemy

- [x] 3.1 Create `backend/app/models/encuentro.py`: define enums `DiaSemana`, `InstanciaEncuentroEstado`, `GuardiaEstado` (`str, enum.Enum`)
- [x] 3.2 Add `SlotEncuentro(Base, TenantScopedBase)` with FKs (`asignacion_id` RESTRICT, `materia_id` RESTRICT), `titulo`, `hora` (Time), `dia_semana` (SAEnum `dia_semana`, `create_type=False`, nullable), `fecha_inicio` (Date, nullable), `cant_semanas` (Integer default 0), `fecha_unica` (Date, nullable), `meet_url` (Text nullable), `vig_desde`/`vig_hasta` (Date nullable)
- [x] 3.3 Add `InstanciaEncuentro(Base, TenantScopedBase)` with `slot_id` (FK→slot_encuentro SET NULL, nullable), `materia_id` (RESTRICT), `fecha` (Date), `hora` (Time), `titulo`, `estado` (SAEnum `instancia_encuentro_estado`, `create_type=False`, default `Programado`), `meet_url` (nullable), `video_url` (nullable), `comentario` (Text default '')
- [x] 3.4 Add `Guardia(Base, TenantScopedBase)` with `asignacion_id` (RESTRICT), `materia_id` (RESTRICT), `carrera_id` (RESTRICT), `cohorte_id` (RESTRICT), `dia` (SAEnum `dia_semana`, `create_type=False`), `horario` (Text), `estado` (SAEnum `guardia_estado`, default `Pendiente`), `comentarios` (Text default ''), `creada_at` (DateTime tz) — split into `guardia.py` if `encuentro.py` exceeds 500 LOC
- [x] 3.5 Ensure all models have a `__repr__` that does not dump the full object (ids + key fields only)
- [x] 3.6 Update `backend/app/models/__init__.py` to export `SlotEncuentro`, `InstanciaEncuentro`, `Guardia` and the three enums
- [x] 3.7 Add `ENCUENTRO_GESTIONAR = "ENCUENTRO_GESTIONAR"` to `AuditAction` in `backend/app/models/audit.py`

## 4. Schemas Pydantic (`extra='forbid'`)

- [x] 4.1 Create `backend/app/schemas/encuentro.py`:
  - `CrearSlotRequest(materia_id: UUID, titulo: str, hora: time, dia_semana: DiaSemana | None, fecha_inicio: date | None, cant_semanas: int = 0, fecha_unica: date | None, meet_url: str | None, vig_desde: date | None, vig_hasta: date | None)` — `cant_semanas` validated `0..52`; NO `asignacion_id`/`tenant_id` accepted
  - `EditarInstanciaRequest(estado: InstanciaEncuentroEstado | None, meet_url: str | None, video_url: str | None, comentario: str | None)` — only mutable fields
  - `InstanciaEncuentroRead(id, slot_id, materia_id, fecha, hora, titulo, estado, meet_url, video_url, comentario)` — no `tenant_id`, `from_attributes=True`
  - `SlotEncuentroRead(id, materia_id, titulo, hora, dia_semana, fecha_inicio, cant_semanas, fecha_unica, meet_url)` — no `tenant_id`
  - `BloqueHtmlResponse(html: str)`
  - All with `model_config = ConfigDict(extra='forbid')`
- [x] 4.2 Create `backend/app/schemas/guardia.py`:
  - `RegistrarGuardiaRequest(materia_id: UUID, carrera_id: UUID, cohorte_id: UUID, dia: DiaSemana, horario: str, estado: GuardiaEstado = Pendiente, comentarios: str = "")` — NO `asignacion_id`/`tenant_id`
  - `GuardiaRead(id, asignacion_id, materia_id, carrera_id, cohorte_id, dia, horario, estado, comentarios, creada_at)` — no `tenant_id`
  - `GuardiaFiltros(materia_id: UUID | None, carrera_id: UUID | None, cohorte_id: UUID | None, dia: DiaSemana | None, estado: GuardiaEstado | None)`
  - All with `model_config = ConfigDict(extra='forbid')`

## 5. Generación de fechas recurrentes (función pura) — TDD

- [x] 5.1 [RED] Create `backend/tests/test_encuentro_recurrencia.py`; write `test_generates_one_date_per_week`: `fecha_inicio` on a Tuesday, `dia_semana=Martes`, `cant_semanas=4` → 4 dates 7 days apart — fails (no module)
- [x] 5.2 [GREEN] Create `backend/app/services/encuentro_recurrencia.py`: `generar_fechas(fecha_inicio, dia_semana, cant_semanas) -> list[date]` (weekly step from a start that already matches) — passes
- [x] 5.3 [RED] `test_first_instance_snaps_to_day_of_week`: `fecha_inicio` Monday, `dia_semana=Jueves`, `cant_semanas=2` → first date is next Thursday, second is +7 days — fails
- [x] 5.4 [GREEN] generalize: advance `fecha_inicio` to first matching `dia_semana`, then step weekly — passes
- [x] 5.5 [RED] `test_cant_semanas_zero_returns_empty` and `test_cant_semanas_one_returns_single` — fails; [GREEN] handle boundary counts — passes; confirm ≥90% coverage on this module

## 6. Bloque HTML del aula virtual (función pura) — TDD

- [x] 6.1 [RED] Create `backend/tests/test_encuentro_html.py`; `test_html_includes_recording_link_when_present`: instance with `video_url` → output contains the link — fails (no module)
- [x] 6.2 [GREEN] Create `backend/app/services/encuentro_html.py`: `generar_bloque_html(instancias) -> str` (title, date, time, meet, recording-if-present) — passes
- [x] 6.3 [RED] `test_html_omits_recording_link_when_absent`: instance with `video_url=None` → no recording link for it — fails; [GREEN] conditional rendering — passes
- [x] 6.4 [RED] `test_html_escapes_text_against_injection`: `titulo` with `<script>` → escaped in output — fails; [GREEN] apply `html.escape` to all text values — passes

## 7. Servicio de Encuentros (slots + instancias) — TDD

- [x] 7.1 [RED] Write `backend/tests/test_encuentros.py`; safety net; `test_crear_slot_recurrente_genera_n_instancias` (`cant_semanas=4` → 4 instancias `Programado`, `slot_id` set, `tenant_id` from session) — fails (no service/repo)
- [x] 7.2 [GREEN] Create `backend/app/repositories/encuentro_repository.py` (slots + instancias, tenant-scoped) and `backend/app/services/encuentro_service.py` `EncuentroService.crear_slot(req, current_user)`: resolve asignación from user+materia, generate dates via `generar_fechas`, persist slot + instances — passes
- [x] 7.3 [RED] `test_crear_encuentro_unico_genera_una_instancia` (`fecha_unica` set, `cant_semanas=0` → 1 instancia con `fecha=fecha_unica`) — fails; [GREEN] single-mode branch — passes
- [x] 7.4 [RED] `test_crear_slot_ambos_modos_raises_422` (both `cant_semanas>0` and `fecha_unica` → `EncuentroValidationError(422)`) and `test_crear_slot_ningun_modo_raises_422` — fails; [GREEN] validate exactly-one-mode (RN-13) — passes
- [x] 7.5 [RED] `test_editar_instancia_actualiza_estado_y_video` (set `Realizado` + `video_url` → instance updated, slot/siblings unchanged) — fails; [GREEN] `EncuentroService.editar_instancia(instancia_id, patch, current_user)` mutating only allowed fields, resolved within tenant — passes
- [x] 7.6 [RED] `test_editar_instancia_no_afecta_hermanas` (3 instancias, cancel 1 → other 2 unchanged) — fails; [GREEN] confirm per-instance edit (RN-14) — passes
- [x] 7.7 [RED] `test_listar_encuentros_coordinador_ve_todos` vs `test_listar_encuentros_profesor_ve_solo_propios` (F6.5: COORDINADOR/ADMIN transversal; PROFESOR filtered to own asignación) — fails; [GREEN] `EncuentroService.listar(current_user, filtros)` with role-based scoping, repo always tenant-filtered — passes
- [x] 7.8 [RED] `test_crear_slot_records_audit_encuentro_gestionar` (AuditEvent `accion='ENCUENTRO_GESTIONAR'`, `registros_afectados=N`) — fails; [GREEN] call `AuditService.record(...)` — passes
- [x] 7.9 [RED] `test_encuentros_tenant_isolation` (T1 slots/instances not visible in T2) — fails; [GREEN] confirm base-class tenant scoping; explicit assertion — passes

## 8. Servicio de Guardias — TDD

- [x] 8.1 [RED] Write `backend/tests/test_guardias.py`; safety net; `test_registrar_guardia_resuelve_asignacion_de_sesion` (TUTOR registers → `asignacion_id` from current_user, `tenant_id` from session, `estado=Pendiente`) — fails (no service/repo)
- [x] 8.2 [GREEN] Create `backend/app/repositories/guardia_repository.py` (tenant-scoped, filtered query) and `backend/app/services/guardia_service.py` `GuardiaService.registrar(req, current_user)` — passes
- [x] 8.3 [RED] `test_registrar_guardia_ignores_body_asignacion_id` (body with `asignacion_id` → 422 forbidden field, never used as selector) — fails; [GREEN] confirm schema `extra='forbid'` + identity from session (rules #8/#14) — passes
- [x] 8.4 [RED] `test_consultar_guardias_global_filtra_por_materia` (COORDINADOR queries by materia → all tutors' guardias of that materia) — fails; [GREEN] `GuardiaService.consultar(filtros, current_user)` with tenant-scoped filtered query — passes
- [x] 8.5 [RED] `test_consultar_guardias_filtra_por_estado` (`estado=Realizada` → only that state) — fails; [GREEN] apply state filter — passes
- [x] 8.6 [RED] `test_exportar_guardias_genera_csv` (export filtered register → CSV with one row per guardia and its fields) — fails; [GREEN] `GuardiaService.exportar(filtros, current_user)` building CSV — passes
- [x] 8.7 [RED] `test_guardias_tenant_isolation` (T1 guardias not visible/exportable in T2) — fails; [GREEN] confirm tenant scoping; explicit assertion — passes

## 9. Routers y endpoints

- [x] 9.1 Create `backend/app/api/v1/routers/encuentros.py`:
  - `POST /encuentros/slots` — JSON `CrearSlotRequest`; `require_permission("encuentros:gestionar")`; returns slot + created instances; map `EncuentroValidationError` → 422
  - `PATCH /encuentros/instancias/{instancia_id}` — JSON `EditarInstanciaRequest`; `require_permission("encuentros:gestionar")`; returns `InstanciaEncuentroRead`
  - `GET /encuentros/instancias` — query filtros; `require_permission("encuentros:gestionar")`; returns list[`InstanciaEncuentroRead`] (role-scoped: F6.5)
  - `GET /encuentros/bloque-html` — query `materia_id`/`slot_id`; `require_permission("encuentros:gestionar")`; returns `BloqueHtmlResponse`
- [x] 9.2 Create `backend/app/api/v1/routers/guardias.py`:
  - `POST /guardias` — JSON `RegistrarGuardiaRequest`; `require_permission("encuentros:gestionar")`; returns `GuardiaRead`
  - `GET /guardias` — query `GuardiaFiltros`; `require_permission("encuentros:gestionar")`; returns list[`GuardiaRead`]
  - `GET /guardias/export` — query `GuardiaFiltros`; `require_permission("encuentros:gestionar")`; returns CSV (`text/csv`)
- [x] 9.3 Register both routers in the v1 aggregator (prefixes `/encuentros`, `/guardias`; tags `encuentros`, `guardias`)
- [x] 9.4 Ensure all routes use `get_current_user`; identity, tenant and asignación derive from the JWT/session — never from body/path params (rules #8/#14)

## 10. Tests de integración HTTP (router-level)

- [x] 10.1 `test_crear_slot_endpoint_unauthenticated_returns_401`
- [x] 10.2 `test_crear_slot_endpoint_unauthorized_returns_403` (missing `encuentros:gestionar`)
- [x] 10.3 `test_crear_slot_recurrente_endpoint_creates_instances`
- [x] 10.4 `test_editar_instancia_endpoint_updates_estado`
- [x] 10.5 `test_bloque_html_endpoint_returns_html`
- [x] 10.6 `test_registrar_guardia_endpoint_creates_guardia` and `test_guardia_endpoint_unauthorized_returns_403`
- [x] 10.7 `test_export_guardias_endpoint_returns_csv`

## 11. Cobertura y cierre

- [x] 11.1 Run full test suite once at the end: `python -m pytest tests/ -q --ignore=tests/test_audit_migration.py --ignore=tests/test_auth_migration.py --ignore=tests/test_rbac_migration.py`; confirm all pre-existing tests still pass
- [x] 11.2 Check coverage: ≥80% líneas y ≥90% reglas de negocio (`generar_fechas`, modo único/recurrente, edición de instancia, bloque HTML, guardias); add tests if below threshold
- [x] 11.3 Verify all new files stay ≤500 LOC; split `encuentro.py` model into `guardia.py`, or `encuentro_service.py` into a guardia service, if any exceeds the limit
- [x] 11.4 Mark change `[x]` in CHANGES.md (estado del C-13)
