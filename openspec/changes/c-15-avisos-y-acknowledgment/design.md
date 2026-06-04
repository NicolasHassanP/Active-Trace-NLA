## Context

C-15 adds the system avisos board (F3.5, FL-09) on top of the existing multi-tenant Clean Architecture backend. It reuses the established building blocks: row-level `tenant_id` scoping (C-02), the `require_permission` RBAC guard (C-04), the audit log (C-05), and the academic structure Materia/Cohorte (C-06, archived). The domain has two entities (`Aviso`, `AcknowledgmentAviso`, KB §E13) and three behaviours: management, recipient visualization, and acknowledgment. The hard constraints are the project rules (identity from JWT, tenant scoping, fail-closed RBAC, soft delete, `extra='forbid'`, ≤500 LOC/file, one Alembic migration). Governance level: MEDIO.

## Goals / Non-Goals

**Goals:**
- Model `Aviso` (scope/severity/validity/order/ack flag) and `AcknowledgmentAviso` exactly per KB §E13.
- Enforce audience filtering (RN-20), validity window (RN-18) and acknowledgment (RN-19) in the repository/service layer, with tests.
- Derive view/ack counters from `AcknowledgmentAviso` (never denormalized).
- Add `avisos:publicar` RBAC permission and `AVISO_PUBLICAR` audit action, seeded per tenant in migration `013`.
- Prevent double-ack via a partial unique index.

**Non-Goals:**
- Frontend UI for the board (separate frontend change).
- Push/email delivery of avisos (this is an in-app board; outbound email is C-12 comunicaciones).
- A "viewed" (impression) counter distinct from ack — KB derives counters from `AcknowledgmentAviso`; we only model explicit acknowledgments. Pure view tracking is out of scope.
- Real-time notifications / websockets.

## Decisions

### D1 — Two tables, FK order Aviso → AcknowledgmentAviso
`aviso` and `acknowledgment_aviso`, both tenant-scoped with `deleted_at` and UUID PK (`gen_random_uuid()`), mirroring C-14. `acknowledgment_aviso.aviso_id` FK → `aviso.id`. Created in FK order in the migration. `aviso.materia_id` / `aviso.cohorte_id` are nullable FKs to the C-06 tables; `rol_destino` is a nullable enum/text matching the project role catalog. Alternative considered: a single JSONB "audience" column — rejected because scoped FK columns give referential integrity, indexable filtering, and clearer queries.

### D2 — New enums (idempotent)
`aviso_alcance` (Global | PorMateria | PorCohorte | PorRol) and `aviso_severidad` (Info | Advertencia | Critico). Created with the idempotent `DO $$ ... EXCEPTION WHEN duplicate_object THEN NULL $$` pattern from migration 012. `rol_destino` reuses the existing role enum/catalog rather than introducing a new type.

### D3 — Audience match lives in the repository as one tenant-scoped query
The recipient feed is a single SQLAlchemy query filtered by: `tenant_id = session.tenant`, `deleted_at IS NULL`, `activo = true`, `inicio_en <= now() <= fin_en`, AND an OR of the four alcance branches bound to the session's role(s)/cohorte/linked-materias. Ordering: `orden ASC, severidad` priority. This keeps audience logic in the repository (no business logic in routers, no DB access in services). Alternative considered: fetch all and filter in Python — rejected (not scalable, leaks tenant scoping responsibility out of the repo).

### D4 — Counters strictly derived
Ack count = `COUNT(*)` over `acknowledgment_aviso` WHERE `tenant_id` matches, `aviso_id` matches, `deleted_at IS NULL`. No counter column on `aviso`. Exposed via the service/read schema computed at query time (e.g. a subquery / correlated count or a separate count endpoint). This honours KB §E13 rule and avoids denormalization drift.

### D5 — Pending vs full feed
The recipient feed supports a "pending" view: avisos with `requiere_ack = true` that the session user has NOT yet acknowledged. Implemented as a LEFT JOIN / NOT EXISTS against `acknowledgment_aviso` for `(aviso_id, session.usuario_id, deleted_at IS NULL)`. Acknowledged avisos drop off the pending view but remain in the full feed and still count.

