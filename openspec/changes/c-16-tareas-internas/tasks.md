## 1. Models — Tarea + ComentarioTarea + TareaEstado (D1, D2)

- [ ] 1.1 (RED) Write `backend/tests/models/test_tarea.py`: instantiating `Tarea` with required fields sets estado default-able, exposes `tenant_id`/`asignado_a`/`asignado_por`/`descripcion`/`materia_id`/`contexto_id`/`contexto_tipo`/`deleted_at`; assert `TareaEstado` is a `str`-enum with exactly `Pendiente | EnProgreso | Resuelta | Cancelada`.
- [ ] 1.2 (GREEN) Create `backend/app/models/tarea.py` with `TareaEstado(str, enum.Enum)` and the `Tarea` SQLAlchemy model on `TenantScopedBase` (UUID PK, soft-delete), `estado` mapped via `SAEnum(..., name="tarea_estado", create_type=False)`, FKs to `usuario.id` (asignado_a, asignado_por) and nullable `materia.id`; `contexto_id` UUID nullable (no FK), `contexto_tipo` String(50) nullable. Relationships `lazy="noload"` (D11).
- [ ] 1.3 (RED) Add to `test_tarea.py`: `ComentarioTarea` exposes `tenant_id`/`tarea_id`/`autor_id`/`cuerpo`/`es_sistema`/`deleted_at` and relates to `Tarea`.
- [ ] 1.4 (GREEN) Add `ComentarioTarea` model in the same module (UUID PK, soft-delete, FK `tarea_id` → `tarea.id`, FK `autor_id` → `usuario.id`, `es_sistema` bool flag, `cuerpo` text) with `lazy="noload"` relationship.
- [ ] 1.5 (TRIANGULATE+REFACTOR) Add a second case (e.g. contexto par both-null vs both-present at the model level) and refactor; keep file ≤500 LOC, snake_case.

## 2. Schemas — request/response (D6)

- [ ] 2.1 (RED) Write `backend/tests/schemas/test_tarea_schema.py`: the create schema rejects unknown fields (`extra='forbid'`) and rejects any identity field (`tenant_id`/`asignado_por`/`autor_id`); `asignado_a` IS accepted.
- [ ] 2.2 (GREEN) Create `backend/app/schemas/tarea.py` with Pydantic v2 schemas (`TareaCreate`, `TareaUpdateEstado`, `TareaDelegar`, `ComentarioTareaCreate`, response schemas) all with `model_config = ConfigDict(extra='forbid')`; NO identity fields in any request schema.
- [ ] 2.3 (RED) Add tests for contexto coherence: `contexto_id` without `contexto_tipo` (and vice-versa) is rejected; both-null and both-present are accepted.
- [ ] 2.4 (GREEN) Implement the contexto coherence validator (`model_validator`) enforcing both-null-or-both-present.
- [ ] 2.5 (TRIANGULATE+REFACTOR) Add edge cases (empty `descripcion`, invalid `estado` value) and refactor; file ≤500 LOC.

## 3. Migration 014 — schema, enums, RBAC, audit (D2, D8, D9)

- [ ] 3.1 Create `backend/alembic/versions/014_create_tareas_internas.py` with `revision="014"`, `down_revision="013"`.
- [ ] 3.2 Extend `audit_action` enum with `TAREA_ASIGNAR`, `TAREA_DELEGAR`, `TAREA_CAMBIAR_ESTADO` idempotently (`DO $$ ... ADD VALUE ... EXCEPTION WHEN duplicate_object THEN NULL $$`).
- [ ] 3.3 Create enum `tarea_estado` (Pendiente|EnProgreso|Resuelta|Cancelada) idempotently (mirror the `aviso_alcance` pattern in 013).
- [ ] 3.4 Create table `tarea` (tenant-scoped, UUID PK, soft-delete `deleted_at`, FKs `asignado_a`/`asignado_por` → `usuario.id`, nullable `materia_id` → `materia.id`, `contexto_id` UUID nullable without FK, `contexto_tipo` varchar(50) nullable, `estado` `tarea_estado`, `descripcion`) in FK order.
- [ ] 3.5 Create table `comentario_tarea` (tenant-scoped, UUID PK, soft-delete, FK `tarea_id` → `tarea.id`, FK `autor_id` → `usuario.id`, `es_sistema` bool, `cuerpo` text).
- [ ] 3.6 Add named indexes (D9): `ix_tarea_tenant_asignado_a_estado` (tenant_id, asignado_a, estado), `ix_tarea_tenant_asignado_por` (tenant_id, asignado_por), `ix_tarea_tenant_materia_id` (tenant_id, materia_id), `ix_tarea_tenant_estado` (tenant_id, estado), `ix_comentario_tarea_tenant_tarea_id` (tenant_id, tarea_id, created_at).
- [ ] 3.7 Seed permission `tareas:gestionar` (modulo `tareas`, accion `gestionar`) per tenant for COORDINADOR and ADMIN with `ON CONFLICT DO NOTHING` (mirror the `avisos:publicar` seed in 013).
- [ ] 3.8 Implement `downgrade()`: remove seeded `tareas:gestionar` rol_permiso/permiso rows, drop indexes, drop tables in reverse FK order (`comentario_tarea` then `tarea`), drop enum `tarea_estado`; document that the `audit_action` extension is NOT reversible (Postgres limitation) in a comment.

