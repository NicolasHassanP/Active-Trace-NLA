## ADDED Requirements

### Requirement: Coloquios metrics panel (F7.1)
The system SHALL allow a user with `coloquios:gestionar` to retrieve aggregate metrics for the tenant's coloquios: total alumnos cargados (distinct candidates across convocatorias), cantidad de convocatorias activas (`cerrada = false`, not soft-deleted), reservas activas (count of `ReservaEvaluacion` with `estado = Activa`) and notas registradas (count of `ResultadoEvaluacion`). All metrics SHALL be derived at query time and scoped to the session's tenant.

#### Scenario: Metrics reflect current state
- **WHEN** a tenant has 2 active convocatorias, 30 distinct candidates, 12 active reservations and 4 recorded results
- **THEN** the metrics panel returns `convocatorias_activas = 2`, `alumnos_cargados = 30`, `reservas_activas = 12`, `notas_registradas = 4`

#### Scenario: Metrics are tenant-scoped
- **WHEN** tenant T1 has 5 active reservations and tenant T2 has 9
- **THEN** the metrics panel for T1 returns `reservas_activas = 5` and never counts T2's data

---

### Requirement: Consolidated reservation agenda (F7.5, HU-32)
The system SHALL allow a user with `coloquios:gestionar` to retrieve a consolidated agenda of active reservations across convocatorias, filterable by `materia`, responsible/asignacion, date range and free-text search. Each agenda entry SHALL expose the convocatoria, the turn `fecha`, the alumno and the reservation state. Only `estado = Activa` reservations SHALL appear in the agenda by default.

#### Scenario: Agenda lists active reservations across convocatorias
- **WHEN** two convocatorias each have active reservations
- **THEN** the agenda returns entries from both convocatorias, each with its turn date and alumno

#### Scenario: Agenda filters by date range
- **WHEN** the agenda is requested with a date range covering only turn date D1
- **THEN** only reservations on turns with `fecha = D1` are returned

#### Scenario: Cancelled reservations are excluded from the agenda
- **WHEN** a convocatoria has 2 active and 1 cancelled reservations
- **THEN** the agenda returns the 2 active reservations and not the cancelled one

---

### Requirement: Record and consult academic results (F7.5, HU-33)
The system SHALL allow a user with `coloquios:gestionar` to record a `ResultadoEvaluacion` with a `nota_final` (free text, numeric or qualitative) per (`evaluacion_id`, `alumno_id`), and SHALL allow consulting the consolidated academic register of final notes. Recording a result for the same (`evaluacion_id`, `alumno_id`) again SHALL update the existing `nota_final` rather than creating a duplicate. The `tenant_id` SHALL be resolved from the session.

#### Scenario: Record a final note
- **WHEN** a PROFESOR records `nota_final = "8"` for alumno A1 in convocatoria E1
- **THEN** a `ResultadoEvaluacion` exists for (E1, A1) with `nota_final = "8"`

#### Scenario: Re-recording updates the note in place
- **WHEN** a PROFESOR records `nota_final = "Aprobado"` for (E1, A1) which already has a result
- **THEN** the existing `ResultadoEvaluacion` for (E1, A1) is updated and no duplicate row is created

#### Scenario: Consolidated register lists final notes
- **WHEN** a COORDINADOR consults the academic register of convocatoria E1 which has results for A1 and A2
- **THEN** the register returns the final notes of A1 and A2 scoped to the tenant

#### Scenario: Alumno reads only their own result
- **WHEN** an ALUMNO consults their result for a convocatoria where they have a recorded nota
- **THEN** the system returns that alumno's own `nota_final` and never another alumno's result
