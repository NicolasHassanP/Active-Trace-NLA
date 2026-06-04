## ADDED Requirements

### Requirement: Create recurring encounter slot (F6.1, RN-13)
The system SHALL allow a user with `encuentros:gestionar` to create a recurring `SlotEncuentro` by specifying materia, day of week, start time, start date and a number of weeks (`cant_semanas`). Upon creation the system SHALL automatically generate exactly `cant_semanas` `InstanciaEncuentro` rows, one per week, each in state `Programado`, inheriting the slot's `titulo`, `hora`, `meet_url` and `materia_id`. The owning `asignacion_id` and `tenant_id` SHALL be resolved from the authenticated session, never from the request body.

#### Scenario: Recurring slot generates one instance per week
- **WHEN** a PROFESOR with `encuentros:gestionar` creates a slot with `dia_semana = Martes`, `fecha_inicio` on a Tuesday, and `cant_semanas = 4`
- **THEN** 4 `InstanciaEncuentro` rows are created with dates one week apart, all in state `Programado`
- **AND** each instance has `tenant_id` from the session and `slot_id` pointing to the created slot

#### Scenario: First instance falls on the configured day of week
- **WHEN** a slot is created with `dia_semana = Jueves` and `fecha_inicio` on a Monday, `cant_semanas = 2`
- **THEN** the first generated instance date is the next Thursday on or after `fecha_inicio`
- **AND** the second instance date is exactly 7 days after the first

#### Scenario: Tenant isolation on slot creation
- **WHEN** tenant T1 creates a slot
- **THEN** querying slots or instances in tenant T2 never returns T1's records
- **AND** every slot and instance query filters by `tenant_id` from the session

---

### Requirement: Create single encounter (F6.2, RN-13)
The system SHALL allow a user with `encuentros:gestionar` to create a single (non-recurring) encounter by specifying a single date (`fecha_unica`), time and title. The system SHALL generate exactly one `InstanciaEncuentro` in state `Programado`. Recurring and single modes are mutually exclusive.

#### Scenario: Single encounter generates exactly one instance
- **WHEN** a PROFESOR creates a single encounter with `fecha_unica` set and `cant_semanas = 0`
- **THEN** exactly one `InstanciaEncuentro` is created with `fecha = fecha_unica` in state `Programado`

#### Scenario: Providing both recurrence and single date is rejected
- **WHEN** a creation request includes both `cant_semanas > 0` and `fecha_unica`
- **THEN** the system returns HTTP 422 and creates no slot or instance

#### Scenario: Providing neither recurrence nor single date is rejected
- **WHEN** a creation request includes `cant_semanas = 0` and no `fecha_unica`
- **THEN** the system returns HTTP 422 and creates no slot or instance

---

### Requirement: Edit an encounter instance (F6.3, RN-14)
The system SHALL allow a user with `encuentros:gestionar` to edit an individual `InstanciaEncuentro`, modifying only `estado`, `meet_url`, `video_url` (recording) and `comentario`. Editing one instance SHALL NOT affect its slot nor any sibling instance. Immutable fields (`fecha`, `hora`, `slot_id`, `materia_id`, `tenant_id`) SHALL NOT be changed via this operation. The instance SHALL be resolved within the tenant of the session.

#### Scenario: Marking an instance as realizada records the recording URL
- **WHEN** a PROFESOR edits an instance setting `estado = Realizado` and `video_url = "https://video/abc"`
- **THEN** that instance's `estado` is `Realizado` and `video_url` is stored
- **AND** the slot and all sibling instances remain unchanged

#### Scenario: Editing one instance does not change siblings
- **WHEN** a slot has 3 instances and one is set to `Cancelado`
- **THEN** the other 2 instances retain their previous state

#### Scenario: Attempt to change an immutable field is rejected
- **WHEN** an edit request includes `fecha` or `materia_id`
- **THEN** the system returns HTTP 422 (schema rejects unknown/forbidden fields) and the instance is unchanged

---

### Requirement: Admin view of all encounters (F6.5)
The system SHALL provide a transversal listing of `InstanciaEncuentro` across the tenant for users with role COORDINADOR or ADMIN, beyond the encounters they created. A PROFESOR SHALL only see instances belonging to slots owned by their own asignación. Every listing query SHALL filter by `tenant_id` from the session.

#### Scenario: Coordinator sees all tenant encounters
- **WHEN** a COORDINADOR lists encounters and two different PROFESORes created slots in the tenant
- **THEN** the listing includes instances from both PROFESORes' slots

#### Scenario: Profesor sees only their own encounters
- **WHEN** a PROFESOR lists encounters
- **THEN** the listing includes only instances from slots owned by that PROFESOR's asignación
- **AND** instances from other docentes' slots are excluded

---

### Requirement: Generate HTML block for the virtual classroom (F6.4)
The system SHALL generate, for a set of instances, an HTML fragment listing each encounter's title, date, time, meeting link and recording link (when present), suitable for pasting into the LMS virtual classroom. The generation SHALL be a pure function of the instances and SHALL escape all text values to prevent HTML injection.

#### Scenario: HTML block includes recording link when present
- **WHEN** the HTML block is generated for an instance with `video_url` set
- **THEN** the output HTML contains the recording link for that instance

#### Scenario: HTML block omits recording link when absent
- **WHEN** the HTML block is generated for an instance with `video_url = NULL`
- **THEN** the output HTML contains the encounter but no recording link for it

#### Scenario: Text values are escaped against injection
- **WHEN** an instance `titulo` contains `<script>` markup
- **THEN** the generated HTML escapes it (no raw `<script>` tag in the output)

---

### Requirement: Encounter operations are permission-guarded (fail-closed)
The system SHALL reject encounter operations for users without the `encuentros:gestionar` permission, following the fail-closed RBAC policy, and SHALL reject unauthenticated requests.

#### Scenario: User without permission cannot create an encounter
- **WHEN** a user without `encuentros:gestionar` calls any encounter endpoint
- **THEN** the system returns HTTP 403

#### Scenario: Unauthenticated request is rejected
- **WHEN** a request to any encounter endpoint arrives without a valid JWT
- **THEN** the system returns HTTP 401

#### Scenario: Encounter management is audited
- **WHEN** a slot, instance or edit operation completes successfully
- **THEN** an audit event with action `ENCUENTRO_GESTIONAR` is recorded with the actor, tenant and affected record count