## 4. Repositories — tenant-scoped queries (D1, D10, D11)

- [ ] 4.1 (RED) Write `backend/tests/repositories/test_tarea_repository.py`: create/get/update/soft-delete scoped to tenant; cross-tenant access returns nothing (real PostgreSQL, NO DB mocks).
- [ ] 4.2 (GREEN) Implement `TareaRepository` in `backend/app/repositories/tarea_repository.py` (CRUD on `TenantScopedRepository`), all queries filtering by `tenant_id` + `deleted_at IS NULL`, relationships `noload`.
- [ ] 4.3 (RED) Add tests for `listar_mias` (only tareas where `asignado_a == usuario`, tenant-scoped) and the admin filter query covering each filter branch (`asignado_a`, `asignado_por`, `materia_id`, `estado`, `q` ILIKE) + combinations + tenant boundary.
- [ ] 4.4 (GREEN) Implement `listar_mias` and the admin filter query (single tenant-scoped query, optional filters, `ILIKE` on `descripcion`). Queries live ONLY in the repository.
- [ ] 4.5 (RED+GREEN) Implement and test `ComentarioTareaRepository` (`backend/app/repositories/tarea_repository.py` or sibling): add comment + list thread by `tarea_id`, tenant-scoped, `deleted_at IS NULL`, ordered by `created_at`; verify soft-deleted comments excluded.
- [ ] 4.6 (TRIANGULATE+REFACTOR) Add boundary cases (empty result sets, ILIKE no-match) and refactor; files ≤500 LOC.

## 5. Service — business rules / workflow (D3, D5, D6, D7, D8)

- [ ] 5.1 (RED) Write `backend/tests/services/test_tarea_service.py`: `publicar`/asignar sets estado `Pendiente`, resolves `tenant_id`/`asignado_por` from session, records `TAREA_ASIGNAR` audit; identity never from body.
- [ ] 5.2 (GREEN) Implement `tarea_service.py` `publicar`/asignar with audit `TAREA_ASIGNAR`.
- [ ] 5.3 (RED) Write tests for `cambiar_estado` covering EVERY legal transition of the D3 matrix (Pendiente→{EnProgreso,Resuelta,Cancelada}; EnProgreso→{Pendiente,Resuelta,Cancelada}; Resuelta→EnProgreso), each illegal transition → 409, and the no-op (same-state) → 409; assert `TAREA_CAMBIAR_ESTADO` audit on success.
- [ ] 5.4 (GREEN) Implement `cambiar_estado` with `_TRANSICIONES_VALIDAS: dict[TareaEstado, set[TareaEstado]]` matrix; raise HTTP 409 on illegal/no-op; record audit.
- [ ] 5.5 (RED) Write tests for `delegar`: reassigns `asignado_a`, overwrites `asignado_por` to the delegating actor, emits `TAREA_DELEGAR` audit (before/after), and inserts a system `ComentarioTarea` (`es_sistema=True`, `autor_id=actor`).
- [ ] 5.6 (GREEN) Implement `delegar` with audit + system comment insertion.
- [ ] 5.7 (RED) Write tests for ownership enforcement (D7): without `tareas:gestionar`, `cambiar_estado`/`comentar`/detail/thread are allowed ONLY when actor is `asignado_a`/`asignado_por` (else 403); with `tareas:gestionar`, any tarea of the tenant is allowed.
- [ ] 5.8 (GREEN) Implement ownership checks, `listar_mias`, `listar_admin`, `comentar` (identity from session), delegating to repositories.
- [ ] 5.9 (TRIANGULATE+REFACTOR) Add edge cases (delegate across tenant → 404, comment on foreign tarea → 403) and refactor; file ≤500 LOC.

