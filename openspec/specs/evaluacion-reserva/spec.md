## ADDED Requirements

### Requirement: Reserve a turn with cupo control (F7, FL-07)
The system SHALL allow a user with `coloquios:reservar` (ALUMNO) to reserve a `TurnoEvaluacion` that has available cupo, creating a `ReservaEvaluacion` with `estado = Activa`. The reserving `alumno_id` and `tenant_id` SHALL be resolved from the authenticated session, NEVER from the request body, URL or header. A reservation SHALL only be created when the turn's active reservations are strictly fewer than its `cupo_total`. The cupo check SHALL be performed under a row-level lock on the turn to prevent over-booking under concurrency.

#### Scenario: Reserving an available turn creates an active reservation
- **WHEN** an eligible ALUMNO reserves a turn with `cupo_total = 10` and 3 active reservations
- **THEN** a `ReservaEvaluacion` with `estado = Activa` is created for that alumno on that turn
- **AND** the turn now has 4 active reservations and 6 cupos libres

#### Scenario: Reserving a full turn is rejected
- **WHEN** an eligible ALUMNO reserves a turn whose active reservations already equal `cupo_total`
- **THEN** the system returns HTTP 409 and creates no reservation

#### Scenario: Concurrent reservations never exceed cupo
- **WHEN** two eligible alumnos concurrently reserve the last remaining cupo of a turn
- **THEN** exactly one reservation succeeds and the other receives HTTP 409
- **AND** the turn's active reservations never exceed `cupo_total`

#### Scenario: Identity comes from the session, not the body
- **WHEN** a reservation request body contains an `alumno_id` different from the authenticated user
- **THEN** the reservation is created for the authenticated user and the body value is ignored

---

### Requirement: Only imported candidates can reserve (F7.2 gating)
The system SHALL allow a reservation only when the authenticated ALUMNO exists as an active `CandidatoEvaluacion` of the turn's convocatoria. An alumno who is not in the convocatoria's candidate padron SHALL be rejected.

#### Scenario: Non-candidate alumno cannot reserve
- **WHEN** an ALUMNO who is not a candidate of the convocatoria attempts to reserve one of its turns
- **THEN** the system returns HTTP 403 and creates no reservation

#### Scenario: Candidate alumno can reserve
- **WHEN** an ALUMNO who is a candidate of the convocatoria reserves an available turn
- **THEN** the reservation is created with `estado = Activa`

---

### Requirement: One active reservation per alumno per convocatoria
The system SHALL allow at most one `ReservaEvaluacion` with `estado = Activa` for a given (`alumno_id`, `evaluacion_id`) across all turns of that convocatoria. A second active reservation attempt SHALL be rejected while the first remains active.

#### Scenario: Second active reservation in the same convocatoria is rejected
- **WHEN** an ALUMNO with an active reservation on turn T1 of convocatoria E1 attempts to reserve turn T2 of E1
- **THEN** the system returns HTTP 409 and creates no second reservation

#### Scenario: Reserving in a different convocatoria is allowed
- **WHEN** an ALUMNO has an active reservation in convocatoria E1 and reserves a turn in convocatoria E2 (of which they are a candidate)
- **THEN** the reservation in E2 is created successfully

---

### Requirement: Cancel a reservation frees the cupo
The system SHALL allow the owning ALUMNO (resolved from the session) to cancel their own `ReservaEvaluacion` by setting `estado = Cancelada`. Cancelling SHALL free one cupo on the turn and SHALL allow the alumno to reserve again in that convocatoria.

#### Scenario: Cancelling frees a cupo
- **WHEN** an ALUMNO cancels their active reservation on a turn with `cupo_total = 10` and 4 active reservations
- **THEN** that reservation's `estado` becomes `Cancelada` and the turn has 3 active reservations and 7 cupos libres

#### Scenario: After cancelling, the alumno can reserve again
- **WHEN** an ALUMNO cancels their active reservation in a convocatoria and then reserves another available turn of the same convocatoria
- **THEN** the new reservation is created with `estado = Activa`

#### Scenario: An alumno cannot cancel another alumno's reservation
- **WHEN** an ALUMNO attempts to cancel a reservation that belongs to a different alumno
- **THEN** the system returns HTTP 403 or 404 and the target reservation remains `Activa`

---

### Requirement: Reservations respect tenant isolation
The system SHALL scope every reservation operation to the tenant of the authenticated session. A reservation SHALL never reference a turn, convocatoria or alumno of another tenant.

#### Scenario: Cross-tenant turn is not reservable
- **WHEN** an ALUMNO of tenant T1 attempts to reserve a turn belonging to tenant T2
- **THEN** the system returns HTTP 404 and creates no reservation
