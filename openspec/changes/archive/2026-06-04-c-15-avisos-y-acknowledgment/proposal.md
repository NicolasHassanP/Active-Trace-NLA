## Why

Institutions need a controlled channel to publish announcements (academic news, operational alerts, urgent notices) targeted at specific audiences and to know who has read the ones that matter. Today there is no system bulletin board: coordinators communicate ad hoc, with no segmentation, no validity window, and no proof of receipt. C-15 delivers the avisos board (F3.5) with audience scoping (RN-20), validity windows (RN-18) and read acknowledgment (RN-19).

## What Changes

- New `Aviso` model: `alcance` (Global | PorMateria | PorCohorte | PorRol), `materia_id`/`cohorte_id`/`rol_destino` context, `severidad` (Info | Advertencia | Critico), `titulo`, `cuerpo`, `inicio_en`/`fin_en` validity window, `orden` (presentation priority), `activo`, `requiere_ack`.
- New `AcknowledgmentAviso` model: one row per (`aviso`, `usuario`) read confirmation with `confirmado_at`.
- ABM (alta/baja/modificación) of avisos guarded by a new permission `avisos:publicar` (roles COORDINADOR, ADMIN). Fail-closed: no permission → 403.
- Recipient feed: any authenticated user retrieves the avisos that match their role/scope/cohorte AND fall inside the active validity window, ordered by priority.
- Acknowledgment endpoint: any role may confirm reading an aviso that requires ack; once acknowledged it drops off that user's pending feed but still counts.
- View/ack counters are DERIVED on read (COUNT over `AcknowledgmentAviso`, tenant-scoped, not soft-deleted) — NEVER stored denormalized.
- New REST routes under `/api/avisos/*`.
- Alembic migration `013` (down_revision `012`): new enums, `aviso` + `acknowledgment_aviso` tables in FK order, named indexes, a partial unique index to prevent double-ack, and per-tenant seed of `avisos:publicar` plus the `AVISO_PUBLICAR` audit action.

## Capabilities

### New Capabilities
- `avisos-publicacion`: management (alta/baja/modificación) of avisos by COORDINADOR/ADMIN, including scope, severity, target roles, validity window, ordering and ack requirement. Covers F3.5 management side and FL-09 creation.
- `avisos-visualizacion`: recipient-facing retrieval of avisos filtered by audience (RN-20) and validity window (RN-18), ordered by priority.
- `avisos-acknowledgment`: read confirmation by any role (RN-19), idempotent per user, with counters derived from `AcknowledgmentAviso`.

### Modified Capabilities
<!-- None. Avisos is a new domain; no existing spec requirements change. -->

## Impact

- **Models**: `backend/app/models/aviso.py` (new — `Aviso`, `AcknowledgmentAviso`).
- **Repositories**: `backend/app/repositories/aviso_repository.py` (new — tenant-scoped, audience + validity filtering, derived counters).
- **Services**: `backend/app/services/aviso_service.py` (new — management, recipient feed, ack).
- **Schemas**: `backend/app/schemas/aviso.py` (new — `extra='forbid'`, no identity fields in body).
- **Routers**: `backend/app/api/v1/routers/avisos.py` (new — `/api/avisos/*`).
- **Migration**: `backend/alembic/versions/013_create_avisos_acknowledgment.py` (new).
- **RBAC**: new permission `avisos:publicar` seeded per tenant.
- **Audit**: new `audit_action` enum value `AVISO_PUBLICAR`.
- **Dependencies**: C-06 (estructura académica — Materia/Cohorte) already archived/satisfied; reuses C-04 RBAC guard and C-05 audit log.
