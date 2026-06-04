## ADDED Requirements

### Requirement: Create evaluation convocatoria with reservable day turns (F7.3, FL-07)
The system SHALL allow a user with `coloquios:gestionar` to create an `Evaluacion` (convocatoria) by specifying `materia_id`, `cohorte_id`, `tipo` (one of `Parcial`, `TP`, `Coloquio`, `Recuperatorio`), `instancia` (free-text denomination) and `dias_disponibles` (inscription window in days). In the same operation the system SHALL create one `TurnoEvaluacion` per requested day, each with its own `fecha` and `cupo_total` (a positive integer). The `tenant_id` SHALL be resolved from the authenticated session, never from the request body. A new convocatoria SHALL be created with `cerrada = false`.

#### Scenario: Create a coloquio convocatoria with multiple day turns
- **WHEN** a PROFESOR with `coloquios:gestionar` creates an `Evaluacion` of `tipo = Coloquio` with two turns: `fecha = D1, cupo_total = 10` and `fecha = D2, cupo_total = 8`
- **THEN** one `Evaluacion` row is created with `cerrada = false` and `tenant_id` from the session
- **AND** two `TurnoEvaluacion` rows are created referencing that `Evaluacion`, with cupos 10 and 8

#### Scenario: Cupo must be positive
- **WHEN** a creation request includes a turn with `cupo_total <= 0`
- **THEN** the system returns HTTP 422 and creates no `Evaluacion` and no `TurnoEvaluacion`

#### Scenario: Tenant isolation on convocatoria creation
- **WHEN** tenant T1 creates a convocatoria
- **THEN** querying convocatorias or turnos in tenant T2 never returns T1's records
- **AND** every convocatoria and turno query filters by `tenant_id` from the session

#### Scenario: Reservation permission cannot create a convocatoria
- **WHEN** a user holding only `coloquios:reservar` (ALUMNO) attempts to create a convocatoria
- **THEN** the system returns HTTP 403 (fail-closed) and creates nothing

---

### Requirement: Import candidate padron into a convocatoria (F7.2)
The system SHALL allow a user with `coloquios:gestionar` to import a list of `alumno_id` into a specific convocatoria, creating a `CandidatoEvaluacion` row per (`evaluacion_id`, `alumno_id`). The import SHALL be idempotent: re-importing an already-present candidate SHALL NOT create a duplicate. This padron is independent of the general padron. The `tenant_id` SHALL be resolved from the session.

#### Scenario: Import candidates creates one row per alumno
- **WHEN** a PROFESOR imports `[A1, A2, A3]` into a convocatoria with no prior candidates
- **THEN** three `CandidatoEvaluacion` rows exist for that convocatoria, one per alumno

#### Scenario: Re-importing is idempotent
- **WHEN** a PROFESOR imports `[A1, A2]` into a convocatoria that already has candidate `A1`
- **THEN** the convocatoria has candidates `A1` and `A2` with no duplicate row for `A1`

#### Scenario: Candidates are scoped to the convocatoria
- **WHEN** alumno `A1` is a candidate of convocatoria `E1` but not of `E2`
- **THEN** querying candidates of `E2` does not return `A1`

---

### Requirement: List convocatorias with operational metrics (F7.4)
The system SHALL allow a user with `coloquios:gestionar` to list convocatorias with, per convocatoria, its `materia`, `instancia`, available turns and the derived counters `convocados` (count of `CandidatoEvaluacion`), `reservas_activas` (count of `ReservaEvaluacion` with `estado = Activa`) and `cupos_libres` (sum of `cupo_total` minus `reservas_activas`). Counters SHALL be derived at query time, never stored denormalized. Soft-deleted rows SHALL be excluded.

#### Scenario: Convocatoria listing reflects current reservations
- **WHEN** a convocatoria has 12 candidates, total cupo 18 across its turns, and 5 active reservations
- **THEN** its listing row shows `convocados = 12`, `reservas_activas = 5`, `cupos_libres = 13`

#### Scenario: Cancelled reservations do not consume cupo
- **WHEN** a convocatoria with cupo 10 has 3 active and 2 cancelled reservations
- **THEN** `reservas_activas = 3` and `cupos_libres = 7`

---

### Requirement: Close a convocatoria (F7.5)
The system SHALL allow a user with `coloquios:gestionar` to close a convocatoria by setting `cerrada = true`. A closed convocatoria SHALL NOT accept new reservations. Closing SHALL NOT delete existing reservations or results. Deletion of a convocatoria or a turn SHALL be soft (`deleted_at`), never physical.

#### Scenario: Closing blocks new reservations
- **WHEN** a convocatoria is closed and an ALUMNO attempts to reserve a turn
- **THEN** the system returns HTTP 409 and creates no reservation

#### Scenario: Closing preserves existing data
- **WHEN** a convocatoria with active reservations and recorded results is closed
- **THEN** those reservations and results remain unchanged

---

### Requirement: All convocatoria management operations are audited
The system SHALL record an audit event in the audit log for every convocatoria management operation (create, import candidates, close, delete) and the actor SHALL be resolved from the authenticated session.

#### Scenario: Creating a convocatoria writes an audit event
- **WHEN** a PROFESOR creates a convocatoria
- **THEN** an audit event is recorded with the session's actor and tenant
