## ADDED Requirements

### Requirement: Register a guardia (F6.6)
The system SHALL allow a user with `encuentros:gestionar` (typically a TUTOR) to register a `Guardia` recording who covered it (their own asignación), the materia, carrera, cohorte, day of week, time range (`horario`), state and comments. The covering `asignacion_id` and `tenant_id` SHALL be resolved from the authenticated session, never from the request body. A new guardia SHALL start in state `Pendiente`.

#### Scenario: Tutor registers their own guardia
- **WHEN** a TUTOR with `encuentros:gestionar` registers a guardia for materia M, carrera C, cohorte K, `dia = Miércoles`, `horario = "14:00–14:45"`
- **THEN** a `Guardia` is created with `asignacion_id` resolved from the session, `tenant_id` from the session, and `estado = Pendiente`

#### Scenario: asignacion_id is never taken from the request body
- **WHEN** a registration request includes an `asignacion_id` in the body
- **THEN** the system rejects the request (HTTP 422, forbidden field) and does not use it as an identity selector

#### Scenario: Tenant isolation on guardia registration
- **WHEN** tenant T1 registers a guardia
- **THEN** querying guardias in tenant T2 never returns T1's records
- **AND** every guardia query filters by `tenant_id` from the session

---

### Requirement: Global guardia query for coordination (F6.6)
The system SHALL allow users with role COORDINADOR or ADMIN to query the global guardia register of the tenant, filterable by materia, carrera, cohorte, day and state. Every query SHALL filter by `tenant_id` from the session.

#### Scenario: Coordinator queries all guardias filtered by materia
- **WHEN** a COORDINADOR queries guardias filtering by materia M
- **THEN** the result includes all guardias of materia M in the tenant, regardless of which tutor registered them

#### Scenario: Filter by state returns only matching guardias
- **WHEN** a COORDINADOR queries guardias filtering by `estado = Realizada`
- **THEN** only guardias in state `Realizada` are returned

---

### Requirement: Export the guardia register (F6.6)
The system SHALL allow users with role COORDINADOR or ADMIN to export the filtered guardia register as a downloadable file (CSV), including who covered it, materia, carrera/cohorte, day, time range, state and comments.

#### Scenario: Export produces a CSV of the filtered register
- **WHEN** a COORDINADOR exports the guardia register filtered by cohorte K
- **THEN** the system returns a CSV file containing one row per guardia of cohorte K with its fields

#### Scenario: Export respects tenant isolation
- **WHEN** a COORDINADOR of tenant T1 exports the register
- **THEN** the CSV contains only T1's guardias and never any record from another tenant

---

### Requirement: Guardia operations are permission-guarded (fail-closed)
The system SHALL reject guardia operations for users without the `encuentros:gestionar` permission, following the fail-closed RBAC policy, and SHALL reject unauthenticated requests.

#### Scenario: User without permission cannot register a guardia
- **WHEN** a user without `encuentros:gestionar` calls any guardia endpoint
- **THEN** the system returns HTTP 403

#### Scenario: Unauthenticated request is rejected
- **WHEN** a request to any guardia endpoint arrives without a valid JWT
- **THEN** the system returns HTTP 401
