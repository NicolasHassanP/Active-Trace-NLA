## 1. Migration 013 — schema, enums, RBAC, audit (D1, D2, D6, D7, D9)

- [x] 1.1 Create `backend/alembic/versions/013_create_avisos_acknowledgment.py` with `revision="013"`, `down_revision="012"`.
- [x] 1.2 Extend `audit_action` enum with `AVISO_PUBLICAR` idempotently (`DO $$ ... EXCEPTION WHEN duplicate_object THEN NULL $$`).
- [x] 1.3 Create enums `aviso_alcance` (Global|PorMateria|PorCohorte|PorRol) and `aviso_severidad` (Info|Advertencia|Critico) idempotently.
- [x] 1.4 Create table `aviso` (tenant-scoped, UUID PK, soft-delete `deleted_at`, FKs to materia/cohorte nullable, `rol_destino` nullable, validity/orden/activo/requiere_ack columns) in FK order.
- [x] 1.5 Create table `acknowledgment_aviso` (tenant-scoped, UUID PK, soft-delete, FK `aviso_id` → `aviso.id`, `usuario_id`, `confirmado_at`).
- [x] 1.6 Add named indexes: `aviso (tenant_id, activo, inicio_en, fin_en)`, `aviso (tenant_id, cohorte_id)`, `aviso (tenant_id, materia_id)`, `acknowledgment_aviso (tenant_id, aviso_id)`.
- [x] 1.7 Add partial unique index `uq_ack_aviso_usuario` on `(tenant_id, aviso_id, usuario_id) WHERE deleted_at IS NULL`.
- [x] 1.8 Seed permission `avisos:publicar` per tenant for COORDINADOR and ADMIN with `ON CONFLICT DO NOTHING`.
- [x] 1.9 Implement `downgrade()`: drop indexes, drop tables in reverse FK order, drop enums, remove seeded permission rows (leave audit enum value in place).
- [x] 1.10 Run the migration up/down against the test DB to confirm it applies and reverts cleanly.

## 2. Models (D1)

- [x] 2.1 Create `backend/app/models/aviso.py` with the `Aviso` SQLAlchemy model (tenant_id, alcance, materia_id, cohorte_id, rol_destino, severidad, titulo, cuerpo, inicio_en, fin_en, orden, activo, requiere_ack, deleted_at).
- [x] 2.2 Add the `AcknowledgmentAviso` model in the same module (tenant_id, aviso_id, usuario_id, confirmado_at, deleted_at) with relationship to `Aviso`.

## 3. Schemas (D8)

- [x] 3.1 Create `backend/app/schemas/aviso.py` request schemas (create/update) with `model_config = ConfigDict(extra='forbid')`; NO `tenant_id`/`autor_id`/`usuario_id` fields.
- [x] 3.2 Add scope-context coherence validation (materia_id/cohorte_id/rol_destino required per alcance; null for Global) and validity coherence (`fin_en > inicio_en`).
- [x] 3.3 Add response schemas including the derived ack count field (computed, not a stored column).

## 4. Repository — tenant-scoped queries (D3, D4, D5)

- [x] 4.1 (RED) Write tests for `aviso_repository`: create/get/update/soft-delete scoped to tenant; cross-tenant access returns nothing.
- [x] 4.2 (GREEN) Implement CRUD methods in `backend/app/repositories/aviso_repository.py`, all filtering by tenant and `deleted_at IS NULL`.
- [x] 4.3 (RED) Write tests for the recipient feed query covering all four alcance branches (Global / PorRol / PorCohorte / PorMateria) + tenant boundary.
- [x] 4.4 (GREEN) Implement the recipient feed query (audience OR-branches bound to session role/cohorte/materias) with `activo` + window filter and `orden ASC, severidad` ordering.
- [x] 4.5 (RED+GREEN) Implement and test the "pending" feed variant (requiere_ack AND NOT EXISTS active ack for the user).
- [x] 4.6 (RED+GREEN) Implement and test the derived ack COUNT (tenant-scoped, deleted_at IS NULL); verify soft-deleted acks are excluded.

## 5. Service — business rules (D5, D6, D8)

- [x] 5.1 (RED) Write tests for `aviso_service` management: publish/modify/soft-delete; identity (tenant) taken from session; invalid scope/validity rejected.
- [x] 5.2 (GREEN) Implement management methods; record `AVISO_PUBLICAR` audit entry on create.
- [x] 5.3 (RED) Write tests for acknowledgment: ack visible aviso; cannot ack out-of-audience/out-of-window/inactive/deleted aviso; idempotent double-ack; identity from session.
- [x] 5.4 (GREEN) Implement ack-or-no-op logic guarded by visibility check; rely on partial unique index as defense-in-depth.
- [x] 5.5 (RED+GREEN) Implement feed/pending retrieval delegating audience+window+ordering to the repository; expose derived counters.

## 6. Router — `/api/avisos/*` (D7, D8)

- [x] 6.1 Create `backend/app/api/v1/routers/avisos.py`; no business logic in the router.
- [x] 6.2 Add management endpoints (create/update/delete) guarded by `require_permission("avisos:publicar")`; derive current user from the JWT dependency.
- [x] 6.3 Add recipient feed endpoint (full + pending) — authenticated, any role; visibility enforced by audience rules, not RBAC.
- [x] 6.4 Add acknowledgment endpoint — authenticated, any role; identity from session.
- [x] 6.5 Register the router in the API v1 router aggregator.

## 7. Integration tests & verification (spec scenarios)

- [x] 7.1 (RED+GREEN) Integration test: publish requires `avisos:publicar` (403 without it, success with it) and writes an `AVISO_PUBLICAR` audit row.
- [x] 7.2 (RED+GREEN) Integration test: scope filtering — Global/PorRol/PorCohorte/PorMateria each shown only to the right recipients, never across tenants.
- [x] 7.3 (RED+GREEN) Integration test: validity window — not-yet-started and expired avisos are hidden; in-window shown; assert inclusive boundary behavior.
- [x] 7.4 (RED+GREEN) Integration test: acknowledgment — ack drops the aviso from the pending feed AND increments the derived ack count; double-ack stays at one row.
- [x] 7.5 (RED+GREEN) Integration test: priority ordering — lower `orden` first, severidad breaks ties.
- [x] 7.6 Confirm coverage thresholds (≥80% lines, ≥90% business rules) for the new module and that all files stay ≤500 LOC.
