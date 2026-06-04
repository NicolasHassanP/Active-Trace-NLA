## ADDED Requirements

### Requirement: Publish an aviso with audience, validity and ack settings (F3.5, FL-09)
The system SHALL allow a user with `avisos:publicar` (roles COORDINADOR, ADMIN) to create an `Aviso` with `alcance` (Global | PorMateria | PorCohorte | PorRol), optional `materia_id`/`cohorte_id`/`rol_destino` context, `severidad` (Info | Advertencia | Critico), `titulo`, `cuerpo`, validity window `inicio_en`/`fin_en`, `orden`, `activo` and `requiere_ack`. The publishing user's `tenant_id` SHALL be resolved from the authenticated session, NEVER from the request body, URL or header. Request bodies SHALL reject unknown fields (`extra='forbid'`) and SHALL NOT accept any acting-user identity field. Creating an aviso SHALL be recorded in the audit log with action `AVISO_PUBLICAR`.

#### Scenario: COORDINADOR publishes a global aviso
- **WHEN** a COORDINADOR with `avisos:publicar` creates a Global aviso with valid `inicio_en` < `fin_en`
- **THEN** the aviso is persisted under the caller's tenant with `activo` as provided
- **AND** an audit entry with action `AVISO_PUBLICAR` is recorded

#### Scenario: User without permission cannot publish
- **WHEN** a user lacking `avisos:publicar` attempts to create an aviso
- **THEN** the system returns HTTP 403 and creates no aviso

#### Scenario: Identity comes from the session, not the body
- **WHEN** a publish request body contains a `tenant_id` or `autor_id` different from the authenticated user
- **THEN** the aviso is created under the authenticated user's tenant and the body values are ignored (or rejected as unknown fields)

### Requirement: Scope context must match the chosen alcance
The system SHALL require `materia_id` when `alcance = PorMateria`, `cohorte_id` when `alcance = PorCohorte`, and `rol_destino` when `alcance = PorRol`. When `alcance = Global`, context fields SHALL be null. Referenced `materia_id`/`cohorte_id` SHALL belong to the caller's tenant. An invalid combination SHALL be rejected.

#### Scenario: PorMateria without materia_id is rejected
- **WHEN** a publisher creates an aviso with `alcance = PorMateria` and no `materia_id`
- **THEN** the system returns HTTP 422 and creates no aviso

#### Scenario: PorCohorte with a cohorte from another tenant is rejected
- **WHEN** a publisher creates an aviso with `alcance = PorCohorte` referencing a `cohorte_id` of a different tenant
- **THEN** the system returns HTTP 404/422 and creates no aviso

#### Scenario: Global aviso ignores context fields
- **WHEN** a publisher creates an aviso with `alcance = Global`
- **THEN** the aviso is created with `materia_id`, `cohorte_id` and `rol_destino` null

### Requirement: Validity window must be coherent
The system SHALL reject an aviso whose `fin_en` is not strictly after `inicio_en`.

#### Scenario: fin_en before inicio_en is rejected
- **WHEN** a publisher creates an aviso with `fin_en` earlier than or equal to `inicio_en`
- **THEN** the system returns HTTP 422 and creates no aviso

### Requirement: Modify and soft-delete an aviso
The system SHALL allow a user with `avisos:publicar` to modify an existing aviso (including `activo`, `orden`, validity window, scope and `requiere_ack`) and to soft-delete it (`deleted_at`). Soft-deleted avisos SHALL NOT appear in any recipient feed and SHALL NOT count toward any derived counter. All operations SHALL be scoped to the caller's tenant. Hard delete SHALL NOT be supported.

#### Scenario: Deactivating an aviso removes it from recipient feeds
- **WHEN** a publisher sets `activo = false` on an aviso currently inside its validity window
- **THEN** the aviso no longer appears in any recipient feed

#### Scenario: Soft-deleting an aviso hides it everywhere
- **WHEN** a publisher soft-deletes an aviso
- **THEN** the aviso's `deleted_at` is set and it appears in no recipient feed nor counter

#### Scenario: Cannot modify an aviso from another tenant
- **WHEN** a publisher attempts to modify an aviso belonging to a different tenant
- **THEN** the system returns HTTP 404 and the aviso is unchanged