## 6. Router — `/api/v1/tareas/*` + audit enum (D7, D8)

- [ ] 6.1 Extend `AuditAction` in `backend/app/models/audit.py` with `TAREA_ASIGNAR`, `TAREA_DELEGAR`, `TAREA_CAMBIAR_ESTADO`.
- [ ] 6.2 Create `backend/app/api/v1/routers/tareas.py`; no business logic in the router; current user from the JWT dependency.
- [ ] 6.3 (RED) Write `backend/tests/api/test_tareas_router.py` for the permission split (D7): `POST /tareas`, `POST /tareas/{id}/delegar`, `GET /tareas/admin`, `DELETE /tareas/{id}` require `tareas:gestionar` (403 without); `GET /tareas/mias`, `GET /tareas/{id}`, `PATCH /tareas/{id}/estado`, `POST|GET /tareas/{id}/comentarios` are authenticated with service-enforced ownership.
- [ ] 6.4 (GREEN) Implement the endpoints with `require_permission("tareas:gestionar")` on the gestión routes and plain auth on the self-service routes; delegate all logic to `tarea_service`.
- [ ] 6.5 Register the `tareas` router in `backend/app/main.py` (API v1 aggregator).
- [ ] 6.6 (TRIANGULATE+REFACTOR) Add success-path router tests for each endpoint and refactor; file ≤500 LOC.

## 7. Integration tests — spec scenarios end-to-end (real PostgreSQL)

- [ ] 7.1 (RED+GREEN) Integration: crear/asignar requires `tareas:gestionar` (403 without, success with) and writes a `TAREA_ASIGNAR` audit row; estado inicial `Pendiente`; `asignado_por` from JWT.
- [ ] 7.2 (RED+GREEN) Integration: `GET /tareas/mias` returns only the caller's assigned tareas, no others, tenant-scoped, without `tareas:gestionar`.
- [ ] 7.3 (RED+GREEN) Integration: state machine — every legal transition succeeds, illegal and no-op return 409; ownership (asignado_a self-service vs `tareas:gestionar`) enforced.
- [ ] 7.4 (RED+GREEN) Integration: delegación reassigns `asignado_a`, writes `TAREA_DELEGAR` audit, and inserts a system comment in the thread.
- [ ] 7.5 (RED+GREEN) Integration: comentarios — add + list thread; access control (asignado_a/asignado_por or `tareas:gestionar`); 403 for unrelated user; autor from session.
- [ ] 7.6 (RED+GREEN) Integration: `GET /tareas/admin` filters (`asignado_a`, `asignado_por`, `materia_id`, `estado`, `q` ILIKE) require `tareas:gestionar`; soft-delete hides the tarea everywhere.
- [ ] 7.7 (RED+GREEN) Integration: tenant isolation — tarea/comentario of another tenant is never visible/accessible (detail 404, state-change 404, admin list never crosses tenants).
- [ ] 7.8 (RED+GREEN) Integration: contexto polimórfico — both-null and both-present accepted; only-one-present rejected (422).

## 8. Migration apply/revert verification (D9)

- [ ] 8.1 Run `alembic upgrade head` against the test DB and verify tables `tarea`/`comentario_tarea`, enum `tarea_estado`, the five named indexes, the `tareas:gestionar` seed for COORDINADOR+ADMIN, and the extended `audit_action` values exist.
- [ ] 8.2 Run `alembic downgrade 013` and verify tables/indexes/enum and the `tareas:gestionar` seed are removed cleanly (the `audit_action` extension stays — documented Postgres limitation). asyncpg IS installed under Python 3.10 — this is doable.

## 9. Final verification

- [ ] 9.1 Run the full pytest suite against real PostgreSQL; all tests green, no DB mocks.
- [ ] 9.2 Confirm coverage thresholds (≥80% lines, ≥90% business rules) for the new module and that every new backend file stays ≤500 LOC.