### D6 — Idempotent acknowledgment via partial unique index
Partial unique index `uq_ack_aviso_usuario` on (`tenant_id`, `aviso_id`, `usuario_id`) `WHERE deleted_at IS NULL`, mirroring the C-14 partial-index pattern. The service performs an upsert-style "ack or no-op": if an active ack exists, return success without inserting; otherwise insert. The index is defense-in-depth against races. Ack is only allowed for avisos the user can actually see (audience + window + active + not soft-deleted) — enforced in the service before insert.

### D7 — RBAC + audit seeding in migration 013
Seed permission `avisos:publicar` for roles COORDINADOR and ADMIN, per tenant, with `ON CONFLICT DO NOTHING` (pattern from migration 012 for `coloquios:gestionar`). Extend `audit_action` enum with `AVISO_PUBLICAR` idempotently (`DO $$ ... duplicate_object`). Reading the feed and acknowledging require only authentication (any role per audience), so no read/ack permission is seeded — visibility is enforced by audience rules, not RBAC.

### D8 — Schemas reject identity and unknown fields
All request schemas use `model_config = ConfigDict(extra='forbid')` and never declare `tenant_id`/`usuario_id`/`autor_id` — these come from the JWT-derived current-user dependency (C-04 `current-user-dependency`). Validity coherence (`fin_en > inicio_en`) and scope-context coherence (context field required per alcance) validated in Pydantic / service.

### D9 — Named indexes for query paths
Explicit named indexes: on `aviso (tenant_id, activo, inicio_en, fin_en)` for window+active filtering, on `aviso (tenant_id, cohorte_id)` and `aviso (tenant_id, materia_id)` for scoped lookups, and on `acknowledgment_aviso (tenant_id, aviso_id)` for the derived count. Follows the named-index rule from migration 012.

## Risks / Trade-offs

- [Audience query complexity — the four-branch OR with role/cohorte/materia binding is the most error-prone part] → Cover every branch and the tenant boundary with explicit tests (the spec scenarios map 1:1 to tests); keep the filter in one repository method.
- [User↔materia linkage source ambiguity — "a materia the user is linked to" depends on how C-06/C-07 model that link] → Resolve the exact linkage source (asignaciones/equipos vs cohorte→materia) during apply by reading the existing models; the spec phrasing stays linkage-agnostic. Captured as an open question.
- [Time-window boundaries (inclusive vs exclusive) and timezone] → Use timezone-aware UTC `now()` consistent with the rest of the backend; treat `[inicio_en, fin_en]` as inclusive; assert boundary behavior in tests.
- [Derived counter performance on large ack volumes] → Acceptable at expected scale; the `(tenant_id, aviso_id)` index supports the COUNT. Revisit with a materialized counter only if profiling demands it (out of scope now).

## Migration Plan

- Migration `013_create_avisos_acknowledgment.py`, `revision="013"`, `down_revision="012"`.
- `upgrade()`: (1) extend `audit_action` with `AVISO_PUBLICAR` (idempotent); (2) create enums `aviso_alcance`, `aviso_severidad` (idempotent); (3) create `aviso` then `acknowledgment_aviso` in FK order; (4) create named indexes (D9) and the partial unique index (D6); (5) seed `avisos:publicar` per tenant for COORDINADOR/ADMIN with `ON CONFLICT DO NOTHING`.
- `downgrade()`: drop indexes, drop `acknowledgment_aviso`, drop `aviso`, drop enums; remove seeded permission rows. The seeded `audit_action` enum value is left in place (Postgres enum value removal is unsafe), consistent with prior migrations.
- Rollback strategy: standard `alembic downgrade 012`. No data backfill required (new tables).

## Open Questions

- **OQ-1**: Exact source of the user↔materia link used by `PorMateria` visibility — confirm against C-06/C-07 models during apply (asignación docente, equipo, or cohorte→materia derivation). Does NOT block propose.
- **OQ-2**: Should `rol_destino` for `PorRol` support multiple roles per aviso, or exactly one? KB §E13 models a single `rol_destino` (nullable = todos); F3.5 text says "rol(es) destinatario(s)". Decision for propose: single `rol_destino` per aviso (matches the data model); multi-role can be achieved with multiple avisos. Revisit if the user wants a true many-to-many.
- **OQ-3**: Is a distinct "viewed/impression" counter required in addition to ack? KB derives counters from `AcknowledgmentAviso` only, so we model ack only. Confirm no separate impression tracking is expected.
